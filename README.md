---
tipo: readme
tags: [scraping, real-estate, portal-inmobiliario, vina-del-mar]
fecha: 09-11-26
objetivo: Estimar precios de departamentos en venta en un sector de Viña del Mar.
---

# vina-scraper

Este proyecto hace scraping de departamentos en venta en Viña del Mar, desde [Portal Inmobiliario](https://www.portalinmobiliario.com/venta/departamento/vina-del-mar-valparaiso). Separa los avisos en NUEVO (proyecto inmobiliario) y USADO. Filtra un sector por palabras clave. Calcula un precio simulado por tipología con los cuartiles de UF/m² (UF: Unidad de Fomento).

El sector por defecto es calle Álvarez, cerca del Hospital Gustavo Fricke.

## Arquitectura

| Capa | Archivo | Función |
|---|---|---|
| Datos | `vina/data.py` | Usa Playwright con stealth y parsea las tarjetas de avisos. |
| Negocio | `vina/logic.py` | Elimina duplicados, segmenta, filtra el sector y simula precios. |
| Presentación | `vina/__main__.py` | Escribe los CSV y el resumen en consola. |

## Uso

```bash
uv sync
uv run playwright install chromium
uv run python -m vina
```

Una corrida completa revisa hasta 42 páginas (unos 2000 avisos, el tope del portal) y tarda unos 6 minutos.

## Configuración (variables de entorno)

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `VINA_MAX_PAGES` | `42` | Número máximo de páginas, con 48 avisos por página. |
| `VINA_DELAY` | `8` | Segundos de espera entre páginas. |
| `VINA_SECTOR` | `alvarez,álvarez,fricke,chorrillos,viana,quinta vergara` | Palabras clave del sector, separadas por coma. |
| `VINA_UF_CLP` | `40845` | Valor fijo de la UF en pesos chilenos (CLP). |

Ejemplo, prueba rápida en Reñaca:

```bash
VINA_MAX_PAGES=2 VINA_SECTOR=reñaca uv run python -m vina
```

## Salida (`output/`)

| Archivo | Contenido |
|---|---|
| `vina_avisos_<ts>.csv` | Todos los avisos de Viña del Mar, ya enriquecidos. |
| `vina_sector_ejemplos_<ts>.csv` | Comparables del sector, con la columna `segmento`. |
| `vina_simulaciones_<ts>.csv` | Precio simulado por segmento y tipología (P25, mediana, P75). |

Si un segmento tiene menos de 3 avisos en el sector, el cálculo usa el UF/m² de todo Viña del Mar (columna `base`). Los proyectos publican precios "Desde UF", por eso el UF/m² usa los m² mínimos.

## Tests

```bash
uv run pytest -q
uv run ruff check .
```

## Problemas comunes

Si la salida queda vacía, el portal puede estar bloqueando el acceso. Suba `VINA_DELAY` o reintente más tarde.
