# -*- coding: utf-8 -*-
"""把 Markdown 文档转成课程报告格式的 Word 文档。

用法：
    python tools/md2docx.py [输入.md] [输出.docx]

格式：中文宋体小四（12pt）、1.1 倍行距，英文 Times New Roman，
标题宋体加粗，表格带表头底纹与跨页重复表头。

支持：标题、段落、**加粗**、`代码`、*斜体*、无序/有序列表、引用块、
Markdown 表格、图片、``` 代码块、<!-- pagebreak --> 分页、--- 分隔线。
"""
import os
import re
import sys

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HEAD_FONT = '宋体'
BODY_FONT = '宋体'
CODE_FONT = 'Times New Roman'
LATIN_FONT = 'Times New Roman'
ACCENT = RGBColor(0x00, 0x00, 0x00)
ACCENT2 = RGBColor(0x00, 0x00, 0x00)
MUTED = RGBColor(0x59, 0x59, 0x59)
LINE_SPACING = 1.1
BODY_SIZE = 12


# ---------------------------------------------------------------- 基础工具
def set_run_font(run, name=BODY_FONT, latin=None):
    run.font.name = latin or LATIN_FONT
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn('w:rFonts'))
    if rfonts is None:
        rfonts = OxmlElement('w:rFonts')
        rpr.append(rfonts)
    rfonts.set(qn('w:eastAsia'), name)
    rfonts.set(qn('w:ascii'), latin or LATIN_FONT)
    rfonts.set(qn('w:hAnsi'), latin or LATIN_FONT)
    rfonts.set(qn('w:cs'), latin or LATIN_FONT)


def shade(element, color):
    """给段落或单元格加底色。element 需为 w:pPr 的容器或 tcPr。"""
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color)
    element.append(shd)


def cell_shade(cell, color):
    tcpr = cell._tc.get_or_add_tcPr()
    shade(tcpr, color)


def para_shade(paragraph, color):
    ppr = paragraph._p.get_or_add_pPr()
    shade(ppr, color)


def para_border_left(paragraph, color='2E6BB0', size=18):
    ppr = paragraph._p.get_or_add_pPr()
    borders = OxmlElement('w:pBdr')
    left = OxmlElement('w:left')
    left.set(qn('w:val'), 'single')
    left.set(qn('w:sz'), str(size))
    left.set(qn('w:space'), '8')
    left.set(qn('w:color'), color)
    borders.append(left)
    ppr.append(borders)


def para_border_bottom(paragraph, color='C9D8EA', size=8, space=4):
    ppr = paragraph._p.get_or_add_pPr()
    borders = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), str(size))
    bottom.set(qn('w:space'), str(space))
    bottom.set(qn('w:color'), color)
    borders.append(bottom)
    ppr.append(borders)


def add_field(paragraph, instr):
    run = paragraph.add_run()
    fld_begin = OxmlElement('w:fldChar')
    fld_begin.set(qn('w:fldCharType'), 'begin')
    instr_el = OxmlElement('w:instrText')
    instr_el.set(qn('xml:space'), 'preserve')
    instr_el.text = instr
    fld_end = OxmlElement('w:fldChar')
    fld_end.set(qn('w:fldCharType'), 'end')
    run._r.append(fld_begin)
    run._r.append(instr_el)
    run._r.append(fld_end)
    return run


# ---------------------------------------------------------------- 行内格式
INLINE = re.compile(r'(\*\*.+?\*\*|`[^`]+`|\*[^*]+\*)')


def add_inline(paragraph, text, size=BODY_SIZE, color=None, base_bold=False):
    for part in INLINE.split(text):
        if not part:
            continue
        if part.startswith('**') and part.endswith('**') and len(part) > 4:
            run = paragraph.add_run(part[2:-2])
            run.bold = True
            set_run_font(run, BODY_FONT)
        elif part.startswith('`') and part.endswith('`') and len(part) > 2:
            run = paragraph.add_run(part[1:-1])
            set_run_font(run, CODE_FONT, latin=CODE_FONT)
            run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
        elif part.startswith('*') and part.endswith('*') and len(part) > 2:
            run = paragraph.add_run(part[1:-1])
            run.italic = True
            set_run_font(run, BODY_FONT)
        else:
            run = paragraph.add_run(part)
            set_run_font(run, BODY_FONT)
            if base_bold:
                run.bold = True
        run.font.size = Pt(size)
        if color is not None:
            run.font.color.rgb = color


