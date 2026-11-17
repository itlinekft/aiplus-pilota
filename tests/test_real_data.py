"""Tests of the real-data gate (kit/real_data.py). The valid-looking numbers are computed at run time, so no
real-looking identifier is ever written into this file."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kit"))
import real_data as rd  # noqa: E402


def with_weighted_check(prefix7):
    """Seven digits plus the 9-7-3-1 check digit that makes them pass."""
    s = sum(int(d) * w for d, w in zip(prefix7, [9, 7, 3, 1, 9, 7, 3]))
    return prefix7 + str((10 - s % 10) % 10)


def taj(prefix8):
    return prefix8 + str(sum(int(d) * (3 if i % 2 == 0 else 7) for i, d in enumerate(prefix8)) % 10)


def wrong(number):
    """The same number with its last digit off by one: it can no longer be real."""
    return number[:-1] + str((int(number[-1]) + 1) % 10)


class Checks(unittest.TestCase):
    def setUp(self):
        self.tax = with_weighted_check("1234567") + "-2-41"
        self.taj = taj("12345678")
        self.bank = with_weighted_check("1177301") + "-" + with_weighted_check("2003040")

    def test_check_digits(self):
        self.assertTrue(rd.weighted_ok(self.tax[:8]))
        self.assertFalse(rd.weighted_ok(wrong(self.tax[:8])))
        self.assertTrue(rd.taj_ok(self.taj))
        self.assertFalse(rd.taj_ok(wrong(self.taj)))

    def test_real_looking_ids_are_found(self):
        kinds = [k for _, k, _ in rd.findings(f"adószám {self.tax}\nTAJ {self.taj[:3]} {self.taj[3:6]} {self.taj[6:]}\n"
                                              f"számla {self.bank}")]
        self.assertEqual(kinds, ["adószám", "TAJ", "bankszámlaszám"])

    def test_invented_ids_with_a_wrong_check_digit_pass(self):
        text = f"adószám {wrong(self.tax[:8])}-2-41, TAJ {wrong(self.taj)}, számla {self.bank[:9]}{wrong(self.bank[9:])}"
        self.assertEqual(rd.findings(text), [])

    def test_invented_bank_prefix_passes(self):
        invented = with_weighted_check("9990001") + "-" + with_weighted_check("0000001")
        self.assertEqual(rd.findings(f"számla {invented}"), [])

    def test_amounts_and_voucher_numbers_pass(self):
        self.assertEqual(rd.findings("V/000006 37 389 Ft, VSZ-2026/0412, 919 162 = 919 162, 2026.11.17"), [])

    def test_fixtures_are_not_scanned_but_forbidden_names_are(self):
        cfg = rd.load_config('{"forbiddenNames": [["\\\\.dbf$", "a program data file"]]}')
        files = [("tests/fixtures/x.txt", f"{self.tax}".encode()), ("profiles/x/adat.DBF", b"")]
        self.assertEqual(rd.scan(files, cfg), ["profiles/x/adat.DBF: a program data file (refused by file name)"])
        self.assertEqual(len(rd.scan([("profiles/x/notes.md", self.tax.encode())], cfg)), 1)


if __name__ == "__main__":
    unittest.main()
