"""Generate a fixed synthetic benchmark."""
import csv
from pathlib import Path
from random import Random

ROOT = Path(__file__).parent
DATA = ROOT / "data"
SEED = 402193
STEMS = """
йогурт кефир молоко творог сметана творожок сгущенка газировка шоколад печенье
колбаса макароны ряженка простокваша мороженое пломбир крем пудинг мусс суфле
зефир мармелад пастила вафли пряник кекс бисквит крекер эклер пончик
булочка рулет сироп джем повидло варенье сок нектар компот морс
лимонад кисель чай кофе какао желе конфеты халва козинаки ирис
каша хлопья мюсли гранола панкейки оладьи сырники блины запеканка торт
пирог пирожное тарт маффин брауни чизкейк макарун сорбет десерт парфе
батончик драже леденцы карамель помадка нуга трюфель глазурь топпинг начинка
паста соус дип хумус паштет салат котлеты пельмени равиоли вареники
пицца гренки хлебцы чипсы сушки сухари сухарики попкорн снеки хлеб
""".split()
VARIANTS = "ваниль клубника малина вишня персик яблоко банан лимон кокос карамель".split()
ABBR = dict(zip(STEMS[:12], "йог кеф мол твор смет сырок сгущ газвода шокол печ колб мак".split()))
HIDDEN = {
    "творог": "кисломолочный сыр", "сгущенка": "концентрированное подслащённое молоко",
    "газировка": "шипучий напиток", "зефир": "воздушная сладость из пюре",
    "пельмени": "мясо в тесте", "мюсли": "зерновая смесь для завтрака",
    "сухари": "сушёный хлеб", "ирис": "тянучка", "варенье": "плоды в сахаре",
    "морс": "ягодный отвар", "булочка": "сдоба", "оладьи": "жареные лепёшки",
    "карамель": "жжёный сахар",
}
SPECIAL = [
    ("масло сливочное", "масло оливковое"), ("молоко 2,5%", "молоко 3,2%"),
    ("йогурт без сахара", "йогурт с сахаром"), ("кофе молотый", "кофе растворимый"),
    ("лук репчатый", "лук зелёный"), ("рис пропаренный", "рис непропаренный"),
    ("молоко безлактозное", "молоко цельное"), ("перец красный", "перец чёрный"),
]


def fixture():
    rng = Random(SEED)
    entries = [(stem, variant) for stem in STEMS for variant in VARIANTS]
    names = [" ".join(pair) for pair in entries]
    names[-2 * len(SPECIAL):] = [name for pair in SPECIAL for name in pair]
    catalog = [(i, name) for i, name in enumerate(names, 1)]
    queries = []
    seen = set()

    def add(group, query, target, distractor=None, novel=None):
        if query not in seen:
            seen.add(query)
            queries.append((group, query, target, distractor, novel))

    for case_index, index in enumerate(rng.sample(range(984), 340)):
        stem, flavor = entries[index]
        target = index + 1
        brand = rng.choice(["добрый", "простоквашино", "домик в деревне", "чудо"])
        size = rng.choice(["500 г", "0,25 кг", "200мл", "1 л", "6 шт"])
        name = names[index]
        punctuation = (" ", " / ", " — ")[case_index % 3]
        add("case_punctuation", f" {stem.upper()}{punctuation}{flavor.upper()} ", target)
        pos = rng.randrange(len(stem) - 1)
        typo = (
            stem[:pos] + stem[pos + 1] + stem[pos] + stem[pos + 2:]
            if case_index % 2 == 0 else stem[:pos] + stem[pos + 1:]
        )
        add("typo", f"{typo} {flavor}", target)
        add("word_order", f"{flavor} {stem}", target)
        inflected = {
            "ваниль": "ванилью", "клубника": "клубники", "малина": "малиной",
            "вишня": "вишни", "персик": "персиком", "яблоко": "яблока",
            "банан": "бананом", "лимон": "лимона", "кокос": "кокосом",
            "карамель": "карамелью",
        }[flavor]
        add("morphology", f"{inflected} {stem}", target)
        add("known_brand_pack", f"{name} «{brand}» {size}", target)
        unknown = rng.choice(["Речной берег", "Северная ферма", "Лавка вкуса", "Лесной дом"])
        add("unknown_brand_pack", f"{unknown} {name} {size}", target)
    for index, (stem, flavor) in enumerate(entries[:984]):
        if stem in ABBR:
            add("abbreviation", f"{ABBR[stem]} {flavor}", index + 1)
        if stem in HIDDEN:
            add("hidden_synonym", f"{HIDDEN[stem]} {flavor}", index + 1)
    for index in rng.sample(range(984), 250):
        stem, flavor = entries[index]
        variant = rng.choice(["без сахара", "веганский", "копчёный", "обезжиренный"])
        add("trap_novel", f"{stem} {flavor} {variant}", None, index + 1, f"novel-{index}")
    for i, pair in enumerate(SPECIAL):
        for j, name in enumerate(pair):
            target = 985 + 2 * i + j
            add("trap_present", f"{name} 300 г", target, 985 + 2 * i + (1 - j))
    return catalog, queries


def write_csv(path, header, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerows(rows)


if __name__ == "__main__":
    DATA.mkdir(exist_ok=True)
    catalog, queries = fixture()
    write_csv(DATA / "catalog.csv", ["id", "name"], catalog)
    write_csv(DATA / "queries.csv", ["noise", "query", "target", "distractor", "novel"], queries)
