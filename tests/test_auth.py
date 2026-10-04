import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import modules


class SessionStateProxy:
    def get(self, key, default=None):
        return {"authenticated": True}.get(key, default)


class AuthenticationTests(unittest.TestCase):
    def test_reads_streamlit_session_state_proxy(self):
        fake_streamlit = SimpleNamespace(session_state=SessionStateProxy())
        with patch.object(modules, "st", fake_streamlit):
            self.assertTrue(modules.is_authenticated())

    def test_missing_streamlit_state_is_unauthenticated(self):
        with patch.object(modules, "st", None):
            self.assertFalse(modules.is_authenticated())

    def test_authentication_requires_both_environment_values(self):
        with patch.dict(os.environ, {"AUTH_USERNAME": "admin", "AUTH_PASSWORD": ""}, clear=True):
            self.assertFalse(modules.is_auth_enabled())

        with patch.dict(os.environ, {"AUTH_USERNAME": "admin", "AUTH_PASSWORD": "secret"}, clear=True):
            self.assertTrue(modules.is_auth_enabled())

    def test_credentials_are_checked_against_environment(self):
        with patch.dict(os.environ, {"AUTH_USERNAME": "admin", "AUTH_PASSWORD": "secret"}, clear=True):
            self.assertTrue(modules._validate_credentials("admin", "secret"))
            self.assertFalse(modules._validate_credentials("admin", "wrong"))


if __name__ == "__main__":
    unittest.main()
