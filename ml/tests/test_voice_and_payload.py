import unittest

from receipts.normalize import Item, normalize_lines
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
        self.assertEqual(
            payload["items"],
            [
                {
                    "name": "молоко",
                    "quantity": 2000,
                    "unit": "мл",
                    "storage": "Холодильник",
                    "category": None,
                    "unit_id": None,
                    "best_before": None,
                    "storage_place_id": None,
                }
            ],
        )
        self.assertNotIn("id_user_group", payload["items"][0])


if __name__ == "__main__":
    unittest.main()