# ---------------------------------------------------------------- 文档样式
def setup_styles(doc):
    normal = doc.styles['Normal']
    normal.font.name = BODY_FONT
    normal.font.size = Pt(BODY_SIZE)
    normal.element.rPr.rFonts.set(qn('w:eastAsia'), BODY_FONT)
    fmt = normal.paragraph_format
    fmt.line_spacing = LINE_SPACING
    fmt.space_before = Pt(0)
    fmt.space_after = Pt(0)

    specs = {
        'Heading 1': (18, ACCENT, 6, 6),
        'Heading 2': (15, ACCENT, 12, 6),
        'Heading 3': (13, ACCENT2, 10, 4),
        'Heading 4': (12, ACCENT2, 8, 3),
    }
    for name, (size, color, before, after) in specs.items():
        st = doc.styles[name]
        st.font.name = HEAD_FONT
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = color
        st.element.rPr.rFonts.set(qn('w:eastAsia'), HEAD_FONT)
        st.element.rPr.rFonts.set(qn('w:ascii'), LATIN_FONT)
        st.element.rPr.rFonts.set(qn('w:hAnsi'), LATIN_FONT)
        st.paragraph_format.space_before = Pt(before)
        st.paragraph_format.space_after = Pt(after)
        st.paragraph_format.keep_with_next = True
        st.paragraph_format.line_spacing = LINE_SPACING

    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(2.6)
    section.right_margin = Cm(2.6)
    section.header_distance = Cm(1.2)
    section.footer_distance = Cm(1.2)


def setup_header_footer(doc, title):
    header = doc.sections[0].header
    p = header.paragraphs[0]
    p.text = ''
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = p.add_run(title)
    set_run_font(run, BODY_FONT)
    run.font.size = Pt(8.5)
    run.font.color.rgb = MUTED
    para_border_bottom(p)

    footer = doc.sections[0].footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = fp.add_run('— ')
    set_run_font(r1, BODY_FONT)
    r1.font.size = Pt(8.5)
    r1.font.color.rgb = MUTED
    r2 = add_field(fp, 'PAGE')
    set_run_font(r2, BODY_FONT)
    r2.font.size = Pt(8.5)
    r2.font.color.rgb = MUTED
    r3 = fp.add_run(' —')
    set_run_font(r3, BODY_FONT)
    r3.font.size = Pt(8.5)
    r3.font.color.rgb = MUTED


# ---------------------------------------------------------------- 表格
def compute_widths(rows, total_cm=16.2):
    """按内容长度给每列分配宽度（cm），避免 # 列过宽、长文本列被压扁。"""
    n = len(rows[0])
    weights = []
    for i in range(n):
        vals = []
        for r in rows:
            cell = r[i] if i < len(r) else ''
            vals.append(len(re.sub(r'[*`]', '', cell)))
        body = vals[1:] or vals
        avg = sum(body) / max(len(body), 1)
        has_rating = any(('●' in (r[i] if i < len(r) else '')) or
                         ('○' in (r[i] if i < len(r) else '')) for r in rows)
        head_len = len(re.sub(r'[*`]', '', rows[0][i])) if i < len(rows[0]) else 0
        if max(body) <= 3 and head_len <= 2 and not has_rating:   # 序号 / 周次 这类极短列
            weights.append(0.7)
            continue
        weights.append(2.0 + min(9.0, (avg ** 0.5) * 1.1))
    scale = total_cm / sum(weights)
    widths = [w * scale for w in weights]
    # 保证最小宽度，差额从其它列按比例扣
    MIN_W = 1.3
    for _ in range(3):
        excess = sum(max(0.0, MIN_W - w) for w in widths)
        if excess <= 1e-6:
            break
        widths = [max(MIN_W, w) for w in widths]
        flexible = [i for i, w in enumerate(widths) if w > MIN_W + 1e-6]
        tot = sum(widths[i] for i in flexible) or 1.0
        for i in flexible:
            widths[i] -= excess * widths[i] / tot
    return widths


def add_table(doc, rows):
    header, body = rows[0], rows[1:]
    ncols = len(header)
    table = doc.add_table(rows=1, cols=ncols)
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    widths = compute_widths(rows)
    tbl_pr = table._tbl.tblPr
    layout = OxmlElement('w:tblLayout')
    layout.set(qn('w:type'), 'fixed')
    tbl_pr.append(layout)

    for i in range(ncols):
        table.columns[i].width = Cm(widths[i])

    hdr = table.rows[0]
    tr_pr = hdr._tr.get_or_add_trPr()
    tbl_header = OxmlElement('w:tblHeader')
    tbl_header.set(qn('w:val'), 'true')
    tr_pr.append(tbl_header)
    cant = OxmlElement('w:cantSplit')
    tr_pr.append(cant)

    font_size = 9.5 if ncols <= 4 else 9.0

    for i, text in enumerate(header):
        cell = hdr.cells[i]
        cell.width = Cm(widths[i])
        cell_shade(cell, '1F3A5F')
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.1
        r = p.add_run(re.sub(r'[*`]', '', text))
        set_run_font(r, HEAD_FONT)
        r.bold = True
        r.font.size = Pt(font_size)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    for row in body:
        cells = table.add_row().cells
        tr = table.rows[-1]._tr
        tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
        for i in range(ncols):
            text = row[i] if i < len(row) else ''
            cell = cells[i]
            cell.width = Cm(widths[i])
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.12
            add_inline(p, text, size=font_size)
            if re.fullmatch(r'[●○]{3}', text.strip()):
                for run in p.runs:
                    run.font.size = Pt(11)
            if i == 0:
                for run in p.runs:
                    run.bold = True

    # 交替行底色
    for idx, row in enumerate(table.rows[1:]):
        if idx % 2 == 1:
            for cell in row.cells:
                cell_shade(cell, 'F4F7FB')

    # 小表整表不拆页：除最后一行外都设置 keepNext
    if len(rows) <= 4:
        for row in table.rows[:-1]:
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.keep_with_next = True
    return table


