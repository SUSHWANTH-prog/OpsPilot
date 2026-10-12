import tempfile
import unittest
from pathlib import Path
from tools.data_tools import calculate_kpis, compare_periods, inspect_data, revenue_by_category

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample_sales.csv"

class DataToolTests(unittest.TestCase):
    def test_inspect_data_counts_rows(self):
        result = inspect_data(SAMPLE)
        self.assertEqual(result["row_count"], 12)
        self.assertIn("revenue", result["columns"])

    def test_kpis_total_revenue(self):
        result = calculate_kpis(SAMPLE)
        self.assertEqual(result["total_revenue"], 226300.0)

    def test_period_comparison(self):
        result = compare_periods(SAMPLE)
        self.assertEqual(result["earliest_month"], "2026-01")
        self.assertEqual(result["latest_month"], "2026-03")

    def test_category_revenue(self):
        result = revenue_by_category(SAMPLE)
        self.assertIn("Computers", result["revenue_by_category"])

    def test_missing_file_errors(self):
        with self.assertRaises(FileNotFoundError):
            inspect_data("file_that_does_not_exist.csv")

if __name__ == "__main__":
    unittest.main()
