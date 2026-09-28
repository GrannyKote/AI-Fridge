import unittest

from receipts.photo import _group_lines


class GroupLinesTest(unittest.TestCase):
    def test_words_on_one_row_join_left_to_right(self):
        detections = [
            ([[10, 0], [40, 0], [40, 20], [10, 20]], "яблочный", 0.9),
            ([[50, 2], [120, 2], [120, 22], [50, 22]], "восстановленный", 0.8),
            ([[10, 40], [40, 40], [40, 60], [10, 60]], "молоко", 0.9),
        ]

        self.assertEqual(
            _group_lines(detections),
            ["яблочный восстановленный", "молоко"],
        )

    def test_next_receipt_row_stays_separate(self):
        detections = [
            ([[0, 0], [40, 0], [40, 20], [0, 20]], "ветчина", 0.9),
            ([[0, 28], [80, 28], [80, 48], [0, 48]], "вермишель", 0.9),
        ]

        self.assertEqual(_group_lines(detections), ["ветчина", "вермишель"])

    def test_low_confidence_fragment_is_dropped(self):
        detections = [
            ([[0, 0], [10, 0], [10, 10], [0, 10]], "Сэк", 0.05),
            ([[20, 0], [80, 0], [80, 10], [20, 10]], "сок", 0.7),
        ]

        self.assertEqual(_group_lines(detections), ["сок"])


if __name__ == "__main__":
    unittest.main()
