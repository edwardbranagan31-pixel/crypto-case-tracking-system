from __future__ import annotations

import csv
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules.entities import EntityGraph


def audit_file() -> Path:
    return Path(os.getenv("AUDIT_FILE", Path(__file__).resolve().parent.parent / "audit_log.jsonl"))


def record_audit(user: str, action: str, case_id: str, detail: str = "", path: Path | None = None) -> bool:
    """Append who did what (e.g. which transform was run) to a JSON-lines audit trail."""
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "user": user or "anonymous",
             "action": action, "case_id": case_id, "detail": detail}
    target = path or audit_file()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        return False
    return True


def read_audit(case_id: str | None = None, path: Path | None = None) -> List[Dict[str, Any]]:
    target = path or audit_file()
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    entries = []
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if case_id is None or entry.get("case_id") == case_id:
            entries.append(entry)
    return entries


def allowed_users_for_case(case: Dict[str, Any]) -> Optional[set]:
    """Optional per-case access list: case["allowed_users"]. None means open to all authenticated users."""
    users = case.get("allowed_users")
    return {str(u) for u in users} if isinstance(users, list) and users else None


def can_access_case(user: str, case: Dict[str, Any], auth_enabled: bool) -> bool:
    allowed = allowed_users_for_case(case)
    if not auth_enabled or allowed is None:
        return True
    return user in allowed


def graph_to_csv(graph: EntityGraph) -> str:
    """Entities and links in one CSV (record_type column distinguishes them)."""
    def safe(value: Any) -> str:
        text = str(value)
        return "'" + text if text[:1] in ("=", "+", "-", "@") else text  # avoid spreadsheet formula injection

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["record_type", "type", "value", "source", "timestamp", "target_type", "target_value", "label"])
    for e in graph.entities.values():
        writer.writerow(["entity", e.type, safe(e.value), e.source, e.timestamp, "", "", ""])
    for l in graph.links:
        writer.writerow(["link", l.source[0], safe(l.source[1]), "", "", l.target[0], safe(l.target[1]), safe(l.label)])
    return out.getvalue()


def graph_to_json(graph: EntityGraph) -> str:
    return json.dumps(graph.to_dict(), ensure_ascii=False, indent=2)


def _pdf_escape(text: str) -> str:
    text = text.encode("latin-1", "replace").decode("latin-1")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def lines_to_pdf(lines: List[str], per_page: int = 55) -> bytes:
    """Minimal dependency-free text PDF (Helvetica, A4)."""
    pages = [lines[i:i + per_page] for i in range(0, max(len(lines), 1), per_page)] or [[]]
    objects: List[bytes] = []
    n_pages = len(pages)
    page_ids = [3 + 2 * i for i in range(n_pages)]
    font_id = 3 + 2 * n_pages
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>".encode())
    for i, page in enumerate(pages):
        stream = "BT /F1 9 Tf 40 800 Td 14 TL\n" + "\n".join(f"({_pdf_escape(l[:110])}) '" for l in page) + "\nET"
        data = stream.encode("latin-1")
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents {page_ids[i] + 1} 0 R "
                       f"/Resources << /Font << /F1 {font_id} 0 R >> >> >>".encode())
        objects.append(b"<< /Length %d >>\nstream\n" % len(data) + data + b"\nendstream")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for idx, obj in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{idx} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def graph_to_pdf(case_id: str, graph: EntityGraph) -> bytes:
    lines = [f"Case {case_id} - entity graph", f"Generated {datetime.now(timezone.utc).isoformat()}", "",
             f"Entities ({len(graph.entities)}):"]
    lines += [f"  [{e.type}] {e.value} (source: {e.source})" for e in graph.entities.values()]
    lines += ["", f"Links ({len(graph.links)}):"]
    lines += [f"  {l.source[1]} -> {l.target[1]} {l.label}" for l in graph.links]
    return lines_to_pdf(lines)


def sync_graph_to_neo4j(driver: Optional[Any], case_id: str, graph: EntityGraph) -> Dict[str, Any]:
    """Persist the entity graph as :Entity nodes and :LINK relationships scoped by case_id."""
    if driver is None:
        return {"status": "skipped", "reason": "No Neo4j driver available"}
    try:
        with driver.session() as session:
            for e in graph.entities.values():
                session.run(
                    "MERGE (n:Entity {case_id: $case_id, type: $type, value: $value}) "
                    "SET n.source = $source, n.timestamp = $timestamp",
                    case_id=case_id, type=e.type, value=e.value, source=e.source, timestamp=e.timestamp)
            for l in graph.links:
                session.run(
                    "MATCH (a:Entity {case_id: $case_id, type: $st, value: $sv}), "
                    "(b:Entity {case_id: $case_id, type: $tt, value: $tv}) "
                    "MERGE (a)-[r:LINK {label: $label}]->(b)",
                    case_id=case_id, st=l.source[0], sv=l.source[1], tt=l.target[0], tv=l.target[1], label=l.label)
        return {"status": "success", "entities": len(graph.entities), "links": len(graph.links)}
    except Exception as error:
        return {"status": "error", "error": str(error)}
