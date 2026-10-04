import json
import tempfile
import unittest
from pathlib import Path

from modules.case_loader import load_cases_from_json, save_cases_to_json


class CasePersistenceTests(unittest.TestCase):
    def test_load_returns_empty_mapping_for_missing_or_invalid_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            self.assertEqual(load_cases_from_json(path), {})

            path.write_text("{invalid json", encoding="utf-8")
            self.assertEqual(load_cases_from_json(path), {})

    def test_save_and_load_round_trip(self):
        cases = {"CASE-1": {"victim": "Example", "total_loss_usd": 1200}}

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "cases.json"
            save_cases_to_json(path, cases)

            self.assertEqual(load_cases_from_json(path), cases)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), cases)

    def test_save_surfaces_write_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            with self.assertRaises(OSError):
                save_cases_to_json(path, {})


if __name__ == "__main__":
    unittest.main()
