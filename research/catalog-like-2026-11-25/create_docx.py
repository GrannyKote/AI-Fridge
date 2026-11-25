from pathlib import Path
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).parent / 'results'
lines = (ROOT / 'report.txt').read_text(encoding='utf-8-sig').splitlines()
doc = Document()
section = doc.sections[0]
section.page_width, section.page_height = Cm(29.7), Cm(21)
section.top_margin = section.bottom_margin = Cm(1.5)
section.left_margin = section.right_margin = Cm(1.8)
for name in ('Normal', 'Title', 'Heading 1'):
    style = doc.styles[name]
    style.font.name = 'Arial'
    style.font.color.rgb = RGBColor(0, 0, 0)
doc.styles['Normal'].font.size = Pt(10)
doc.styles['Normal'].paragraph_format.space_after = Pt(5)
doc.styles['Normal'].paragraph_format.line_spacing = 1.05
doc.styles['Title'].font.size = Pt(21)
doc.styles['Heading 1'].font.size = Pt(14)

labels = {'baseline': 'LIKE', 'hybrid': 'Гибрид',
    'case_punctuation': 'Регистр и пунктуация', 'typo': 'Опечатки',
    'word_order': 'Порядок слов', 'morphology': 'Морфология',
    'known_brand_pack': 'Известный бренд и фасовка',
    'unknown_brand_pack': 'Неизвестный бренд и фасовка',
    'abbreviation': 'Сокращения', 'hidden_synonym': 'Скрытые синонимы',
    'trap_novel': 'Ловушки с новым продуктом', 'trap_present': 'Ловушки с продуктом в каталоге'}


def table(rows, widths, noise=False):
    t = doc.add_table(rows=0, cols=len(widths))
    t.autofit = False
    for column, width in zip(t.columns, widths):
        column.width = Cm(width)
    for index, values in enumerate(rows):
        cells = t.add_row().cells
        for col, (cell, text, width) in enumerate(zip(cells, values, widths)):
            cell.width = Cm(width)
            text = labels.get(text, text)
            if text == 'None':
                text = '—'
            elif noise and index > 0 and col >= 3:
                text = f'{float(text):.4f}'.replace('.', ',')
            cell.text = text
            cell.vertical_alignment = 1
            props = cell._tc.get_or_add_tcPr()
            shade = OxmlElement('w:shd')
            shade.set(qn('w:fill'), 'DBE5F1' if index == 0 else ('F3F6FA' if index % 2 == 0 else 'FFFFFF'))
            props.append(shade)
            borders = OxmlElement('w:tcBorders')
            for side in ('top', 'left', 'bottom', 'right'):
                edge = OxmlElement('w:' + side)
                for key, value in [('val', 'single'), ('sz', '4'), ('color', 'D9D9D9')]:
                    edge.set(qn('w:' + key), value)
                borders.append(edge)
            props.append(borders)
            for p in cell.paragraphs:
                p.paragraph_format.space_before = Pt(3)
                p.paragraph_format.space_after = Pt(3)
                p.alignment = 0 if col == 0 else 1
                for run in p.runs:
                    run.font.size = Pt(9)
                    run.bold = index == 0
        trpr = t.rows[-1]._tr.get_or_add_trPr()
        no_split = OxmlElement('w:cantSplit')
        trpr.append(no_split)
        if index == 0:
            trpr.append(OxmlElement('w:tblHeader'))
    doc.add_paragraph().paragraph_format.space_after = Pt(1)


doc.add_paragraph('Сравнение гибридного поиска и префиксного поиска LIKE', 'Title')
i = 1
while i < len(lines):
    line = lines[i].strip()
    i += 1
    if not line or line.startswith('Дата'):
        continue
    if line.startswith('Повторно использована'):
        line = 'Использована фиксированная выборка с seed 402193. Независимая внешняя выборка отсутствует.'
    if line == 'Метрики по классам шума':
        doc.add_page_break()
    if line.startswith('Задержка —'):
        doc.add_page_break()
    if line in ('Методика', 'Общие метрики', 'Метрики по классам шума', 'Критерии') or line.startswith('Задержка —'):
        doc.add_paragraph('Задержка автодополнения' if line.startswith('Задержка —') else line, 'Heading 1')
        if line == 'Метрики по классам шума':
            doc.add_paragraph('Значения Recall@5, Precision@5, MRR@5 и доли вводов с дублем приведены как доли единицы с округлением до четырёх знаков. Прочерк означает отсутствие применимого значения.')
        continue
    if ' | ' in line:
        rows = [[cell.strip() for cell in line.split('|')]]
        while i < len(lines) and ' | ' in lines[i]:
            rows.append([cell.strip() for cell in lines[i].split('|')])
            i += 1
        noise = rows[0][0] == 'Класс'
        widths = [6.1, 2.1, 1.4, 3.2, 3.4, 2.6, 7.3] if noise else ([3.1, 3.4, 3.4, 3.5, 3.4, 3.4, 3.9] if len(rows[0]) == 7 else [2.3, 2.4, 2.8, 8.5, 8.1])
        if noise:
            widths = [6.1, 2.1, 1.4, 3.2, 3.4, 2.6, 7.3]
            widths[-1] = 7.3 - 4
        table(rows, widths, noise)
        continue
    if line.startswith('DCR relative reduction'):
        criteria = []
        translated = {'DCR relative reduction > 20%': 'Относительное снижение DCR более 20%',
                      'Recall@5 >= 85%': 'Recall@5 не менее 85%',
                      'Recall gain >= 30 pp': 'Прирост Recall@5 не менее 30 п п',
                      'FMR <= 2%': 'FMR не более 2%', 'p95 <= 80 ms': 'p95 не более 80 мс'}
        entries = [line]
        while i < len(lines) and any(lines[i].startswith(key) for key in translated):
            entries.append(lines[i])
            i += 1
        for entry in entries:
            key, value = entry.split(' — ', 1)
            criteria.append([translated[key], value])
        table([['Критерий', 'Результат']] + criteria, [17, 9.1])
        continue
    doc.add_paragraph(line)

doc.core_properties.title = 'Сравнение гибридного поиска и префиксного поиска LIKE'
doc.core_properties.author = ''
doc.save(ROOT / 'report_adjusted.docx')
print(ROOT / 'report_adjusted.docx')



