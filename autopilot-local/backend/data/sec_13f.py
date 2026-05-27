from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

import httpx

from portfolios import get_portfolio_spec

SEC_HEADERS = {
    "User-Agent": "AutopilotLocal research@example.com",
    "Accept-Encoding": "gzip, deflate",
}


def _cik_pad(cik: str) -> str:
    digits = re.sub(r"\D", "", cik)
    return digits.zfill(10)


def fetch_latest_13f_url(cik: str) -> str | None:
    cik10 = _cik_pad(cik)
    url = f"https://data.sec.gov/submissions/CIK{cik10}.json"
    try:
        with httpx.Client(timeout=30.0, headers=SEC_HEADERS) as client:
            r = client.get(url)
            if r.status_code != 200:
                return None
            data = r.json()
            recent = data.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            accessions = recent.get("accessionNumber", [])
            primary = recent.get("primaryDocument", [])
            for i, form in enumerate(forms):
                if form and "13F" in str(form).upper():
                    acc = str(accessions[i]).replace("-", "")
                    doc = primary[i]
                    return (
                        f"https://www.sec.gov/Archives/edgar/data/"
                        f"{int(cik10)}/{acc}/{doc}"
                    )
    except Exception:
        return None
    return None


def _parse_13f_xml(content: str) -> list[tuple[str, float]]:
    holdings: list[tuple[str, float]] = []
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return []
    # 13F XML variants: infoTable with nameOfIssuer + value
    for table in root.iter():
        tag = table.tag.split("}")[-1] if "}" in table.tag else table.tag
        if tag.lower() not in {"infotable", "info_table"}:
            continue
        ticker = ""
        value = 0.0
        for child in table:
            ctag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            text = (child.text or "").strip()
            if ctag in {"nameofissuer", "nameOfIssuer"}:
                ticker = text.split()[0].upper() if text else ""
            if ctag in {"value", "sshprnamt"} and ctag == "value":
                try:
                    value = float(text)
                except ValueError:
                    value = 0.0
            if ctag in {"cusip"} and not ticker:
                pass
            if ctag in {"titleofclass"} and text.upper() in {"COM", "COMMON", "CL A"}:
                pass
        if ticker and value > 0:
            holdings.append((ticker, value))
    if not holdings:
        # fallback: any value + issuer pairs in tree
        issuer = ""
        val = 0.0
        for elem in root.iter():
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if tag in {"nameOfIssuer", "nameofissuer"}:
                issuer = (elem.text or "").strip().split()[0].upper()
            if tag == "value":
                try:
                    val = float((elem.text or "0").strip())
                except ValueError:
                    val = 0.0
                if issuer and val > 0:
                    holdings.append((issuer, val))
                    issuer, val = "", 0.0
    if not holdings:
        return []
    total = sum(v for _, v in holdings) or 1.0
    # Map issuer names to tickers is hard — use first token as pseudo-ticker
    merged: dict[str, float] = {}
    for name, v in holdings:
        sym = re.sub(r"[^A-Z]", "", name.upper())[:5] or name[:5].upper()
        merged[sym] = merged.get(sym, 0.0) + v
    ranked = sorted(merged.items(), key=lambda x: x[1], reverse=True)[:12]
    total = sum(v for _, v in ranked) or 1.0
    return [(t, v / total) for t, v in ranked]


def fetch_13f_holdings(cik: str) -> list[tuple[str, float]] | None:
    doc_url = fetch_latest_13f_url(cik)
    if not doc_url:
        return None
    try:
        with httpx.Client(timeout=60.0, headers=SEC_HEADERS) as client:
            r = client.get(doc_url)
            if r.status_code != 200:
                return None
            return _parse_13f_xml(r.text)
    except Exception:
        return None


def refresh_hedge_fund_portfolio(portfolio_id: str) -> list[tuple[str, float]] | None:
    spec = get_portfolio_spec(portfolio_id)
    if not spec or spec.get("category") != "hedge-fund":
        return None
    cik = spec.get("cik")
    if not cik:
        return None
    holdings = fetch_13f_holdings(cik)
    return holdings if holdings else None
