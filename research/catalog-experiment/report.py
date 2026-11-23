"""Build the human-readable report from the saved benchmark results."""
import json
from bench import RESULTS, records
from summarize import LABELS, read
from search import MODES

NAMES = {"baseline": "Baseline", "hybrid": "Гибрид", "pgvector": "pgvector"}


def percent(value):
    return "—" if value is None else f"{value:.2%}".replace(".", ",")


def num(value):
    return f"{float(value):.2f}".replace(".", ",")


def count(value):
    return f"{value:,}".replace(",", " ")


def main():
    quality = json.loads((RESULTS / "quality.json").read_text(encoding="utf-8"))
    criteria = json.loads((RESULTS / "criteria.json").read_text(encoding="utf-8"))
    latency = read(RESULTS / "latency.csv")
    at_scale = {row["mode"]: row for row in latency
                if row["catalog"] == "100000" and row["trial"] == "pooled"}
    audit = read(RESULTS / "merge-audit.csv")
    ranking = {(row["mode"], row["noise"]): row for row in quality["ranking"]}
    agg = {(row["mode"], row["unit"]): row for row in quality["aggregation"]}
    b, h, v = (ranking[mode, "all"] for mode in MODES)
    status = {
        "confirmed": "подтверждена",
        "partially_confirmed": "частично подтверждена",
        "not_confirmed": "не подтверждена",
    }[criteria["verdict"]]
    lines = [f"Проверка гипотезы AI-Fridge — гипотеза {status}",
             "", "22 ноября 2026, эксперимент на синтетических данных", "",
             f"Каталог — {count(len(records('catalog.csv')))} продуктов. Запросы — {count(b['attempts'])}, из них "
             f"{count(b['positive'])} с эталонным продуктом и {b['novel']} с новым продуктом. "
             f"История — {count(len(records('operations.csv')))} операций потребления и списания.",
             "", "Критерии гипотезы", ""]
    checks = [
        ("Снижение DCR ≥ 50%", "dcr_reduction_at_least_50_pct",
         f"{percent(b['dcr_final'])} → {percent(h['dcr_final'])}, "
         f"относительное снижение {percent(criteria['dcr_relative_reduction'])}"),
        ("Recall@5 ≥ 85%", "recall_at_least_85_pct", percent(h["recall5"])),
        ("Прирост Recall@5 ≥ 30 п. п.", "recall_gain_at_least_30_points",
         f"+{num(100 * criteria['recall_gain'])} п. п."),
        ("MAPE ≤ 1%", "mape_at_most_1_pct",
         f"{percent(agg['baseline', 'comparable']['mape'])} → {percent(agg['hybrid', 'comparable']['mape'])}"),
        ("Изоляция несовместимых единиц", "no_mixed_dimensions",
         f"{agg['baseline', 'comparable']['mixed_output_groups']} смешанных групп → "
         f"{agg['hybrid', 'comparable']['mixed_output_groups']}"),
        ("FMR ≤ 2%", "fmr_at_most_2_pct", f"{h['false_merges']} из {h['merges']} слияний"),
        ("HTTP p95 ≤ 50 мс во всех повторах", "http_p95_at_most_50_ms_in_every_trial",
         f"максимум {num(criteria['max_hybrid_http_p95_ms'])} мс"),
    ]
    for label, field, value in checks:
        result = "выполнен" if criteria["criteria"][field] else "не выполнен"
        end = "" if value.endswith(".") else "."
        lines.append(f"• {label} — {value}{end} Критерий {result}.")
    lines.extend(["", "Итоговое качество", "",
                  "Режим       Recall@5    Precision@5   MRR@5       DCR        Новые дубли   FMR"])
    for mode, row in zip(MODES, (b, h, v)):
        lines.append(f"{NAMES[mode]:<11} {percent(row['recall5']):>8} {percent(row['precision5']):>13} "
                     f"{num(row['mrr5']):>8} {percent(row['dcr_final']):>12} "
                     f"{row['duplicates']:>12} {percent(row['fmr']):>9}")
    lines.extend([
        "",
        "DCR — новые дубли / (1 000 исходных строк + все созданные строки). "
        "Доля вводов существующих продуктов, создавших дубль, — отдельная метрика.",
        f"По числу вновь созданных дублей снижение {percent(1 - h['duplicates'] / b['duplicates'])}. "
        f"Парные исходы по запросам улучшились в {criteria['duplicate_outcomes_improved']} случаях "
        f"и ухудшились в {criteria['duplicate_outcomes_worsened']}. При условии независимости пар "
        f"точное p = {criteria['paired_exact_p_descriptive']:.2g}. Общие продукты и шаблоны "
        "создают зависимость, поэтому p описывает выборку и не характеризует пользователей.",
        "Recall@5 и MRR@5 считаются по запросам с эталоном. Precision@5 использует пять позиций "
        "и один эталон, поэтому максимум равен 20%. FMR — ошибочные автослияния среди автослияний. "
        "Для новых продуктов отдельно проверялась ошибочная привязка к существующему.",
        "", "Качество по классам шума", "",
        "Режимы в каждой тройке идут в порядке Baseline / Гибрид / pgvector.",
        "Дубли в таблице — доля положительных вводов, при которых создана дублирующая строка.",
        "",
    ])
    for group, label in LABELS.items():
        if group == "all":
            continue
        group_rows = [ranking[mode, group] for mode in MODES]
        metrics = [" / ".join(percent(row[field]) for row in group_rows)
                   for field in ("recall5", "precision5", "duplicate_risk")]
        lines.extend([f"{label}, n = {group_rows[0]['attempts']}",
                      f"  Recall@5 {metrics[0]}  |  Precision@5 {metrics[1]}  |  Дубли {metrics[2]}"])
    lines.extend(["", "Ошибочные слияния и ловушки", ""])
    for mode in MODES:
        model = ranking[mode, "all"]
        near = [row for row in audit if row["mode"] == mode and row["noise"] == "trap_novel"
                and row["distractor_in_top5"] == "True"]
        lines.append(f"{NAMES[mode]} — ошибочные слияния {model['false_merges']}/{model['merges']}, "
                     f"привязки нового продукта {model['false_novel']}/{model['novel']}, "
                     f"заданный отвлекающий продукт в топ-5 новых ловушек {len(near)}/{model['novel']}.")
        if near:
            example = near[0]
            lines.append(f"  Пример — «{example['query']}», похожий продукт «{example['distractor']}». "
                         f"Автопривязка ID {example['matched_id'] or 'отсутствует'}.")
    lines.extend([
        "Например, «масло сливочное» и «масло оливковое» имеют разные канонические ключи. "
        "Уникальный точный нормализованный ключ даёт право на автопривязку гибрида. "
        "Нечёткие кандидаты остаются подсказками. Нулевая наблюдаемая FMR относится к этому набору ловушек.",
        "", "Статистика потребления и списания", "",
        "В качестве эталона генератор сохраняет целое количество в граммах, миллилитрах или штуках "
        "до преобразования единиц. Группы задаются продуктом, видом операции и базовой единицей.",
    ])
    for unit in ("г", "мл", "шт"):
        before, after = agg["baseline", unit], agg["hybrid", unit]
        lines.append(f"{unit}, групп {before['groups']} — MAE {num(before['mae'])} → {num(after['mae'])}, "
                     f"MAPE {percent(before['mape'])} → {percent(after['mape'])}.")
    lines.extend([
        "Для сравнимого численного baseline операции сначала разделены по эталонной размерности, "
        "после чего посчитана прямая сумма без коэффициентов. Отдельно проверена структурная ошибка "
        "исходной группировки по продукту и типу операции, где размерность пропускается. "
        "Граммы, миллилитры и штуки в нормализованной версии всегда идут разными рядами. "
        "Векторный режим использует ту же детерминированную агрегацию.",
        "", "Нагрузка", "",
        "Каталог    Режим       Запросы   HTTP p50 / p95, мс   Поиск p50 / p95, мс",
    ])
    for row in latency:
        if row["trial"] == "pooled":
            lines.append(f"{int(row['catalog']):>7}    {NAMES[row['mode']]:<10} {int(row['requests']):>8}   "
                         f"{num(row['http_p50_ms']):>7} / {num(row['http_p95_ms']):<7}   "
                         f"{num(row['server_p50_ms']):>7} / {num(row['server_p95_ms']):<7}")
    lines.extend([
        "Три повтора на размер и режим, восемь одновременных клиентов Locust, пауза 50 мс между запросами "
        "одного клиента, восемь секунд на повтор. Случайный порядок воспроизводится по номеру повтора. "
        "HTTP измерен на loopback от клиента. Внутренний тайминг включает ожидание соединения, "
        "подготовку запроса и обход результата, HTTP дополнительно включает транспорт и сериализацию. "
        "В таблице объединены запросы повторов. Для порога использован худший p95 отдельного повтора.",
        "", "Граница применимости", "",
        f"Скрытые синонимы дали Recall@5 {percent(ranking['hybrid', 'hidden_synonym']['recall5'])} "
        f"у гибрида против {percent(ranking['pgvector', 'hidden_synonym']['recall5'])} у pgvector. "
        "Это контроль с 128-мерными хешированными символьными n-граммами, косинусным расстоянием "
        "и HNSW. Вывод относится к этому представлению. Семантические эмбеддинги требуют отдельного замера.",
        f"На 100 000 строк HTTP p95 составил {num(at_scale['hybrid']['http_p95_ms'])} мс "
        f"у гибрида и {num(at_scale['pgvector']['http_p95_ms'])} мс у pgvector. "
        "Для MVP гибрид подходит как основной вариант подсказок по покрытым классам. "
        "На этом стенде векторный индекс даёт альтернативный профиль задержки, "
        "сопоставимую общую полноту и слабое покрытие скрытых синонимов. "
        "Снижение DCR требует отдельно проверить выбор подсказок при записи.",
        "Быстрый поиск и автослияние оценивались раздельно. Каталог для ранжирования фиксирован, "
        "повторные операции записи воспроизводились последовательно поверх него в памяти. "
        "Пользовательский выбор подсказок и нагрузка конкурентной записи не измерялись.",
        "Каталог синтетический, а 10 000 и 100 000 строк получены за счёт добавления похожих серий. "
        "Выборка классов шума равномернее естественного трафика. Качество ранжирования измерено "
        "на каталоге из 1 000 строк. Данные пользовательского ввода и рабочий SLA приложения "
        "требуют отдельной валидации.",
        "", "Артефакты", "",
        "data/ — исходный каталог, запросы с целевыми ID и ловушками, история с эталоном.",
        "results/ranking.csv и recall-heatmap.png — метрики и карта полноты.",
        "results/merge-audit.csv и predictions.csv — решения по ловушкам и исходы каждого запроса.",
        "results/aggregation.csv — эталон, исходная и нормализованная суммы.",
        "results/latency.csv, latency-*.csv и hnsw-plan-*.txt — сводка, сырые замеры и планы.",
        "001_catalog.sql и 002_vector.sql — экспериментальные миграции PostgreSQL.",
        "backend/app/services/canonicalization.py и units.py — нормализация каталога и единиц.",
    ])
    (RESULTS / "report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
