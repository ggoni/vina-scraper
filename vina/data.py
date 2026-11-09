"""Data layer: scrape Viña del Mar apartment sales from Portal Inmobiliario."""

import os
import re
import time
from datetime import datetime

from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

BASE_URL = "https://www.portalinmobiliario.com/venta/departamento/vina-del-mar-valparaiso"
PAGE_SIZE = 48
MAX_PAGES = int(os.getenv("VINA_MAX_PAGES", "42"))  # ponytail: portal caps at ~2000 results
DELAY_BETWEEN_PAGES = int(os.getenv("VINA_DELAY", "8"))
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

CARD = "li.ui-search-layout__item"
TITLE = (".poly-component__title", "h2", "h3")
LOCATION = (".poly-component__location", "[class*='location']")
ATTRS = ".poly-attributes_list__item"

SQM = r"(\d+)(?:\s*[-–]\s*(\d+))?\s*m(?:²|2)"
BEDS = r"(\d+)(?:\s*a\s*\d+)?\s*dormitorios?"
BATHS = r"(\d+)(?:\s*a\s*\d+)?\s*baños?"


def _int(pattern: str, text: str) -> int | None:
    m = re.search(pattern, text)
    return int(m.group(1)) if m else None


def _text(el, selectors: tuple[str, ...]) -> str | None:
    for sel in selectors:
        node = el.select_one(sel)
        if node and (t := node.get_text(" ", strip=True)):
            return t
    return None


def _price(text: str) -> tuple[int | None, str | None]:
    if m := re.search(r"UF\s*([\d\.]+)", text):
        return int(m.group(1).replace(".", "")), "UF"
    if m := re.search(r"\$\s*([\d\.]+)", text):
        return int(m.group(1).replace(".", "")), "CLP"
    return None, None


def _valid(row: dict) -> bool:
    p, cur, m2 = row["price"], row["price_currency"], row["square_meters"]
    if not p:
        return False
    if cur == "UF" and not 500 <= p <= 50_000:
        return False
    if cur == "CLP" and not 20_000_000 <= p <= 2_000_000_000:
        return False
    return m2 is None or 15 <= m2 <= 600


def parse_card(el) -> dict | None:
    """Turn one listing card into a row, or None if it fails validation."""
    raw = el.get_text(" ", strip=True)
    price_box = el.select_one(".poly-component__price, .andes-money-amount")
    price, currency = _price(price_box.get_text(" ", strip=True) if price_box else raw)
    if not price:
        price, currency = _price(raw)
    attrs = " ".join(a.get_text(" ", strip=True) for a in el.select(ATTRS)) or raw
    sqm = re.search(SQM, attrs) or re.search(SQM, raw)
    row = {
        "title": _text(el, TITLE),
        "price": price,
        "price_currency": currency,
        "bedrooms": _int(BEDS, attrs) or (0 if "Estudio" in attrs else None),
        "bathrooms": _int(BATHS, attrs),
        "square_meters": int(sqm.group(1)) if sqm else None,
        "square_meters_max": int(sqm.group(2)) if sqm and sqm.group(2) else None,
        "address": _text(el, LOCATION),
        "raw_text": raw,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    return row if _valid(row) else None


def parse_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    return [r for r in map(parse_card, soup.select(CARD)) if r]


def scrape(max_pages: int = MAX_PAGES) -> list[dict]:
    """Return every valid Viña del Mar listing (all sectors)."""
    rows: list[dict] = []
    seen: set[frozenset] = set()
    with Stealth(navigator_user_agent_override=USER_AGENT).use_sync(sync_playwright()) as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_context(
            user_agent=USER_AGENT, locale="es-CL", timezone_id="America/Santiago"
        ).new_page()
        for n in range(max_pages):
            url = BASE_URL if n == 0 else f"{BASE_URL}/_Desde_{n * PAGE_SIZE + 1}_NoIndex_True"
            try:
                page.goto(url, timeout=60_000)
                page.wait_for_selector(CARD, timeout=30_000)
            except PlaywrightTimeout:
                print(f"página {n + 1}: timeout, se detiene")
                break
            items = parse_page(page.content())
            key = frozenset((r["title"], r["price"], r["address"]) for r in items)
            if not items or key in seen:
                break
            seen.add(key)
            rows.extend(items)
            print(f"página {n + 1}: +{len(items)} (total {len(rows)})")
            if n + 1 < max_pages:
                time.sleep(DELAY_BETWEEN_PAGES)
        browser.close()
    return rows
