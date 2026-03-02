"""
scraper_precios.py — Web Scraper Profesional de Precios de Libros.

Arquitectura ETL (Extract → Transform → Load):
  - Extract:   Descarga el HTML con reintentos, sesión persistente y rate limiting.
  - Transform: Parsea y limpia los datos convirtiéndolos en objetos tipados.
  - Load:      Persiste los resultados en CSV y JSON con logging dual (consola + archivo).

Uso:
    python scraper_precios.py

Salidas generadas:
    precios_libros.csv  — Datos tabulares listos para Excel / Pandas.
    precios_libros.json — Datos estructurados listos para APIs u otros sistemas.
    scraper.log         — Historial completo de ejecución.
"""

import csv
import io
import json
import logging
import random
import sys
import time
from dataclasses import dataclass, fields
from datetime import datetime
from pathlib import Path
from typing import Any, Generator
from urllib.parse import urljoin

if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8")
if isinstance(sys.stderr, io.TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8")

import requests  # type: ignore[import-untyped]
from bs4 import BeautifulSoup  # type: ignore[import-untyped]

from config import CONFIG, ScraperConfig  # type: ignore[import-not-found]


# ══════════════════════════════════════════════
# CONFIGURACIÓN DE LOGGING (Consola + Archivo)
# ══════════════════════════════════════════════
def _configurar_logging(ruta_log: Path) -> logging.Logger:
    """
    Configura un logger con doble handler: consola y archivo rotativo.

    Args:
        ruta_log: Ruta al archivo .log donde se persistirá el historial.

    Returns:
        Logger configurado y listo para usar.
    """
    logger = logging.getLogger("WebScraper")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    consola = logging.StreamHandler(stream=sys.stdout)
    consola.setLevel(logging.INFO)
    consola.setFormatter(fmt)

    archivo = logging.FileHandler(ruta_log, encoding="utf-8")
    archivo.setLevel(logging.DEBUG)
    archivo.setFormatter(fmt)

    logger.addHandler(consola)
    logger.addHandler(archivo)
    return logger


log = _configurar_logging(CONFIG.salida_log)


# ══════════════════════════════════════════════
# 1. MODELADO DE DATOS
# ══════════════════════════════════════════════
@dataclass
class Libro:
    """
    Representa un libro extraído del sitio web, con datos ya limpios y tipados.

    Attributes:
        titulo:        Título completo del libro.
        precio_libras: Precio en libras esterlinas (£) como número decimal.
        disponible:    True si hay stock disponible, False en caso contrario.
        calificacion:  Calificación de 1 a 5 estrellas extraída del HTML.
        enlace:        URL absoluta a la página de detalle del libro.
    """

    titulo: str
    precio_libras: float
    disponible: bool
    calificacion: int
    enlace: str


# ══════════════════════════════════════════════
# 2. MOTOR ETL — CLASE PRINCIPAL
# ══════════════════════════════════════════════
class ScraperLibros:
    """
    Motor de scraping con patrón ETL para books.toscrape.com.

    Extrae todos los libros de todas las páginas del catálogo, aplica
    limpieza y normalización de datos, y los exporta a CSV y JSON.
    """

    _RATING_MAP: dict[str, int] = {
        "One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5,
    }

    _total_peticiones: int

    def __init__(self, config: ScraperConfig = CONFIG) -> None:
        """
        Inicializa el scraper con la configuración provista.

        Args:
            config: Instancia de ScraperConfig. Por defecto usa CONFIG global.
        """
        self.config = config
        self.session = self._crear_sesion()
        self._total_peticiones = 0

    # ──────────────────────────────────────────
    # Helpers privados
    # ──────────────────────────────────────────
    def _crear_sesion(self) -> requests.Session:
        """
        Crea y configura una sesión HTTP persistente con headers predefinidos.

        Returns:
            Sesión de requests lista para hacer peticiones.
        """
        sesion = requests.Session()
        sesion.headers.update(self.config.headers)
        return sesion

    def _espera_cortesia(self) -> None:
        """Pausa aleatoria entre peticiones para respetar al servidor."""
        delay = random.uniform(self.config.delay_min, self.config.delay_max)
        log.debug(f"Rate limiting: esperando {delay:.2f}s antes de la siguiente petición.")
        time.sleep(delay)

    # ──────────────────────────────────────────
    # FASE 1 — EXTRACT (Extracción)
    # ──────────────────────────────────────────
    def _extraer_html(self, url: str) -> str | None:
        """
        Descarga el HTML de una URL con reintentos y backoff exponencial.

        Args:
            url: URL a descargar.

        Returns:
            HTML como string, o None si todos los reintentos fallan.
        """
        for intento in range(1, self.config.max_reintentos + 1):
            try:
                log.info(f"[GET] {url} (intento {intento}/{self.config.max_reintentos})")
                respuesta = self.session.get(url, timeout=self.config.timeout)
                respuesta.raise_for_status()
                self._total_peticiones += 1
                return respuesta.text

            except requests.exceptions.HTTPError as e:
                log.warning(f"Error HTTP {e.response.status_code} en {url}: {e}")
            except requests.exceptions.ConnectionError:
                log.warning(f"Error de conexión al intentar acceder a {url}.")
            except requests.exceptions.Timeout:
                log.warning(f"Timeout después de {self.config.timeout}s en {url}.")
            except requests.exceptions.RequestException as e:
                log.error(f"Error inesperado de red: {e}")

            if intento < self.config.max_reintentos:
                espera = self.config.backoff_factor ** intento
                log.info(f"Reintentando en {espera:.1f}s...")
                time.sleep(espera)

        log.error(f"Se agotaron los {self.config.max_reintentos} reintentos para {url}.")
        return None

    def _generar_urls_paginas(self) -> Generator[str, None, None]:
        """
        Genera las URLs de todas las páginas del catálogo descubriendo la paginación.

        Yields:
            URL de cada página del catálogo en orden.
        """
        url_actual = self.config.url_base
        pagina_num = 1

        while url_actual:
            yield url_actual

            html = self._extraer_html(url_actual)
            if not html:
                break

            sopa = BeautifulSoup(html, "html.parser")
            boton_siguiente = sopa.select_one("li.next > a")

            if boton_siguiente:
                href = boton_siguiente["href"]
                if pagina_num == 1:
                    url_actual = f"{self.config.url_base}catalogue/{href}"
                else:
                    url_actual = f"{self.config.url_base}catalogue/{href}"
                pagina_num += 1
                self._espera_cortesia()
            else:
                url_actual = None 

    # ──────────────────────────────────────────
    # FASE 2 — TRANSFORM (Transformación)
    # ──────────────────────────────────────────
    def _transformar_pagina(self, html: str, num_pagina: int) -> list[Libro]:
        """
        Parsea una página HTML y extrae todos los libros como objetos Libro.

        Args:
            html:       Contenido HTML de la página.
            num_pagina: Número de página (para logging informativo).

        Returns:
            Lista de objetos Libro limpios y validados.
        """
        sopa = BeautifulSoup(html, "html.parser")
        tarjetas = sopa.find_all("article", class_="product_pod")
        log.info(f"Página {num_pagina}: procesando {len(tarjetas)} libros encontrados.")

        libros: list[Libro] = []

        for tarjeta in tarjetas:
            try:
                titulo: str = tarjeta.find("h3").find("a")["title"]

                precio_texto: str = tarjeta.find("p", class_="price_color").text
                precio: float = float(
                    precio_texto.encode("ascii", "ignore").decode().replace("£", "").strip()
                )

                disponibilidad_txt: str = (
                    tarjeta.find("p", class_="instock availability").text.strip()
                )
                disponible: bool = "In stock" in disponibilidad_txt

                # Calificación: clase CSS como "star-rating Three" → 3
                rating_css: list[str] = tarjeta.find("p", class_="star-rating")["class"]
                calificacion: int = self._RATING_MAP.get(rating_css[1], 0)

                # Enlace: resolvemos la URL relativa contra la URL actual del catálogo
                href: str = tarjeta.find("h3").find("a")["href"]
                enlace: str = urljoin("https://books.toscrape.com/catalogue/", href)

                libros.append(Libro(titulo, precio, disponible, calificacion, enlace))

            except (AttributeError, KeyError, ValueError) as e:
                log.warning(f"Artículo omitido por HTML incompleto o malformado: {e}")
                continue

        return libros

    def extraer_todos(self) -> list[Libro]:
        """
        Punto de entrada principal de la fase ETL. Navega todas las páginas
        y retorna la colección completa de libros.

        Returns:
            Lista consolidada de todos los libros del catálogo.
        """
        todos_los_libros: list[Libro] = []
        pagina_num: int = 1

        # Iteramos página a página usando el generador de URLs
        url_actual: str | None = self.config.url_base

        while url_actual:
            html = self._extraer_html(url_actual)
            if not html:
                log.error(f"No se pudo obtener la página {pagina_num}. Deteniendo.")
                break

            libros_pagina = self._transformar_pagina(html, pagina_num)
            todos_los_libros.extend(libros_pagina)

            # Descubrimos la URL de la siguiente página
            sopa = BeautifulSoup(html, "html.parser")
            boton_siguiente = sopa.select_one("li.next > a")

            if boton_siguiente:
                href = boton_siguiente["href"]
                url_actual = urljoin(url_actual, href)
                pagina_num = pagina_num + 1  # type: ignore[operator]
                self._espera_cortesia()
            else:
                url_actual = None

        log.info(f"Extracción completa: {len(todos_los_libros)} libros en {pagina_num} página(s).")
        return todos_los_libros

    # ──────────────────────────────────────────
    # FASE 3 — LOAD (Carga / Persistencia)
    # ──────────────────────────────────────────
    @staticmethod
    def _libro_a_dict(libro: "Libro") -> dict[str, Any]:
        """Convierte un Libro a diccionario sin depender de dataclasses.asdict().

        Esta implementación manual evita ambigüedades de tipado con Pyre2.
        """
        return {
            f.name: getattr(libro, f.name)
            for f in fields(libro)  # type: ignore[arg-type]
        }

    def guardar_csv(self, datos: list["Libro"]) -> None:
        """
        Exporta los libros a un archivo CSV con encabezado automático.

        Args:
            datos: Lista de objetos Libro a persistir.
        """
        if not datos:
            log.warning("CSV: no hay datos para guardar.")
            return

        ruta = self.config.salida_csv
        try:
            with open(ruta, mode="w", newline="", encoding="utf-8") as f:
                columnas = list(self._libro_a_dict(datos[0]).keys())
                writer = csv.DictWriter(f, fieldnames=columnas)
                writer.writeheader()
                for libro in datos:
                    writer.writerow(self._libro_a_dict(libro))
            log.info(f"CSV guardado → {ruta} ({len(datos)} registros)")
        except IOError as e:
            log.error(f"Error al escribir el CSV: {e}")

    def guardar_json(self, datos: list[Libro]) -> None:
        """
        Exporta los libros a un archivo JSON con formato legible (indentado).

        Args:
            datos: Lista de objetos Libro a persistir.
        """
        if not datos:
            log.warning("JSON: no hay datos para guardar.")
            return

        ruta = self.config.salida_json
        try:
            payload = {
                "metadata": {
                    "generado_en": datetime.now().isoformat(),
                    "fuente": self.config.url_base,
                    "total_registros": len(datos),
                },
                "libros": [self._libro_a_dict(libro) for libro in datos],
            }
            with open(ruta, mode="w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            log.info(f"JSON guardado → {ruta} ({len(datos)} registros)")
        except IOError as e:
            log.error(f"Error al escribir el JSON: {e}")


# ══════════════════════════════════════════════
# PUNTO DE ENTRADA
# ══════════════════════════════════════════════
def _mostrar_resumen(libros: list[Libro], tiempo_total: float) -> None:
    """
    Imprime en consola un resumen estadístico post-ejecución.

    Args:
        libros:       Lista completa de libros extraídos.
        tiempo_total: Tiempo transcurrido en segundos.
    """
    if not libros:
        print("Sin datos para mostrar resumen.")
        return

    precios = [l.precio_libras for l in libros]
    disponibles = sum(1 for l in libros if l.disponible)

    print("\n" + "═" * 55)
    print("  📊  RESUMEN DE EJECUCIÓN")
    print("═" * 55)
    print(f"  {'Total de libros extraídos:':<30} {len(libros):>8}")
    print(f"  {'Libros disponibles (In Stock):':<30} {disponibles:>8}")
    print(f"  {'Precio mínimo:':<30} £{min(precios):>7.2f}")
    print(f"  {'Precio máximo:':<30} £{max(precios):>7.2f}")
    print(f"  {'Precio promedio:':<30} £{sum(precios)/len(precios):>7.2f}")
    print(f"  {'Tiempo total de ejecución:':<30} {tiempo_total:>7.1f}s")
    print("═" * 55)

    print("\n  📚  Muestra — Primeros 5 libros:")
    print("  " + "─" * 53)
    # islice + list evita el error de Pyre2 con slice en listas tipadas
    from itertools import islice
    for libro in list(islice(libros, 5)):
        estrellas = "★" * libro.calificacion + "☆" * (5 - libro.calificacion)
        titulo_corto = libro.titulo[:38] + "…" if len(libro.titulo) > 38 else libro.titulo
        stock = "✅" if libro.disponible else "❌"
        print(f"  {stock} {titulo_corto:<40} £{libro.precio_libras:>6.2f}  {estrellas}")
    print()


def main() -> None:
    """Función principal que orquesta el pipeline ETL completo."""
    print("╔" + "═" * 53 + "╗")
    print("║      🚀  WEB SCRAPER PROFESIONAL — ETL Engine      ║")
    print("║            books.toscrape.com  —  v2.0             ║")
    print("╚" + "═" * 53 + "╝\n")

    inicio = time.time()
    scraper = ScraperLibros()

    # ── EXTRACT + TRANSFORM ──
    libros = scraper.extraer_todos()

    if not libros:
        log.error("El scraper no obtuvo ningún dato. Revisa los logs para más detalles.")
        return

    # ── LOAD ──
    scraper.guardar_csv(libros)
    scraper.guardar_json(libros)

    # ── RESUMEN ──
    _mostrar_resumen(libros, time.time() - inicio)


if __name__ == "__main__":
    main()
