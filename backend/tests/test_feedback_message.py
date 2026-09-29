import unittest

from pydantic import ValidationError

from app.schemas import FeedbackIn
from app.services.feedback import ensure_photo_count


class FeedbackMessageTest(unittest.TestCase):
    def test_blank_message_is_rejected(self):
        with self.assertRaises(ValidationError):
            FeedbackIn(user_id=1, message="   ")

    def test_message_is_trimmed(self):
        payload = FeedbackIn(user_id=1, message="  молоко кончилось  ")
        self.assertEqual(payload.message, "молоко кончилось")

    def test_sixth_photo_is_rejected(self):
        ensure_photo_count(5)
        with self.assertRaises(ValueError):
            ensure_photo_count(6)


if __name__ == "__main__":
    unittest.main()
