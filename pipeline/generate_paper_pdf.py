#!/usr/bin/env python3
"""
generate_paper_pdf.py -- Generate professional PDF from paper.md using ReportLab
Usage: python generate_paper_pdf.py [--input paper.md] [--output skillgym-paper.pdf]
"""
import argparse
import os
import re
import sys

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, inch
from reportlab.lib.colors import HexColor, Color
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, HRFlowable, Flowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, String, Line

# ── Brand Tokens ──────────────────────────────────────────────────────────────
ACCENT = HexColor("#3B82F6")
BG = HexColor("#080808")
SURFACE = HexColor("#121212")
CARD = HexColor("#141414")
BORDER = HexColor("#2A2A2A")
TEXT = HexColor("#1A1A1A")       # Dark text for print (not white)
TEXT_SEC = HexColor("#4B5563")
TEXT_MUTED = HexColor("#6B7280")
LIGHT_BG = HexColor("#F9FAFB")

PAGE_W, PAGE_H = A4
MARGIN = 25 * mm


# ── Styles ────────────────────────────────────────────────────────────────────
def build_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        'PaperTitle', fontName='Helvetica-Bold', fontSize=22, leading=28,
        textColor=TEXT, spaceAfter=6, alignment=TA_CENTER
    ))
    styles.add(ParagraphStyle(
        'PaperSubtitle', fontName='Helvetica', fontSize=12, leading=16,
        textColor=TEXT_SEC, spaceAfter=4, alignment=TA_CENTER
    ))
    styles.add(ParagraphStyle(
        'PaperMeta', fontName='Helvetica', fontSize=9, leading=13,
        textColor=TEXT_MUTED, spaceAfter=3, alignment=TA_CENTER
    ))
    styles.add(ParagraphStyle(
        'SectionHead', fontName='Helvetica-Bold', fontSize=14, leading=18,
        textColor=TEXT, spaceBefore=18, spaceAfter=8
    ))
    styles.add(ParagraphStyle(
        'SubsectionHead', fontName='Helvetica-Bold', fontSize=11, leading=15,
        textColor=TEXT, spaceBefore=12, spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        'BodyText2', fontName='Helvetica', fontSize=10, leading=15,
        textColor=TEXT, spaceAfter=6, alignment=TA_JUSTIFY
    ))
    styles.add(ParagraphStyle(
        'AbstractText', fontName='Helvetica-Oblique', fontSize=10, leading=15,
        textColor=TEXT_SEC, spaceAfter=6, alignment=TA_JUSTIFY,
        leftIndent=15, rightIndent=15
    ))
    styles.add(ParagraphStyle(
        'ListItem', fontName='Helvetica', fontSize=10, leading=15,
        textColor=TEXT, spaceAfter=3, leftIndent=20, bulletIndent=8
    ))
    styles.add(ParagraphStyle(
        'CodeBlock', fontName='Courier', fontSize=8.5, leading=12,
        textColor=TEXT_SEC, spaceAfter=6, leftIndent=15, rightIndent=15,
        backColor=LIGHT_BG, borderPadding=6
    ))
    styles.add(ParagraphStyle(
        'RefText', fontName='Helvetica', fontSize=9, leading=13,
        textColor=TEXT_SEC, spaceAfter=3, leftIndent=20, firstLineIndent=-20
    ))
    styles.add(ParagraphStyle(
        'FooterStyle', fontName='Helvetica', fontSize=8, leading=10,
        textColor=TEXT_MUTED
    ))
    styles.add(ParagraphStyle(
        'TableHeader', fontName='Helvetica-Bold', fontSize=9, leading=12,
        textColor=TEXT_SEC
    ))
    styles.add(ParagraphStyle(
        'TableCell', fontName='Helvetica', fontSize=9, leading=12,
        textColor=TEXT
    ))
    return styles


