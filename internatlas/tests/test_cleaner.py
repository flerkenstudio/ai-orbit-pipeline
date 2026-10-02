import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from competitions.processing.cleaner import parse_date, extract_prize_value, classify_category, clean
from competitions.processing.dedupe import upsert_records, mark_expired, fetch_all
from competitions.schema import init_db


class T(unittest.TestCase):
    def test_dates(self):
        self.assertEqual(parse_date("15 Jan 2030"), "2030-01-15")
        self.assertEqual(parse_date("Apply by: 5th Mar 2030"), "2030-03-05")
        self.assertIsNone(parse_date("soon"))

    def test_prize(self):
        self.assertEqual(extract_prize_value("₹5 Lakh"), 500000)
        self.assertEqual(extract_prize_value("50k"), 50000)
        self.assertEqual(extract_prize_value("1 Cr"), 10000000)
        self.assertIsNone(extract_prize_value(""))

    def test_category(self):
        self.assertEqual(classify_category("Smart India Hackathon"), "hackathon")
        self.assertEqual(classify_category("Random thing"), "other")

    def test_dedupe_and_expire(self):
        db = os.path.join(tempfile.mkdtemp(), "t.db")
        conn = init_db(db)
        raw = {"title": "A", "organiser": "X", "official_url": "http://a", "reg_deadline": "01-01-2000"}
        recs = [clean(raw), clean(raw), clean({"title": ""})]
        c = upsert_records(conn, recs)
        self.assertEqual(c, {"inserted": 1, "updated": 0, "skipped": 2})
        c2 = upsert_records(conn, [clean(raw)])
        self.assertEqual(c2["updated"], 1)
        mark_expired(conn)
        self.assertEqual(fetch_all(conn)[0]["status"], "expired")


if __name__ == "__main__":
    unittest.main()
