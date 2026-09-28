import unittest

from receipts.analyze import analyze


class LlmAnalyzeTest(unittest.TestCase):
    def test_model_names_are_snapped_to_base_products(self):
        def fake(_prompt: str) -> str:
            return (
                'Вот ответ: [{"i": 0, "product": "яблочный сок"}, '
                '{"i": 1, "product": "яблочный сок"}]'
            )

        found = analyze(
            ["сэк яблочный восстановленный", "сок блочный 129,00"],
            complete=fake,
        )

        self.assertEqual([item.category for item in found], ["яблочный сок", "яблочный сок"])

    def test_broken_answer_falls_back_to_letter_match(self):
        found = analyze(["хлеб"], complete=lambda _prompt: "не json")

        self.assertEqual([item.category for item in found], ["хлеб"])

    def test_lines_the_model_skipped_are_still_matched(self):
        found = analyze(
            ["хлеб", "молоко"],
            complete=lambda _prompt: '[{"i": 1, "product": "молоко"}]',
        )

        self.assertEqual([item.category for item in found], ["хлеб", "молоко"])

    def test_glued_line_splits_into_products(self):
        found = analyze(["Паштет шпротный Вермишель со вкусом курицы Драже Лимончики"])

        self.assertEqual(
            [item.category for item in found],
            ["паштет", "вермишель", "драже"],
        )

    def test_non_product_index_is_skipped(self):
        def fake(_prompt: str) -> str:
            return '[{"i": 1, "product": "молоко"}]'

        found = analyze(["ИТОГО 10.00", "Молоко 2.5% 89.90"], complete=fake)

        self.assertEqual([item.category for item in found], ["молоко"])
        self.assertTrue(found[0].phrase.startswith("Молоко"))


if __name__ == "__main__":
    unittest.main()
