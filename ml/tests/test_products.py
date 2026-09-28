import unittest

from receipts.products import BASE_PRODUCTS


class BaseProductsTest(unittest.TestCase):
    def test_catalog_has_at_least_one_hundred_unique_names(self):
        self.assertGreaterEqual(len(BASE_PRODUCTS), 100)
        self.assertEqual(len(BASE_PRODUCTS), len(set(BASE_PRODUCTS)))


if __name__ == "__main__":
    unittest.main()