# ── Page Template ─────────────────────────────────────────────────────────────
def header_footer(canvas_obj, doc):
    canvas_obj.saveState()
    # Header
    canvas_obj.setFont('Helvetica', 8)
    canvas_obj.setFillColor(TEXT_MUTED)
    canvas_obj.drawString(MARGIN, PAGE_H - 15 * mm, "4M Labs Research")
    canvas_obj.drawRightString(PAGE_W - MARGIN, PAGE_H - 15 * mm, "Working Paper, July 2026")
    # Header line
    canvas_obj.setStrokeColor(BORDER)
    canvas_obj.setLineWidth(0.5)
    canvas_obj.line(MARGIN, PAGE_H - 17 * mm, PAGE_W - MARGIN, PAGE_H - 17 * mm)
    # Footer
    canvas_obj.setFont('Helvetica', 8)
    canvas_obj.setFillColor(TEXT_MUTED)
    canvas_obj.drawString(MARGIN, 15 * mm, "hello@4mlabs.io")
    canvas_obj.drawRightString(PAGE_W - MARGIN, 15 * mm, f"Page {doc.page}")
    # Footer line
    canvas_obj.line(MARGIN, 18 * mm, PAGE_W - MARGIN, 18 * mm)
    canvas_obj.restoreState()


def title_page_callback(canvas_obj, doc):
    """No header/footer on title page."""
    pass


# ── Markdown Parser ───────────────────────────────────────────────────────────
def clean_text(text):
    """Remove extra whitespace from markdown text."""
    text = re.sub(r'  +', ' ', text)
    return text.strip()


def md_to_html(text):
    """Convert minimal markdown to ReportLab HTML tags."""
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    # Italic
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    # Inline code
    text = re.sub(r'`(.+?)`', r'<font face="Courier" size="9">\1</font>', text)
    return text


