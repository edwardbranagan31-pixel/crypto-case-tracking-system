import tempfile
import unittest
from pathlib import Path

from modules import saas


class SaasTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "t.db"
        self.a, _ = saas.create_tenant("Org A", "alice_admin", "password123", path=self.db)
        self.b, _ = saas.create_tenant("Org B", "bob_admin", "password123", path=self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_authentication(self):
        self.assertEqual(saas.authenticate("alice_admin", "password123", self.db)["tenant"], "Org A")
        self.assertIsNone(saas.authenticate("alice_admin", "wrong", self.db))
        self.assertIsNone(saas.authenticate("nobody", "password123", self.db))

    def test_duplicates_and_validation(self):
        self.assertIsNotNone(saas.create_tenant("Org A", "x_user", "password123", path=self.db)[1])
        self.assertIsNotNone(saas.create_tenant("Org C", "bob_admin", "password123", path=self.db)[1])
        self.assertIsNotNone(saas.create_tenant("Org D", "short_pw", "123", path=self.db)[1])

    def test_cases_are_tenant_isolated(self):
        saas.save_tenant_cases(self.a["tenant_id"], {"C1": {"title": "x"}}, self.db)
        self.assertEqual(saas.load_tenant_cases(self.b["tenant_id"], self.db), {})
        saas.save_tenant_cases(self.b["tenant_id"], {"C2": {}}, self.db)
        self.assertEqual(list(saas.load_tenant_cases(self.a["tenant_id"], self.db)), ["C1"])

    def test_roles_and_user_limit(self):
        tid = self.a["tenant_id"]
        self.assertIsNotNone(saas.add_user(tid, "viewer", "new_user", "password123", "viewer", self.db))
        self.assertIsNone(saas.add_user(tid, "admin", "new_user", "password123", "viewer", self.db))
        self.assertIsNotNone(saas.add_user(tid, "admin", "third_u", "password123", "analyst", self.db))  # free: 2
        self.assertFalse(saas.can_write("viewer"))
        self.assertTrue(saas.can_write("analyst"))

    def test_usage_limits(self):
        tid = self.a["tenant_id"]
        for _ in range(20):
            self.assertTrue(saas.consume(tid, "onchain", path=self.db))
        self.assertFalse(saas.consume(tid, "onchain", path=self.db))
        self.assertEqual(saas.get_usage(tid, "onchain", self.db), 20)
        saas.set_plan(tid, "pro", self.db)
        self.assertTrue(saas.consume(tid, "onchain", path=self.db))

    def test_case_limit(self):
        tid = self.a["tenant_id"]
        self.assertTrue(saas.can_add_case(tid, 4, self.db))
        self.assertFalse(saas.can_add_case(tid, 5, self.db))


if __name__ == "__main__":
    unittest.main()
