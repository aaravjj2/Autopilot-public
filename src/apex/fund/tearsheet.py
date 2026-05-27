"""Friday tear-sheet PDF stub (Week 10 Day 4)."""

from __future__ import annotations

from io import BytesIO
from typing import Any


def generate_tearsheet_pdf(metrics: dict[str, Any]) -> bytes:
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        c.drawString(72, 720, "APEX Fund Tear-Sheet")
        c.drawString(72, 700, f"Equity: ${metrics.get('equity', 0):,.2f}")
        c.drawString(72, 680, f"VaR 99%: ${metrics.get('var_99_usd', 0):,.2f}")
        c.drawString(72, 660, f"VIX: {metrics.get('vix', 0)}")
        c.save()
        return buf.getvalue()
    except ImportError:
        return b"%PDF-1.4\n% APEX tear-sheet placeholder\n"
