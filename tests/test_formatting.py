"""Indian amount grouping and parsing."""
import unittest

from app.utils.formatting import format_indian_amount, parse_amount


class TestIndianFormatting(unittest.TestCase):
    def test_format_examples(self):
        cases = [
            (0, "0.00"),
            (123, "123.00"),
            (1234, "1,234.00"),
            (12345, "12,345.00"),
            (123456, "1,23,456.00"),
            (1234567, "12,34,567.00"),
            (10000000, "1,00,00,000.00"),
            (1234.5, "1,234.50"),
            (-99.9, "-99.90"),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(format_indian_amount(value), expected)

    def test_signed(self):
        self.assertEqual(format_indian_amount(1000.25, signed=True), "+1,000.25")
        self.assertEqual(format_indian_amount(-1000.25, signed=True), "-1,000.25")

    def test_parse_amount(self):
        self.assertEqual(parse_amount("1,23,456.78"), 123456.78)
        self.assertEqual(parse_amount("12,34,567"), 1234567.0)
        self.assertEqual(parse_amount(" 1000 "), 1000.0)
        self.assertEqual(parse_amount(""), 0.0)
        self.assertEqual(parse_amount(None), 0.0)
        self.assertEqual(parse_amount(42), 42.0)
        self.assertEqual(parse_amount("0.5"), 0.5)


if __name__ == "__main__":
    unittest.main()