# ---------------------------------------------------------------- 主流程
def build(md_path, docx_path):
    with open(md_path, encoding='utf-8') as fh:
        lines = fh.read().splitlines()

    doc = Document()
    setup_styles(doc)
    doc_title = next((ln.lstrip('# ').strip() for ln in lines if ln.startswith('# ')), '文档')
    setup_header_footer(doc, doc_title)

    base_dir = os.path.dirname(os.path.abspath(md_path))
    table_buf = []
    quote_buf = []
    first_h1 = True

    def flush_table():
        if table_buf:
            add_table(doc, table_buf)
            table_buf.clear()
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.0

    def flush_quote():
        if quote_buf:
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.6)
            p.paragraph_format.right_indent = Cm(0.4)
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(8)
            p.paragraph_format.line_spacing = 1.35
            para_shade(p, 'EEF3F9')
            para_border_left(p)
            for idx, qline in enumerate(quote_buf):
                if idx:
                    p.add_run().add_break()
                add_inline(p, qline, size=BODY_SIZE)
            quote_buf.clear()

    in_code = False
    code_buf = []

    def flush_code():
        if not code_buf:
            return
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.6)
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(8)
        p.paragraph_format.line_spacing = 1.0
        para_shade(p, 'F2F2F2')
        for idx, cline in enumerate(code_buf):
            if idx:
                p.add_run().add_break()
            run = p.add_run(cline)
            set_run_font(run, '宋体', latin='Consolas')
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
        code_buf.clear()

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()

        if stripped.startswith('```'):
            if in_code:
                flush_code()
                in_code = False
            else:
                flush_table()
                flush_quote()
                in_code = True
            continue
        if in_code:
            code_buf.append(line)
            continue

        if stripped.startswith('|'):
            if re.fullmatch(r'\|[\s:|-]+\|', stripped):
                continue
            cells = [c.strip() for c in stripped.strip('|').split('|')]
            table_buf.append(cells)
            continue
        flush_table()

        if stripped.startswith('>'):
            quote_buf.append(stripped.lstrip('>').strip())
            continue
        flush_quote()

        if not stripped:
            flush_quote()
            continue
        if stripped.startswith('<!--'):
            if 'pagebreak' in stripped:
                doc.add_page_break()
            continue
        if set(stripped) <= {'-'} and len(stripped) >= 3:
            continue

        img = re.match(r'!\[(.*?)\]\((.+?)\)', stripped)
        if img:
            path = os.path.join(base_dir, img.group(2))
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(2)
            p.add_run().add_picture(path, width=Cm(15.6))
            continue

        if stripped.startswith('#'):
            level = len(stripped) - len(stripped.lstrip('#'))
            text = stripped[level:].strip()
            level = min(level, 4)
            if level == 1 and first_h1:
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(48)
                p.paragraph_format.space_after = Pt(10)
                run = p.add_run(text)
                set_run_font(run, HEAD_FONT)
                run.font.size = Pt(26)
                run.bold = True
                run.font.color.rgb = ACCENT
                first_h1 = False
                continue
            h = doc.add_heading(level=level)
            add_inline(h, text, size={1: 18, 2: 15, 3: 13, 4: 12}[level],
                       color={1: ACCENT, 2: ACCENT, 3: ACCENT2, 4: ACCENT2}[level])
            for run in h.runs:
                run.bold = True
                run.font.color.rgb = {1: ACCENT, 2: ACCENT, 3: ACCENT2, 4: ACCENT2}[level]
            if level == 2:
                para_border_bottom(h)
            continue

        if stripped.startswith('- ') or stripped.startswith('* '):
            p = doc.add_paragraph(style='List Bullet')
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.35
            add_inline(p, stripped[2:].strip(), size=BODY_SIZE)
            continue

        m = re.match(r'(\d+)\.\s+(.*)', stripped)
        if m:
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.95)
            p.paragraph_format.first_line_indent = Cm(-0.55)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.line_spacing = 1.4
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            num = p.add_run(f'{m.group(1)}. ')
            set_run_font(num, BODY_FONT)
            num.font.size = Pt(BODY_SIZE)
            num.bold = True
            add_inline(p, m.group(2), size=BODY_SIZE)
            continue

        # 普通段落
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(0.74)
        p.paragraph_format.space_after = Pt(5)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        add_inline(p, stripped, size=BODY_SIZE)
        if re.fullmatch(r'\*\*.+\*\*', stripped):
            p.paragraph_format.keep_with_next = True

    flush_table()
    flush_quote()
    flush_code()
    doc.save(docx_path)
    print('saved:', docx_path)


if __name__ == '__main__':
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join('docs', '换数据方案与项目目的文档.md')
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join('docs', '换数据方案与项目目的文档.docx')
    build(src, dst)
