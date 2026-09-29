from datetime import datetime, timedelta, timezone

from app.services.stats import count_uploads


def test_counts_unique_products_and_users_in_each_window():
    now = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    rows = [
        ("Молоко", 3, now - timedelta(hours=2)),
        ("молоко", 3, now - timedelta(hours=3)),
        ("Мясо", 5, now - timedelta(days=3)),
        ("Хлеб", 5, now - timedelta(days=20)),
        ("Сыр", 7, now - timedelta(days=40)),
        ("Рис", None, now - timedelta(hours=1)),
    ]

    counted = count_uploads(rows, now)

    assert counted["day"] == {"products": 2, "users": 1}
    assert counted["week"] == {"products": 3, "users": 2}
    assert counted["month"] == {"products": 4, "users": 2}
