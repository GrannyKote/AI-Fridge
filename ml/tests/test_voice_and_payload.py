import unittest
from unittest.mock import patch

from receipts.normalize import Item, normalize_lines, read_products
from receipts.payload import MISSING, to_payload
from receipts.voice import split_phrases


class VoiceSplitTest(unittest.TestCase):
    def test_splits_on_comma_and_keeps_decimal(self):
        self.assertEqual(
            split_phrases("молоко 1,5 литра, хлеб и яйца."),
            ["молоко 1,5 литра", "хлеб", "яйца"],
        )
        items = normalize_lines(split_phrases("молоко 1,5 литра, хлеб"))
        self.assertEqual(
            [(item.name, item.quantity, item.unit) for item in items],
            [("молоко", 1500, "мл"), ("хлеб", 1, "шт")],
        )


class PayloadTest(unittest.TestCase):
    def test_shape_matches_add_product_and_lists_gaps(self):
        payload = to_payload([Item(name="молоко", quantity=2000, unit="мл", raw_line="молоко два литра")])

        self.assertEqual(payload["missing"], MISSING)
        self.assertEqual(payload["skipped"], [])
        self.assertEqual(
            payload["items"],
            [
                {
                    "name": "молоко",
                    "quantity": 2000,
                    "unit": "мл",
                    "storage": "Холодильник",
                    "category": "Молочные",
                    "unit_id": None,
                    "shelf_life_days": None,
                    "best_before": None,
                    "storage_place_id": None,
                    "score": None,
                }
            ],
        )
        self.assertNotIn("id_user_group", payload["items"][0])

    def test_milk_response_has_shelf_life_and_skipped_line_does_not(self):
        items, skipped = read_products(["молоко 1 л", "МОЛОКО 2.5% 89.90", "прмт 12.00"])
        payload = to_payload(items, skipped)

        self.assertEqual(
            [(item["name"], item["shelf_life_days"]) for item in payload["items"]],
            [("молоко", 5), ("молоко 2.5%", 5)],
        )
        self.assertEqual(payload["skipped"][0]["line"], "прмт 12.00")
        self.assertLess(payload["skipped"][0]["score"], 0.45)
        self.assertGreaterEqual(payload["items"][0]["score"], 0.45)
        self.assertNotIn("shelf_life_days", payload["skipped"][0])
        self.assertEqual(payload["items"][0]["storage"], "Холодильник")

    @patch("receipts.store.base_products", return_value=[("молоко", 5, "Морозилка")])
    def test_storage_comes_from_the_catalog_row(self, _loaded):
        items, _skipped = read_products(["молоко 1 л"])
        payload = to_payload(items, [])

        self.assertEqual(payload["items"][0]["name"], "молоко")
        self.assertEqual(payload["items"][0]["storage"], "Морозилка")
        self.assertEqual(payload["items"][0]["shelf_life_days"], 5)


if __name__ == "__main__":
    unittest.main()
