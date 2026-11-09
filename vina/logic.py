"""Business layer: segment, filter by sector and simulate prices from UF/m2 quartiles."""

import os
import statistics

# Streets / places within ~1 km of Hospital Gustavo Fricke (Álvarez 1532). Override via VINA_SECTOR.
SECTOR_KEYWORDS = tuple(
    k.strip().lower()
    for k in os.getenv("VINA_SECTOR", "alvarez,álvarez,fricke,chorrillos,viana,quinta vergara").split(",")
    if k.strip()
)
MIN_SECTOR_SAMPLE = 3  # below this, fall back to Viña-wide UF/m2 for the segment
UF_CLP = float(os.getenv("VINA_UF_CLP", "40845"))  # ponytail: fixed rate, plug an API if needed

# Typical units to simulate: (label, bedrooms, bathrooms, m2)
UNIT_TYPES = [
    ("1D1B", 1, 1, 35),
    ("2D1B", 2, 1, 50),
    ("2D2B", 2, 2, 60),
    ("3D2B", 3, 2, 80),
]


def segment(row: dict) -> str:
    """NUEVO for developer projects (card starts with 'PROYECTO'), else USADO."""
    return "NUEVO" if (row.get("raw_text") or "").upper().startswith("PROYECTO") else "USADO"


def in_sector(row: dict, keywords: tuple[str, ...] = SECTOR_KEYWORDS) -> bool:
    text = f"{row.get('address') or ''} {row.get('title') or ''}".lower()
    return any(k in text for k in keywords)


def price_uf(row: dict) -> float | None:
    p = row.get("price")
    if not p:
        return None
    return float(p) if row.get("price_currency") == "UF" else p / UF_CLP


def uf_per_m2(row: dict) -> float | None:
    # ponytail: projects quote "Desde UF" -> pair with min m2, not the range midpoint
    m2, p = row.get("square_meters"), price_uf(row)
    return round(p / m2, 2) if p and m2 else None


def enrich(rows: list[dict]) -> list[dict]:
    """Dedup and add segmento, en_sector, price_uf, uf_m2."""
    out, seen = [], set()
    for r in rows:
        key = (r.get("title"), r.get("price"), r.get("address"))
        if key in seen:
            continue
        seen.add(key)
        p = price_uf(r)
        out.append(
            {
                **r,
                "segmento": segment(r),
                "en_sector": in_sector(r),
                "price_uf": round(p, 1) if p else None,
                "uf_m2": uf_per_m2(r),
            }
        )
    return out


def _quartiles(vals: list[float]) -> tuple[float, float, float]:
    if len(vals) == 1:
        return vals[0], vals[0], vals[0]
    q1, q2, q3 = statistics.quantiles(vals, n=4, method="inclusive")
    return q1, q2, q3


def simulate(rows: list[dict]) -> list[dict]:
    """Simulated price = UF/m2 quartiles of the segment x unit m2."""
    sims = []
    for seg in ("NUEVO", "USADO"):
        sector = [r["uf_m2"] for r in rows if r["segmento"] == seg and r["en_sector"] and r["uf_m2"]]
        city = [r["uf_m2"] for r in rows if r["segmento"] == seg and r["uf_m2"]]
        vals, base = (sector, "sector") if len(sector) >= MIN_SECTOR_SAMPLE else (city, "viña")
        if not vals:
            continue
        q1, q2, q3 = _quartiles(vals)
        for label, beds, baths, m2 in UNIT_TYPES:
            sims.append(
                {
                    "segmento": seg,
                    "tipologia": label,
                    "dormitorios": beds,
                    "banos": baths,
                    "m2": m2,
                    "uf_m2_mediana": round(q2, 2),
                    "precio_uf_p25": round(q1 * m2),
                    "precio_uf_mediana": round(q2 * m2),
                    "precio_uf_p75": round(q3 * m2),
                    "precio_clp_mediana": round(q2 * m2 * UF_CLP),
                    "base": base,
                    "n_comparables": len(vals),
                }
            )
    return sims
