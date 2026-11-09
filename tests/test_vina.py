from pathlib import Path

from vina.data import parse_page
from vina.logic import enrich, simulate

CARD = Path(__file__).parent / "fixtures" / "card.html"


def _row(raw, addr, price, m2, cur="UF"):
    return {
        "raw_text": raw,
        "address": addr,
        "title": raw,
        "price": price,
        "price_currency": cur,
        "square_meters": m2,
    }


def test_parse_real_card():
    html = f'<ul><li class="ui-search-layout__item">{CARD.read_text()}</li></ul>'
    (row,) = parse_page(html)
    assert (row["price"], row["price_currency"]) == (3647, "UF")
    assert (row["bedrooms"], row["bathrooms"]) == (1, 1)
    assert (row["square_meters"], row["square_meters_max"]) == (29, 34)
    assert enrich([row])[0]["segmento"] == "NUEVO"


def test_segment_sector_and_simulation():
    rows = enrich(
        [
            _row("PROYECTO Departamentos en venta A", "Álvarez 1200, Viña Del Mar", 3000, 40),
            _row("PROYECTO Departamentos en venta B", "Viana 500, Viña Del Mar", 3600, 40),
            _row("PROYECTO Departamentos en venta C", "Chorrillos 10, Viña Del Mar", 3200, 40),
            _row("Departamento en venta D", "Alvarez 900, Viña Del Mar", 2500, 50),
            _row("Departamento en venta E", "Reñaca, Viña Del Mar", 204_225_000, 50, "CLP"),
            _row("Departamento en venta E", "Reñaca, Viña Del Mar", 204_225_000, 50, "CLP"),  # dup
        ]
    )
    assert len(rows) == 5
    assert [r["segmento"] for r in rows] == ["NUEVO"] * 3 + ["USADO"] * 2
    assert [r["en_sector"] for r in rows] == [True, True, True, True, False]
    assert rows[4]["uf_m2"] == 100.0
    sims = {(s["segmento"], s["tipologia"]): s for s in simulate(rows)}
    assert sims[("NUEVO", "2D1B")]["precio_uf_mediana"] == 80 * 50  # median 80 UF/m2
    assert sims[("NUEVO", "2D1B")]["base"] == "sector"
    assert sims[("USADO", "2D1B")]["base"] == "viña"  # only 1 sector sample -> fallback
