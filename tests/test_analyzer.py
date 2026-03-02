import unittest
from analyzer import compute_conversion_score

class TestConversionScore(unittest.TestCase):

    def test_score_positive_case(self):
        row = {
            "total_pax": 4,
            "shuttle_available": 0,
            "lead_time_hours": 72
        }

        score = compute_conversion_score(row)
        self.assertGreater(score, 0)

if __name__ == "__main__":
    unittest.main()