import unittest

from receipts.analyze import analyze
from receipts.category import to_category
from receipts.drop import drop_extra
from receipts.photo import read_lines


class PhotoStepTest(unittest.TestCase):
    def test_missing_file_is_rejected_before_recognition(self):
        with self.assertRaises(FileNotFoundError):
            read_lines("/no/such/receipt.jpg")


class DropStepTest(unittest.TestCase):
    def test_header_goes_away_and_purchase_text_stays(self):
        raw = [
            'ООО "Торгсервис 69"',
            "Кимры Орджоникидзе 6841",
            "КАССОВЫЙ ЧЕК",
            "ИТОГО 89.90",
            "Сэк",
            "сэк яблочный восстановленный",
            "сок",
        ]

        self.assertEqual(
            drop_extra(raw),
            ["сэк яблочный восстановленный", "сок"],
        )


class DropPriceTest(unittest.TestCase):
    def test_four_digit_price_stays_and_house_number_goes(self):
        self.assertEqual(
            drop_extra(["Сосиски сочные ПГН 74.90 1 7113.40"]),
            ["Сосиски сочные ПГН 74.90 1 7113.40"],
        )
        self.assertEqual(drop_extra(["Кимры Орджоникидзе 6841"]), [])


class AnalyzeStepTest(unittest.TestCase):
    def test_ocr_variants_share_one_category(self):
        found = analyze([
            "сэк яблочный восстановленный",
            "сок блочный 129,00",
            "сок",
            "прмт 12.00",
        ])

        self.assertEqual(
            [item.category for item in found],
            ["яблочный сок", "яблочный сок", "сок"],
        )
        self.assertGreater(found[0].score, 0.45)


class CategoryStepTest(unittest.TestCase):
    def test_units_become_grams_and_name_stays_canonical(self):
        found = analyze(["мука 1,5 кг", "молоко два литра", "МОЛОКО 2.5% 89.90"])
        items = to_category(found)

        self.assertEqual(
            [(item.name, item.quantity, item.unit) for item in items],
            [
                ("мука", 1500, "г"),
                ("молоко", 2000, "мл"),
                ("молоко 2.5%", 1, "шт"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
