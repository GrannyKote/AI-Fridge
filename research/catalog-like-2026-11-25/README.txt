Повторная проверка гибридного поиска против префиксного LIKE
25 ноября 2026 года

Результаты — results/report.txt, metrics.csv и latency-summary.csv.
Список продуктов — data/catalog.csv. Размеченные запросы — data/queries.csv.
Ответы обоих методов — results/predictions.csv.
Сырые HTTP-замеры — results/latency-*.csv, журнал — results/load.log.

Воспроизведение из корня репозитория

Нужны Python 3.12, psycopg, FastAPI, Uvicorn, pytest, Locust 2.47.0,
PostgreSQL 17 и доступное расширение pg_trgm. Создайте выделенную пустую
БД catalog_bench_ru на 127.0.0.1:55439 с UTF8 и русским LC_CTYPE.
В текущем запуске использованы PostgreSQL 17.7 и Russian_Russia.1251.

    $env:PYTHONPATH = (Resolve-Path backend).Path
    python research/catalog-like-2026-11-25/dataset.py
    python -m pytest research/catalog-like-2026-11-25/test_experiment.py -q
    python research/catalog-like-2026-11-25/bench.py 1000 --no-vector --quality
    python research/catalog-like-2026-11-25/run_load.py --no-vector --trials 3 --seconds 30
    python research/catalog-like-2026-11-25/finish.py

Скрипт подготовки очищает выделенную таблицу catalog_eval.product.
Рабочий код нормализации импортируется из backend/app/services/canonicalization.py.
В этом повторе используются ровно два режима поиска, baseline и hybrid.
Генератор сохранён из первого эксперимента для сопоставимости выборки.
Критерии MAPE и модели единиц измерения относятся к отдельной части гипотезы.
В итоговом сравнении поисковых методов они не оцениваются.
