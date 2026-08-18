import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.policies import detect_structuring


class StructuringPolicyTest(unittest.TestCase):
    def test_detects_repeated_small_cash_deposits_with_evasion(self):
        messages = [
            "I would like to deposit $9,500 in cash.",
            "Make it $9,000 and I will use the other window tomorrow.",
            "I do not want any reporting paperwork.",
        ]

        self.assertTrue(detect_structuring(messages))

    def test_requires_more_than_one_small_amount(self):
        messages = [
            "I would like to deposit $9,500 in cash.",
            "Do I need reporting paperwork?",
        ]

        self.assertFalse(detect_structuring(messages))

    def test_requires_cash_deposit_context(self):
        messages = [
            "Split the invoice into $9,500 and $9,000.",
            "Send the paperwork to the other window.",
        ]

        self.assertFalse(detect_structuring(messages))


if __name__ == "__main__":
    unittest.main()
