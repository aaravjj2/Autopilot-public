#!/usr/bin/env python
"""Render a Markdown file to PDF using ReportLab (no external binaries).

Supports the subset used by the project README: H1-H4, paragraphs, bold,
inline code, links, fenced code blocks, bullet lists, GitHub tables, and
horizontal rules. Intended for docs, not full CommonMark fidelity.
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ACCENT = colors.HexColor("#1f6feb")
CODE_BG = colors.HexColor("#f3f4f6")
GRID = colors.HexColor("#d0d7de")
HEAD_BG = colors.HexColor("#0d1117")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    body = base["BodyText"]
    body.fontName = "Helvetica"
    body.fontSize = 10.5
    body.leading = 15
    body.spaceAfter = 6
    body.alignment = TA_LEFT

    return {
        "body": body,
        "h1": ParagraphStyle("h1", parent=body, fontName="Helvetica-Bold",
                             fontSize=22, leading=26, spaceBefore=4, spaceAfter=10,
                             textColor=HEAD_BG),
        "h2": ParagraphStyle("h2", parent=body, fontName="Helvetica-Bold",
                             fontSize=15, leading=19, spaceBefore=14, spaceAfter=6,
                             textColor=ACCENT),
        "h3": ParagraphStyle("h3", parent=body, fontName="Helvetica-Bold",
                             fontSize=12.5, leading=16, spaceBefore=10, spaceAfter=4,
                             textColor=HEAD_BG),
        "h4": ParagraphStyle("h4", parent=body, fontName="Helvetica-Bold",
                             fontSize=11, leading=14, spaceBefore=8, spaceAfter=3,
                             textColor=HEAD_BG),
        "code": ParagraphStyle("code", parent=body, fontName="Courier",
                               fontSize=8.6, leading=11.5, textColor=colors.HexColor("#24292f")),
        "cell": ParagraphStyle("cell", parent=body, fontSize=9.5, leading=13, spaceAfter=0),
        "cellhead": ParagraphStyle("cellhead", parent=body, fontName="Helvetica-Bold",
                                   fontSize=9.5, leading=13, spaceAfter=0,
                                   textColor=colors.white),
    }


def _inline(text: str) -> str:
    """Convert inline markdown to ReportLab mini-HTML markup."""
    text = html.escape(text, quote=False)
    # inline code
    text = re.sub(r"`([^`]+)`",
                  r'<font face="Courier" size=9 backColor="#f3f4f6">\1</font>', text)
    # bold
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__([^_]+)__", r"<b>\1</b>", text)
    # drop images first (incl. badge images nested in links): ![alt](url)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    # links [t](url) -> keep only non-empty link text
    def _link(m: re.Match) -> str:
        label = m.group(1).strip()
        if not label:
            return ""
        return f'<a href="{m.group(2)}" color="#1f6feb"><u>{label}</u></a>'
    text = re.sub(r"\[([^\]]*)\]\(([^)]+)\)", _link, text)
    return text


def _split_table_row(line: str) -> list[str]:
    cells = line.strip().strip("|").split("|")
    return [c.strip() for c in cells]


def parse(md_text: str, styles: dict[str, ParagraphStyle]) -> list:
    flow: list = []
    lines = md_text.splitlines()
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # fenced code block
        if stripped.startswith("```"):
            i += 1
            buf: list[str] = []
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1  # closing fence
            code = "\n".join(buf) if buf else " "
            tbl = Table([[Preformatted(code, styles["code"])]],
                        colWidths=[6.5 * inch])
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
                ("BOX", (0, 0), (-1, -1), 0.5, GRID),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            flow.append(tbl)
            flow.append(Spacer(1, 8))
            continue

        # horizontal rule
        if re.fullmatch(r"-{3,}|\*{3,}|_{3,}", stripped):
            flow.append(Spacer(1, 4))
            flow.append(HRFlowable(width="100%", thickness=0.6, color=GRID))
            flow.append(Spacer(1, 6))
            i += 1
            continue

        # table (header row + separator row)
        if (stripped.startswith("|") and i + 1 < n
                and re.match(r"^\s*\|?[\s:|-]+\|?\s*$", lines[i + 1])
                and "-" in lines[i + 1]):
            header = _split_table_row(stripped)
            i += 2
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append(_split_table_row(lines[i].strip()))
                i += 1
            data = [[Paragraph(_inline(c), styles["cellhead"]) for c in header]]
            for r in rows:
                while len(r) < len(header):
                    r.append("")
                data.append([Paragraph(_inline(c), styles["cell"]) for c in r[:len(header)]])
            ncols = len(header)
            col_w = (6.5 / ncols) * inch
            tbl = Table(data, colWidths=[col_w] * ncols, repeatRows=1)
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f8fa")]),
                ("GRID", (0, 0), (-1, -1), 0.5, GRID),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            flow.append(tbl)
            flow.append(Spacer(1, 8))
            continue

        # headings
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            flow.append(Paragraph(_inline(m.group(2)), styles[f"h{level}"]))
            i += 1
            continue

        # bullet list
        if re.match(r"^[-*+]\s+", stripped):
            items = []
            while i < n and re.match(r"^[-*+]\s+", lines[i].strip()):
                txt = re.sub(r"^[-*+]\s+", "", lines[i].strip())
                items.append(ListItem(Paragraph(_inline(txt), styles["body"]),
                                      leftIndent=12))
                i += 1
            flow.append(ListFlowable(items, bulletType="bullet", start="•",
                                     leftIndent=14, bulletColor=ACCENT))
            flow.append(Spacer(1, 4))
            continue

        # blank line
        if not stripped:
            i += 1
            continue

        # paragraph (collect until blank / block boundary)
        para: list[str] = [stripped]
        i += 1
        while i < n:
            nxt = lines[i].strip()
            if (not nxt or nxt.startswith("#") or nxt.startswith("```")
                    or nxt.startswith("|") or re.match(r"^[-*+]\s+", nxt)
                    or re.fullmatch(r"-{3,}|\*{3,}|_{3,}", nxt)):
                break
            para.append(nxt)
            i += 1
        flow.append(Paragraph(_inline(" ".join(para)), styles["body"]))

    return flow


def main() -> None:
    ap = argparse.ArgumentParser(description="Markdown -> PDF (ReportLab)")
    ap.add_argument("src", nargs="?", default="README.md")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()

    src = Path(args.src)
    out = Path(args.out) if args.out else src.with_suffix(".pdf")
    md_text = src.read_text(encoding="utf-8")

    styles = _styles()
    doc = SimpleDocTemplate(
        str(out), pagesize=LETTER,
        leftMargin=0.9 * inch, rightMargin=0.9 * inch,
        topMargin=0.85 * inch, bottomMargin=0.85 * inch,
        title=src.stem,
    )
    doc.build(parse(md_text, styles))
    print(f"Wrote {out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
