import tempfile
import unittest
from pathlib import Path

from modules.case_loader import (
    batch_load_cases,
    get_case_payload,
    load_cases_from_json,
    save_cases_to_json,
    validate_case_id,
)


class CaseLoaderTests(unittest.TestCase):
    def test_missing_case_file_returns_empty_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(load_cases_from_json(Path(directory) / "missing.json"), {})

    def test_save_creates_parent_and_round_trips_cases(self):
        cases = {"CASE-1": {"victim": "Example", "wallets": {"BTC": "address"}}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "cases.json"

            self.assertTrue(save_cases_to_json(path, cases))

            self.assertEqual(load_cases_from_json(path), cases)

    def test_save_reports_file_write_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "not-a-file"
            path.mkdir()

            self.assertFalse(save_cases_to_json(path, {}))

    def test_payload_normalizes_amounts_and_batch_skips_missing_ids(self):
        payload = get_case_payload(
            "CASE-1",
            {"total_loss_usd": "$1,250 USD", "traced_usd": "500.00"},
        )
        cases = batch_load_cases(
            [{"case_id": "CASE-1", "victim": "Example"}, {"victim": "Missing ID"}]
        )

        self.assertEqual(payload["total_loss_usd"], 1250.0)
        self.assertEqual(payload["traced_usd"], 500.0)
        self.assertEqual(cases, {"CASE-1": {"case_id": "CASE-1", "victim": "Example"}})

    def test_case_id_validation_rejects_empty_and_duplicate_ids(self):
        existing_cases = {"CASE-1": {}}

        self.assertIsNotNone(validate_case_id("  ", existing_cases))
        self.assertEqual(
            validate_case_id(" CASE-1 ", existing_cases),
            "El caso CASE-1 ya existe.",
        )
        self.assertIsNone(validate_case_id(" CASE-2 ", existing_cases))


if __name__ == "__main__":
    unittest.main()
