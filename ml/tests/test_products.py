import unittest

from receipts.products import BASE_PRODUCTS, CATEGORIES, SHELF_LIFE


class BaseProductsTest(unittest.TestCase):
    def test_catalog_has_at_least_one_hundred_unique_names(self):
        self.assertGreaterEqual(len(BASE_PRODUCTS), 100)
        self.assertEqual(len(BASE_PRODUCTS), len(set(BASE_PRODUCTS)))

    def test_every_catalog_name_has_shelf_life_days(self):
        self.assertEqual(set(SHELF_LIFE), set(BASE_PRODUCTS))
        self.assertTrue(all(days > 0 for days in SHELF_LIFE.values()))
        self.assertEqual(SHELF_LIFE["молоко"], 5)

    def test_every_catalog_name_has_a_pantry_category(self):
        self.assertEqual(set(CATEGORIES), set(BASE_PRODUCTS))
        self.assertEqual(CATEGORIES["молоко"], "Молочные")


if __name__ == "__main__":
    unittest.main()
