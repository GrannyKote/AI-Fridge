import unittest

from app.services.pantry import product_name_for_pantry, shelf_lookup_name, snap_to_catalog, stored_name

CATALOG = ("молоко", "простокваша", "масло", "сливочное масло", "яблочный сок", "сок", "сыр", "сырники")


class SnapNameTest(unittest.TestCase):
    def test_two_brands_become_one_milk(self):
        self.assertEqual(snap_to_catalog("Молоко Простоквашино", CATALOG), "молоко")
        self.assertEqual(snap_to_catalog("Молоко Пискарёвское", CATALOG), "молоко")

    def test_longer_catalog_name_wins(self):
        self.assertEqual(snap_to_catalog("сливочное масло 82%", CATALOG), "сливочное масло")
        self.assertEqual(snap_to_catalog("яблочный сок", CATALOG), "яблочный сок")

    def test_shorter_name_does_not_eat_a_longer_word(self):
        self.assertEqual(snap_to_catalog("сырники", CATALOG), "сырники")

    def test_unknown_name_stays(self):
        self.assertEqual(snap_to_catalog("редкий товар", CATALOG), "редкий товар")

    def test_shelf_life_uses_the_base_name_inside_a_product(self):
        self.assertEqual(shelf_lookup_name("Молоко 2.5%", CATALOG), "молоко")
        self.assertEqual(shelf_lookup_name("молоко", CATALOG), "молоко")
        self.assertIsNone(shelf_lookup_name("редкий товар", CATALOG))

    def test_pantry_name_starts_with_a_capital(self):
        self.assertEqual(stored_name("молоко"), "Молоко")
        self.assertEqual(stored_name("яблочный сок"), "Яблочный сок")
        self.assertEqual(stored_name("мясО"), "Мясо")
        self.assertEqual(stored_name("Сыр Гауда"), "Сыр Гауда")
        self.assertEqual(stored_name("Яйца С1"), "Яйца С1")

    def test_case_variants_become_one_name(self):
        self.assertEqual(product_name_for_pantry("мясо", CATALOG), "Мясо")
        self.assertEqual(product_name_for_pantry("Мясо", CATALOG), "Мясо")
        self.assertEqual(product_name_for_pantry("мясО", CATALOG), "Мясо")
        self.assertEqual(product_name_for_pantry("мясО", ("мясо",)), "Мясо")

    def test_brand_still_becomes_the_base_name(self):
        self.assertEqual(product_name_for_pantry("Молоко Простоквашино", CATALOG), "Молоко")
        self.assertEqual(product_name_for_pantry("Молоко 2.5%", CATALOG), "Молоко 2.5%")
        self.assertEqual(product_name_for_pantry("Молоко 3.5%", CATALOG), "Молоко 3.5%")
        self.assertNotEqual(
            product_name_for_pantry("Молоко 2.5%", CATALOG),
            product_name_for_pantry("Молоко 3.5%", CATALOG),
        )


if __name__ == "__main__":
    unittest.main()
