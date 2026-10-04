import unittest

from modules.currency_utils import _to_float


class CurrencyConversionTests(unittest.TestCase):
    def test_converts_supported_currency_formats(self):
        values = {
            "$120,000.00": 120000.0,
            "$120,000.00 USD": 120000.0,
            "45,000 USD": 45000.0,
            "usd 45,000": 45000.0,
            1250: 1250.0,
            12.5: 12.5,
        }
        for value, expected in values.items():
            with self.subTest(value=value):
                self.assertEqual(_to_float(value), expected)

    def test_returns_default_for_invalid_or_non_finite_values(self):
        for value in (None, "", "not a value", "NaN", "inf", float("inf")):
            with self.subTest(value=value):
                self.assertEqual(_to_float(value, default=-1.0), -1.0)


if __name__ == "__main__":
    unittest.main()
