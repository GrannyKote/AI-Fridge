"""Export the repeated two-arm experiment, with raw observations preserved."""
import csv
import json
import hashlib
from math import ceil
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / 'results'


def read(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def write(path, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    quality = json.loads((OUT / 'quality.json').read_text(encoding='utf-8-sig'))
    metrics = quality['ranking']
    products = {row['id']: row['name'] for row in read(ROOT / 'data/catalog.csv')}
    queries = read(ROOT / 'data/queries.csv')
    write(OUT / 'queries-with-answers.csv', [dict(row, expected_name=products.get(row['target'], 'Новый продукт'),
          distractor_name=products.get(row['distractor'], '')) for row in queries])
    predictions = read(OUT / 'predictions.csv')
    write(OUT / 'answers.csv', [dict(row, expected_name=products.get(row['target'], 'Новый продукт'),
          top5_names=' | '.join(products[key] for key in row['top5'].split())) for row in predictions])
    write(OUT / 'merge-audit.csv', [row for row in predictions if row['distractor'] or row['false_merge'] == '1'])
    fields = list(dict.fromkeys(key for row in metrics for key in row))
    write(OUT / 'metrics.csv', [{key: row.get(key) for key in fields} for row in metrics])
    latency = []
    for size in (1000, 10000, 100000):
        for mode in ('baseline', 'hybrid'):
            pooled = []
            for trial in (1, 2, 3):
                rows = read(OUT / f'latency-{size}-{mode}-{trial}.csv')
                assert len(rows) > 100 and all(row['failed'] == 'False' for row in rows)
                pooled.extend(rows)
                latency.append(measure(size, mode, trial, rows))
            latency.append(measure(size, mode, 'pooled', pooled))
    write(OUT / 'latency-summary.csv', latency)
    total = {row['mode']: row for row in metrics if row['noise'] == 'all'}
    b, h = total['baseline'], total['hybrid']
    reduction = 1 - h['dcr_final'] / b['dcr_final']
    worst = max(row['http_p95_ms'] for row in latency if row['mode'] == 'hybrid' and row['trial'] != 'pooled')
    checks = {'DCR reduction >= 50%': reduction >= .5, 'Recall@5 >= 85%': h['recall5'] >= .85,
              'Recall gain >= 30 pp': h['recall5'] - b['recall5'] >= .3,
              'FMR <= 2%': h['fmr'] <= .02, 'p95 <= 50 ms': worst <= 50}
    lines = ['Повторный эксперимент — гибридный поиск и префиксный LIKE', 'Дата — 25 ноября 2026 года', '',
             'Методика',
             'Синтетический каталог из 1 000 продуктов и 2 556 запросов, из них 2 306 с эталонным ID и 250 новых продуктов.',
             'Повторно использована фиксированная выборка seed 402193 для сопоставимости с первым прогоном. Независимая внешняя выборка отсутствует.',
             'Каталог включает искусственные комбинации типа продукта и вкуса. Словарь и генератор подготовлены совместно.',
             'LIKE — lower(name) LIKE prefix%, экранирование метасимволов, сортировка по названию и ID.',
             'Гибрид — нормализация, точный ключ, затем pg_trgm и русский FTS, до 64 кандидатов каждой ветви, RRF k=60, топ-5.',
             'Правильный ID сверяется с разметкой. Precision@5 рассчитана на пять позиций с единственным релевантным ID, максимум 20%.',
             'DCR — число новых дублей / (1000 + число созданных строк). FMR — ошибочные автопривязки / все автопривязки.',
             'Автопривязка LIKE выполняется по точному названию без регистра, гибрида — по единственному точному ключу.',
             'Создание строк моделируется последовательно в памяти поверх фиксированного поискового каталога. Выбор подсказки человеком не измеряется.',
             'Нагрузка — отдельный FastAPI, PostgreSQL 17, loopback, 8 клиентов, пауза 50 мс, 3 повтора по 30 секунд на режим и размер.',
             'Каталоги 10 000 и 100 000 строк получены добавлением похожих серий. Качество измерено на 1 000 строках.',
             'Единицы измерения и MAPE в этом сравнении поисковых методов не оцениваются.', '', 'Общие метрики',
             'Режим | Recall@5 | Precision@5 | MRR@5 | DCR | FMR | Дубли']
    for mode, row in total.items():
        lines.append(f"{mode} | {row['recall5']:.4%} | {row['precision5']:.4%} | {row['mrr5']:.6f} | {row['dcr_final']:.4%} | {row['fmr']:.4%} | {row['duplicates']}")
    lines += ['', 'Метрики по классам шума', 'Класс | Режим | n | Recall@5 | Precision@5 | MRR@5 | Доля вводов с дублем']
    for row in metrics:
        if row['noise'] != 'all':
            lines.append(f"{row['noise']} | {row['mode']} | {row['attempts']} | {row['recall5']} | {row['precision5']} | {row['mrr5']} | {row['duplicate_risk']}")
    lines += ['', 'Задержка — объединённые повторы', 'Размер | Режим | запросов | HTTP p50 / p95 мс | поиск p50 / p95 мс']
    for row in latency:
        if row['trial'] == 'pooled':
            lines.append(f"{row['catalog']} | {row['mode']} | {row['requests']} | {row['http_p50_ms']:.3f} / {row['http_p95_ms']:.3f} | {row['server_p50_ms']:.3f} / {row['server_p95_ms']:.3f}")
    lines += ['', 'Критерии', f'Относительное снижение DCR — {reduction:.4%}. Худший p95 отдельного повтора — {worst:.3f} мс.']
    lines += [f"{key} — {'выполнен' if value else 'не выполнен'}" for key, value in checks.items()]
    lines += ['Вывод — ' + ('гипотеза подтверждена в проверенной части.' if all(checks.values()) else 'гипотеза частично подтверждена в проверенной части.'),
              'Нулевая наблюдаемая FMR относится к синтетическим ловушкам этой выборки. Рабочий SLA и поведение реальных пользователей требуют отдельной проверки.']
    (OUT / 'report.txt').write_text('\n'.join(lines), encoding='utf-8')
    (OUT / 'criteria.json').write_text(json.dumps(dict(checks=checks, dcr_reduction=reduction, worst_http_p95_ms=worst), indent=2), encoding='utf-8')
    manifest = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                for folder in ('data', 'results') for path in (ROOT / folder).glob('*')
                if path.is_file() and path.name != 'sha256.json'}
    (OUT / 'sha256.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('\n'.join(lines[:28] + lines[-9:]))


def measure(size, mode, trial, rows):
    result = dict(catalog=size, mode=mode, trial=trial, requests=len(rows), failures=0)
    for field in ('http', 'server'):
        values = sorted(float(row[field + '_ms']) for row in rows)
        for p in (50, 95):
            result[f'{field}_p{p}_ms'] = values[ceil(len(values) * p / 100) - 1]
    return result


if __name__ == '__main__':
    main()

