"""Presentation layer: run scrape -> enrich -> simulate and write CSV files."""

import csv
from datetime import datetime
from pathlib import Path

from vina import data, logic

OUT_DIR = Path("output")
EXAMPLE_FIELDS = [
    "segmento",
    "title",
    "price",
    "price_currency",
    "price_uf",
    "bedrooms",
    "bathrooms",
    "square_meters",
    "square_meters_max",
    "uf_m2",
    "address",
    "timestamp",
]
ALL_FIELDS = EXAMPLE_FIELDS + ["en_sector", "raw_text"]


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"{path}: {len(rows)} filas")


def main() -> None:
    rows = logic.enrich(data.scrape())
    if not rows:
        raise SystemExit("Sin avisos: posible bloqueo del portal. Reintente más tarde o suba VINA_DELAY.")
    examples = sorted((r for r in rows if r["en_sector"]), key=lambda r: (r["segmento"], r["price_uf"] or 0))
    sims = logic.simulate(rows)

    OUT_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    write_csv(OUT_DIR / f"vina_avisos_{ts}.csv", rows, ALL_FIELDS)
    write_csv(OUT_DIR / f"vina_sector_ejemplos_{ts}.csv", examples, EXAMPLE_FIELDS)
    if sims:
        write_csv(OUT_DIR / f"vina_simulaciones_{ts}.csv", sims, list(sims[0]))
    for s in sims:
        print(
            f"[{s['segmento']}] {s['tipologia']} {s['m2']} m2: UF {s['precio_uf_mediana']:,} "
            f"(UF {s['precio_uf_p25']:,} - {s['precio_uf_p75']:,}) base={s['base']} n={s['n_comparables']}"
        )


if __name__ == "__main__":
    main()
