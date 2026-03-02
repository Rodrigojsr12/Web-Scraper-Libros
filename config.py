"""
config.py — Configuración centralizada del Web Scraper.

Todos los parámetros ajustables del scraper se definen aquí.
Modifica este archivo para adaptar el comportamiento sin tocar la lógica principal.
"""

from dataclasses import dataclass, field
from pathlib import Path

# ───────────────────────────────────────────
# Directorio raíz del proyecto
# ───────────────────────────────────────────
BASE_DIR = Path(__file__).parent


@dataclass(frozen=True)
class ScraperConfig:
    """Configuración inmutable del scraper. Todos los valores son de solo lectura."""

    # ── Red ──────────────────────────────────
    url_base: str = "https://books.toscrape.com/"
    timeout: int = 15  
    max_reintentos: int = 3  
    backoff_factor: float = 2.0  

    # ── Rate Limiting ─────────────────────────
    delay_min: float = 0.5   
    delay_max: float = 1.5   

    headers: dict = field(default_factory=lambda: {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })

    # ── Archivos de Salida ────────────────────
    salida_csv: Path = BASE_DIR / "precios_libros.csv"
    salida_json: Path = BASE_DIR / "precios_libros.json"
    salida_log: Path = BASE_DIR / "scraper.log"


# Instancia global lista para importar
CONFIG = ScraperConfig()
