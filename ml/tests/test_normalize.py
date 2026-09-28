import unittest

from receipts.normalize import normalize_lines, suggest_storage


class NormalizeTest(unittest.TestCase):
    def test_photo_line_drops_price_and_keeps_percent(self):
        items = normalize_lines(["МОЛОКО 2.5% 89.90"])

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "молоко 2.5%")
        self.assertEqual(items[0].quantity, 1)
        self.assertEqual(items[0].unit, "шт")

    def test_total_line_is_dropped(self):
        items = normalize_lines(["МОЛОКО 2.5% 89.90", "ИТОГО 89.90"])

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "молоко 2.5%")

    def test_voice_liters_become_milliliters(self):
        items = normalize_lines(["молоко два литра", "хлеб"])

        self.assertEqual(
            [(item.name, item.quantity, item.unit) for item in items],
            [("молоко", 2000, "мл"), ("хлеб", 1, "шт")],
        )

    def test_kilograms_become_grams(self):
        items = normalize_lines(["мука 1,5 кг"])

        self.assertEqual(items[0].name, "мука")
        self.assertEqual(items[0].quantity, 1500)
        self.assertEqual(items[0].unit, "г")

    def test_junk_keywords_do_not_eat_product_names(self):
        items = normalize_lines(["Картофель 2 кг", "ИНН 7707083893", "НДС 20%"])

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "картофель")
        self.assertEqual(items[0].quantity, 2000)
        self.assertEqual(items[0].unit, "г")

    def test_receipt_header_is_dropped_and_product_stays(self):
        items = normalize_lines([
            'ООО "Торгсервис 69"',
            "Кимры Орджоникидзе 6841",
            "КАССОВЫЙ",
            'ЧЕК "1g0 (ПРИХОД)',
            "KACCA ; 00O3,C1 КАССИР: Кассир 01",
            "Сэк",
            "сок",
        ])

        self.assertEqual([item.name for item in items], ["сок"])

    def test_ocr_lines_collapse_to_one_apple_juice(self):
        items = normalize_lines([
            "сэк яблочный восстановленный",
            "сок блочный 129,00",
            "прмт 12.00",
            "хлеб",
            "Сэк",
            "КАССОВЫЙ ЧЕК",
        ])
        self.assertEqual(
            [item.name for item in items],
            ["яблочный сок", "яблочный сок", "хлеб"],
        )

    def test_storage_follows_the_product_name(self):
        self.assertEqual(suggest_storage("Молоко 2.5%"), "Холодильник")
        self.assertEqual(suggest_storage("мука"), "Бакалея")
        self.assertEqual(suggest_storage("хлеб"), "Шкаф")
        self.assertEqual(suggest_storage("куриное филе"), "Морозилка")
        self.assertEqual(suggest_storage("неизвестный товар"), "Шкаф")


if __name__ == "__main__":
    unittest.main()