def parse_paper(filepath):
    """Parse paper.md into structured sections."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove the重复 header/footer lines that were in the PDF export
    # These are: "4M Labs Research", "Working Paper, July 2026", "hello@4mlabs.io", "Page N"
    lines = content.split('\n')
    cleaned = []
    skip_patterns = [
        '4M Labs Research',
        'Working Paper, July 2026',
        'hello@4mlabs.io',
    ]
    for line in lines:
        stripped = line.strip()
        if stripped in skip_patterns:
            continue
        if re.match(r'^Page \d+$', stripped):
            continue
        cleaned.append(line)

    content = '\n'.join(cleaned)

    # Extract title block (everything before "Abstract")
    abstract_match = re.search(r'^Abstract\s*$', content, re.MULTILINE)
    if not abstract_match:
        print("ERROR: Could not find 'Abstract' section", file=sys.stderr)
        sys.exit(1)

    title_block = content[:abstract_match.start()].strip()
    body = content[abstract_match.end():].strip()

    # Parse title block
    title_lines = [l.strip() for l in title_block.split('\n') if l.strip()]
    title_data = {}
    for line in title_lines:
        if line.startswith('Authors:'):
            title_data['authors'] = line.replace('Authors:', '').strip()
        elif line.startswith('Affiliation:'):
            title_data['affiliation'] = line.replace('Affiliation:', '').strip()
        elif line.startswith('Date:'):
            title_data['date'] = line.replace('Date:', '').strip()
        elif line.startswith('Status:'):
            title_data['status'] = line.replace('Status:', '').strip()
        elif line.startswith('Corresponding Author:'):
            title_data['corresponding'] = line.replace('Corresponding Author:', '').strip()
        elif line.startswith('Cite as:'):
            title_data['cite'] = line.replace('Cite as:', '').strip()
        elif 'Public Agent Skills' in line:
            title_data['title'] = line
        elif 'Framework for Extracting' in line:
            title_data['subtitle'] = line

    # Parse body into sections
    sections = []
    current_section = None
    current_content = []

    prev_was_empty = True  # Start as if previous line was empty (start of block)
    for line in body.split('\n'):
        stripped = line.strip()

        # Track if previous line was empty (block boundary)
        if not stripped:
            prev_was_empty = True
            current_content.append(line)
            continue

        # Section heading: must be at block start AND match pattern
        # Section headings are standalone lines like "1. Introduction: Skills as Procedural Policies"
        # NOT list items like "1. Skill optimization: Improving the skill itself. ..."
        section_match = None
        subsection_match = None

        if prev_was_empty:
            # Only check for section/subsection at block boundaries
            subsection_match = re.match(r'^(\d+\.\d+)\s+(.{3,30})$', stripped)
            if not subsection_match:
                section_match = re.match(r'^(\d+)\.\s+(.{3,40})$', stripped)
                # Extra validation: section titles should be short and not start with lowercase
                if section_match:
                    title = section_match.group(2)
                    # If title is too long or starts with lowercase, it's a list item
                    if len(title) > 40 or title[0].islower():
                        section_match = None

        prev_was_empty = False

        if section_match and not subsection_match:
            if current_section:
                sections.append({
                    'type': 'section',
                    'number': current_section['number'],
                    'title': current_section['title'],
                    'content': '\n'.join(current_content).strip()
                })
            current_section = {
                'number': section_match.group(1),
                'title': section_match.group(2)
            }
            current_content = []
        elif subsection_match:
            if current_content:
                sections.append({
                    'type': 'subsection',
                    'number': current_section['number'] if current_section else '',
                    'title': current_section['title'] if current_section else '',
                    'content': '\n'.join(current_content).strip()
                })
                current_content = []
            current_section = {
                'number': subsection_match.group(1),
                'title': subsection_match.group(2)
            }
            current_content = []
        elif line.strip() == 'References':
            if current_section:
                sections.append({
                    'type': 'section',
                    'number': current_section['number'],
                    'title': current_section['title'],
                    'content': '\n'.join(current_content).strip()
                })
            current_section = {'number': '', 'title': 'References'}
            current_content = []
        else:
            current_content.append(line)

    # Append last section
    if current_section:
        sections.append({
            'type': 'section',
            'number': current_section['number'],
            'title': current_section['title'],
            'content': '\n'.join(current_content).strip()
        })

    return title_data, sections


# ── Table Detection ───────────────────────────────────────────────────────────
def is_pipe_table_line(line):
    """Check if a line looks like a pipe-delimited table row."""
    stripped = line.strip()
    if not stripped:
        return False
    if re.match(r'^[\|\-+\s:]+$', stripped):
        return True
    if '|' in stripped and stripped.count('|') >= 2:
        return True
    return False


def is_whitespace_table_block(lines, start_idx):
    """Check if a block of lines starting at start_idx forms a whitespace-aligned table.
    Returns (is_table, end_idx) where end_idx is the line after the last table line."""
    if start_idx >= len(lines):
        return False, start_idx

    header = lines[start_idx].strip()
    if not header or len(header) < 10:
        return False, start_idx

    # Check if header has columns separated by 2+ spaces
    header_cols = re.split(r'\s{2,}', header)
    if len(header_cols) < 2:
        return False, start_idx

    # Heuristic: real table headers have short cells (1-15 chars avg)
    avg_word_len = sum(len(c) for c in header_cols) / len(header_cols)
    if avg_word_len > 15:
        return False, start_idx

    # Check that cells look like table data (short words, numbers, not prose)
    # Prose lines have articles, prepositions, long words
    prose_indicators = ['the', 'a', 'an', 'is', 'are', 'was', 'were', 'of', 'in', 'to',
                        'for', 'and', 'or', 'but', 'not', 'with', 'from', 'that', 'this',
                        'which', 'what', 'when', 'where', 'how', 'they', 'their', 'there']
    header_lower = [c.lower() for c in header_cols]
    prose_count = sum(1 for c in header_lower if c in prose_indicators)
    if prose_count > len(header_cols) * 0.3:
        return False, start_idx

    # Count how many subsequent lines match the column pattern
    table_lines = [start_idx]
    i = start_idx + 1
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            break  # Empty line ends the table

        cols = re.split(r'\s{2,}', line)
        if len(cols) < 2:
            break

        # Check column count matches header
        if len(cols) != len(header_cols):
            break

        # Check that this line also doesn't look like prose
        line_lower = [c.lower() for c in cols]
        line_prose = sum(1 for c in line_lower if c in prose_indicators)
        if line_prose > len(cols) * 0.3:
            break

        table_lines.append(i)
        i += 1

    # Need at least header + 1 data line
    if len(table_lines) >= 2:
        return True, i

    return False, start_idx


def parse_whitespace_table(lines):
    """Parse whitespace-aligned table lines into rows."""
    rows = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Split on 2+ spaces
        cells = re.split(r'\s{2,}', stripped)
        cells = [c.strip() for c in cells if c.strip()]
        if cells:
            rows.append(cells)
    return rows


def parse_pipe_table(lines):
    """Parse pipe-delimited table lines into rows."""
    rows = []
    for line in lines:
        stripped = line.strip()
        if re.match(r'^[\|\-+\s:]+$', stripped):
            continue
        if '|' in stripped:
            cells = [c.strip() for c in stripped.split('|')]
            if cells and cells[0] == '':
                cells = cells[1:]
            if cells and cells[-1] == '':
                cells = cells[:-1]
            if cells:
                rows.append(cells)
    return rows


def build_table_flowable(rows, styles):
    """Build a ReportLab Table from parsed rows."""
    if not rows:
        return None

    num_cols = max(len(r) for r in rows)
    # Pad rows
    for r in rows:
        while len(r) < num_cols:
            r.append('')

    # Calculate column widths
    available = PAGE_W - 2 * MARGIN
    col_width = available / num_cols
    col_widths = [col_width] * num_cols

    # Build table data with Paragraphs
    table_data = []
    for i, row in enumerate(rows):
        table_row = []
        for cell in row:
            cell_text = clean_text(md_to_html(cell))
            if i == 0:
                style = ParagraphStyle('th', parent=styles['TableHeader'],
                                       fontName='Helvetica-Bold', fontSize=9)
            else:
                style = ParagraphStyle('td', parent=styles['TableCell'],
                                       fontName='Helvetica', fontSize=9)
            table_row.append(Paragraph(cell_text, style))
        table_data.append(table_row)

    t = Table(table_data, colWidths=col_widths)
    style_cmds = [
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (-1, 0), TEXT_SEC),
        ('TEXTCOLOR', (0, 1), (-1, -1), TEXT),
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_BG),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor("#FFFFFF"), LIGHT_BG]),
        ('LINEBELOW', (0, 0), (-1, 0), 1, BORDER),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER),
    ]
    t.setStyle(TableStyle(style_cmds))
    return t


# ── Chart Helpers ─────────────────────────────────────────────────────────────
def make_chart_flowable(chart_func, caption, width=440, height=240):
    """Create a chart drawing and wrap it with a caption."""
    drawing = chart_func(width, height)
    elements = [drawing, Spacer(1, 2 * mm)]
    if caption:
        elements.append(Paragraph(
            f'<i>{caption}</i>',
            ParagraphStyle('ChartCaption', fontName='Helvetica-Oblique', fontSize=8,
                           leading=11, textColor=TEXT_MUTED, alignment=TA_CENTER, spaceAfter=4)
        ))
        elements.append(Spacer(1, 3 * mm))
    return elements


def _draw_bar_group(d, x, y, w, h, values, colors, labels, title, zero_val=0, val_min=None, val_max=None, val_step=None, angle=0):
    """Draw a grouped bar chart manually with Rect shapes."""
    # Title
    d.add(String(x, y + h + 15, title, fontName='Helvetica-Bold', fontSize=9, fillColor=TEXT))

    chart_x = x + 55
    chart_y = y + 35
    chart_w = w - 80
    chart_h = h - 50

    if val_min is None:
        val_min = min(0, min(v for row in values for v in row))
    if val_max is None:
        val_max = max(v for row in values for v in row) * 1.2
    if val_step is None:
        val_step = (val_max - val_min) / 5

    # Axes
    d.add(Line(chart_x, chart_y, chart_x + chart_w, chart_y, strokeColor=BORDER, strokeWidth=0.5))
    d.add(Line(chart_x, chart_y, chart_x, chart_y + chart_h, strokeColor=BORDER, strokeWidth=0.5))

    # Y-axis labels and gridlines
    val_range = val_max - val_min
    if val_range == 0:
        val_range = 1
    for v_raw in _frange(val_min, val_max + val_step * 0.01, val_step):
        fy = chart_y + ((v_raw - val_min) / val_range) * chart_h
        d.add(Line(chart_x - 3, fy, chart_x, fy, strokeColor=TEXT_SEC, strokeWidth=0.5))
        label = f'{v_raw:.2f}' if abs(v_raw) < 1 else f'{v_raw:.1f}'
        d.add(String(chart_x - 35, fy - 4, label, fontName='Helvetica', fontSize=7, fillColor=TEXT_SEC))
        if v_raw != val_min:
            d.add(Line(chart_x, fy, chart_x + chart_w, fy, strokeColor=HexColor("#E5E7EB"), strokeWidth=0.3, strokeDashArray=[2, 2]))

    # Zero line
    zero_y = chart_y + ((zero_val - val_min) / val_range) * chart_h
    if zero_val != val_min:
        d.add(Line(chart_x, zero_y, chart_x + chart_w, zero_y, strokeColor=TEXT_MUTED, strokeWidth=0.5, strokeDashArray=[4, 3]))

    # Bars
    n_groups = len(values[0])
    n_bars = len(values)
    group_w = chart_w / n_groups
    bar_w = min(group_w * 0.7 / n_bars, 25)
    group_gap = group_w * 0.15

    for gi in range(n_groups):
        group_x = chart_x + gi * group_w + group_gap
        for bi in range(n_bars):
            val = values[bi][gi]
            bar_x = group_x + bi * (bar_w + 2)
            bar_bottom = max(zero_y, chart_y + ((val - val_min) / val_range) * chart_h)
            bar_top = min(zero_y, chart_y + ((val - val_min) / val_range) * chart_h)
            bar_h_actual = abs(bar_bottom - bar_top)
            if bar_h_actual < 1:
                bar_h_actual = 1
            d.add(Rect(bar_x, bar_bottom, bar_w, bar_h_actual, fillColor=colors[bi], strokeColor=None))

        # Category label
        label_x = group_x + (n_bars * (bar_w + 2)) / 2
        if angle:
            d.add(String(label_x, chart_y - 15, labels[gi], fontName='Helvetica', fontSize=7, fillColor=TEXT, textAnchor='middle'))
        else:
            d.add(String(label_x - 10, chart_y - 12, labels[gi], fontName='Helvetica', fontSize=8, fillColor=TEXT))

    # Legend
    legend_x = chart_x + chart_w - 80
    legend_y = chart_y + chart_h + 8
    for bi in range(n_bars):
        lx = legend_x + bi * 55
        d.add(Rect(lx, legend_y, 8, 8, fillColor=colors[bi], strokeColor=None))
        d.add(String(lx + 12, legend_y + 1, labels[-1] if bi >= len(labels) else '', fontName='Helvetica', fontSize=7, fillColor=TEXT))


def _frange(start, stop, step):
    """Float range generator."""
    vals = []
    v = start
    while v <= stop + step * 0.001:
        vals.append(round(v, 6))
        v += step
    return vals


def chart_sft_vs_dpo(w, h):
    """Bar chart: SFT vs DPO delta per skill."""
    d = Drawing(w, h)
    _draw_bar_group(d, 0, 0, w, h,
        values=[[0.108, 0.064, -0.001], [0.021, -0.021, 0.020]],
        colors=[ACCENT, HexColor("#F59E0B")],
        labels=['Cold-email', 'Copywriting', 'CRO'],
        title='',
        zero_val=0, val_min=-0.05, val_max=0.15, val_step=0.05)
    d.add(String(0, h - 5, 'SFT vs DPO Improvement by Skill', fontName='Helvetica-Bold', fontSize=9, fillColor=TEXT))
    return d


def chart_base_vs_sft(w, h):
    """Bar chart: Base vs SFT composite score per skill."""
    d = Drawing(w, h)
    _draw_bar_group(d, 0, 0, w, h,
        values=[[0.210, 0.311, 0.412], [0.318, 0.375, 0.410]],
        colors=[HexColor("#9CA3AF"), ACCENT],
        labels=['Cold-email', 'Copywriting', 'CRO'],
        title='',
        zero_val=0, val_min=0, val_max=0.5, val_step=0.1)
    d.add(String(0, h - 5, 'Base vs SFT Composite Score by Skill', fontName='Helvetica-Bold', fontSize=9, fillColor=TEXT))
    return d


def chart_top_improvers(w, h):
    """Bar chart: Top 5 task improvements."""
    d = Drawing(w, h)
    _draw_bar_group(d, 0, 0, w, h,
        values=[[0.225, 0.199, 0.190, 0.185, 0.174]],
        colors=[HexColor("#10B981")],
        labels=['cro_004', 'copy_008', 'cold_010', 'copy_007', 'copy_009'],
        title='',
        zero_val=0, val_min=0, val_max=0.25, val_step=0.05)
    d.add(String(0, h - 5, 'Top 5 Task Improvements (SFT Delta)', fontName='Helvetica-Bold', fontSize=9, fillColor=TEXT))
    return d


def chart_per_dimension(w, h):
    """Bar chart: Per-dimension improvement (DPO)."""
    d = Drawing(w, h)
    _draw_bar_group(d, 0, 0, w, h,
        values=[[0.054, 0.013, 0.006, -0.008, -0.005, -0.005]],
        colors=[ACCENT],
        labels=['Voice', 'Criteria', 'Specificity', 'Actionability', 'Structure', 'Depth'],
        title='',
        zero_val=0, val_min=-0.02, val_max=0.07, val_step=0.02)
    d.add(String(0, h - 5, 'DPO Per-Dimension Improvement', fontName='Helvetica-Bold', fontSize=9, fillColor=TEXT))
    return d


# ── Content Builder ───────────────────────────────────────────────────────────
def build_content(title_data, sections, styles):
    """Build the PDF story from parsed paper data."""
    story = []

    # ── Title Page ────────────────────────────────────────────────────────
    story.append(Spacer(1, 60 * mm))
    story.append(Paragraph("4M Labs Research", styles['PaperMeta']))
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph(title_data.get('title', 'Paper Title'), styles['PaperTitle']))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(title_data.get('subtitle', ''), styles['PaperSubtitle']))
    story.append(Spacer(1, 10 * mm))
    story.append(HRFlowable(width="40%", thickness=1, color=ACCENT, spaceAfter=10))
    story.append(Paragraph(f"Authors: {title_data.get('authors', '4M Labs Research')}", styles['PaperMeta']))
    story.append(Paragraph(f"Affiliation: {title_data.get('affiliation', '4M Labs')}", styles['PaperMeta']))
    story.append(Paragraph(f"Date: {title_data.get('date', 'July 2026')}", styles['PaperMeta']))
    story.append(Paragraph(f"Status: {title_data.get('status', 'Working Paper')}", styles['PaperMeta']))
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph(f"Corresponding Author: {title_data.get('corresponding', 'hello@4mlabs.io')}", styles['PaperMeta']))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(f"<i>{title_data.get('cite', '')}</i>", styles['PaperMeta']))
    story.append(PageBreak())

    # ── Abstract ──────────────────────────────────────────────────────────
    # Find abstract section
    for section in sections:
        if section['title'] == 'Abstract' or (section['number'] == '' and 'Abstract' in section.get('content', '')[:50]):
            story.append(Paragraph("Abstract", styles['SectionHead']))
            story.append(Spacer(1, 3 * mm))
            abstract_text = clean_text(md_to_html(section['content']))
            # Split into paragraphs
            for para in abstract_text.split('\n\n'):
                para = para.strip()
                if para:
                    story.append(Paragraph(abstract_text, styles['AbstractText']))
                    break  # Abstract is one block
            story.append(Spacer(1, 5 * mm))
            break

    # ── Body Sections ─────────────────────────────────────────────────────
    for section in sections:
        title = section['title']
        content = section['content']

        # Skip abstract (already rendered)
        if title == 'Abstract':
            continue

        # Section heading
        if section['number']:
            heading = f"{section['number']}. {title}"
        else:
            heading = title

        story.append(Paragraph(heading, styles['SectionHead']))
        story.append(Spacer(1, 2 * mm))

        # Track which charts have been inserted
        charts_inserted = set()

        # Parse content into paragraphs, lists, code blocks, and tables
        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Empty line
            if not stripped:
                i += 1
                continue

            # Pipe table detection
            if is_pipe_table_line(stripped):
                table_lines = []
                while i < len(lines) and is_pipe_table_line(lines[i].strip()):
                    table_lines.append(lines[i])
                    i += 1
                rows = parse_pipe_table(table_lines)
                if rows:
                    story.append(Spacer(1, 3 * mm))
                    t = build_table_flowable(rows, styles)
                    if t:
                        story.append(t)
                    story.append(Spacer(1, 3 * mm))
                continue

            # Whitespace-aligned table detection
            is_table, end_idx = is_whitespace_table_block(lines, i)
            if is_table:
                table_lines = [lines[j] for j in range(i, end_idx)]
                rows = parse_whitespace_table(table_lines)
                if rows:
                    story.append(Spacer(1, 3 * mm))
                    t = build_table_flowable(rows, styles)
                    if t:
                        story.append(t)
                    story.append(Spacer(1, 3 * mm))
                i = end_idx
                continue

            # Code block
            if stripped.startswith('```'):
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                i += 1  # skip closing ```
                if code_lines:
                    code_text = '\n'.join(code_lines)
                    code_text = code_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    story.append(Spacer(1, 2 * mm))
                    story.append(Paragraph(
                        f'<font face="Courier" size="8">{code_text.replace(chr(10), "<br/>")}</font>',
                        styles['CodeBlock']
                    ))
                    story.append(Spacer(1, 2 * mm))
                continue

            # List items
            list_match = re.match(r'^[-*]\s+(.+)$', stripped)
            num_list_match = re.match(r'^(\d+)\.\s+(.+)$', stripped)
            if list_match:
                text = clean_text(md_to_html(list_match.group(1)))
                story.append(Paragraph(f"\u2022  {text}", styles['ListItem']))
                i += 1
                continue
            if num_list_match and not num_list_match.group(1).isdigit() == False:
                # Only treat as list if it's clearly a list item (not a section number)
                text = clean_text(md_to_html(num_list_match.group(2)))
                story.append(Paragraph(f"{num_list_match.group(1)}.  {text}", styles['ListItem']))
                i += 1
                continue

            # Regular paragraph - collect until empty line
            para_lines = []
            while i < len(lines) and lines[i].strip():
                current = lines[i].strip()
                # Don't absorb table lines, list items, or code blocks
                if is_pipe_table_line(current) or re.match(r'^[-*]\s+', current) or re.match(r'^```\w*$', current):
                    break
                # Don't absorb whitespace table lines
                is_tbl, _ = is_whitespace_table_block(lines, i)
                if is_tbl:
                    break
                para_lines.append(current)
                i += 1

            if para_lines:
                text = clean_text(md_to_html(' '.join(para_lines)))
                # Check if it's a reference entry (starts with number + period)
                ref_match = re.match(r'^(\d+)\.\s+(.+)$', text)
                if ref_match and section['title'] == 'References':
                    story.append(Paragraph(text, styles['RefText']))
                else:
                    story.append(Paragraph(text, styles['BodyText2']))
            continue

        # Insert charts after specific sections
        sec_num = section.get('number', '')
        if sec_num == '3.5' and 'chart1' not in charts_inserted:
            # After Experiments section (has all tables), insert all charts
            story.extend(make_chart_flowable(chart_base_vs_sft,
                'Figure 1: Base vs SFT Composite Score by Skill'))
            story.extend(make_chart_flowable(chart_sft_vs_dpo,
                'Figure 2: SFT vs DPO Improvement by Skill'))
            story.extend(make_chart_flowable(chart_per_dimension,
                'Figure 3: DPO Per-Dimension Improvement'))
            story.extend(make_chart_flowable(chart_top_improvers,
                'Figure 4: Top 5 Task Improvements (SFT Delta)'))
            charts_inserted.add('chart1')

        story.append(Spacer(1, 3 * mm))

    return story


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='Generate SkillGym paper PDF')
    parser.add_argument('--input', default=None, help='Input markdown file')
    parser.add_argument('--output', default=None, help='Output PDF path')
    args = parser.parse_args()

    # Resolve paths relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.dirname(script_dir)

    input_path = args.input or os.path.join(repo_dir, 'paper.md')
    output_path = args.output or os.path.join(repo_dir, 'skillgym-paper.pdf')

    if not os.path.exists(input_path):
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Parsing: {input_path}")
    title_data, sections = parse_paper(input_path)
    print(f"  Title: {title_data.get('title', 'Unknown')}")
    print(f"  Sections: {len(sections)}")

    print(f"Building PDF...")
    doc = BaseDocTemplate(
        output_path, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=22 * mm, bottomMargin=22 * mm,
        title=title_data.get('title', 'SkillGym Paper'),
        author='4M Labs Research'
    )

    # Title page frame (full height)
    title_frame = Frame(MARGIN, MARGIN, PAGE_W - 2 * MARGIN, PAGE_H - 2 * MARGIN, id='title')
    title_template = PageTemplate(id='title', frames=title_frame, onPage=title_page_callback)

    # Content frame (with space for header/footer)
    content_frame = Frame(MARGIN, 22 * mm, PAGE_W - 2 * MARGIN, PAGE_H - 44 * mm, id='content')
    content_template = PageTemplate(id='content', frames=content_frame, onPage=header_footer)

    doc.addPageTemplates([title_template, content_template])

    styles = build_styles()
    story = build_content(title_data, sections, styles)

    # Switch to content template after title page
    from reportlab.platypus.doctemplate import NextPageTemplate
    story.insert(0, NextPageTemplate('content'))

    doc.build(story)
    print(f"PDF saved: {output_path}")
    print(f"Size: {os.path.getsize(output_path):,} bytes")


if __name__ == '__main__':
    main()
