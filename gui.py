"""
gui.py — Interfaz Gráfica del Web Scraper Profesional.

Tecnología: CustomTkinter (tema oscuro moderno)
Layout:
  - Header  : título de la app
  - Sidebar : controles, configuración y estadísticas
  - Main    : pestaña Resultados (tabla) + pestaña Logs (consola)
  - Footer  : barra de progreso y botones de exportación
"""

import csv
import json
import logging
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk  # type: ignore[import-untyped]

from config import CONFIG, ScraperConfig  # type: ignore[import-not-found]
from scraper_precios import Libro, ScraperLibros  # type: ignore[import-not-found]


# ══════════════════════════════════════════════
# PALETA DE COLORES (Dark Professional Theme)
# ══════════════════════════════════════════════
COLORS = {
    "bg_dark":      "#0f1117",   
    "bg_sidebar":   "#16213e",  
    "bg_card":      "#1a1a2e",   
    "bg_panel":     "#1e2030",   
    "accent":       "#00b4d8",   
    "accent_hover": "#0096c7",   
    "success":      "#2ecc71",   
    "success_dark": "#27ae60",
    "danger":       "#e74c3c",   
    "danger_dark":  "#c0392b",
    "warning":      "#f39c12",   
    "text":         "#e2e8f0",   
    "text_muted":   "#94a3b8",   
    "border":       "#2d3748",   
    "tag_info":     "#00b4d8",
    "tag_warning":  "#f39c12",
    "tag_error":    "#e74c3c",
    "tag_success":  "#2ecc71",
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ══════════════════════════════════════════════
# HANDLER DE LOGGING PARA LA GUI
# ══════════════════════════════════════════════
class GUILogHandler(logging.Handler):
    """Handler que redirige los logs del scraper al widget de consola de la GUI."""

    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.setFormatter(logging.Formatter(
            "%(asctime)s  %(levelname)-8s  %(message)s",
            datefmt="%H:%M:%S",
        ))

    def emit(self, record: logging.LogRecord):
        msg = self.format(record)
        self.callback(msg, record.levelname)


# ══════════════════════════════════════════════
# VENTANA PRINCIPAL
# ══════════════════════════════════════════════
class ScraperApp(ctk.CTk):
    """Aplicación principal del Web Scraper con interfaz gráfica profesional."""

    def __init__(self):
        super().__init__()

        # ── Propiedades de la ventana ──
        self.title("📚 Book Scraper Pro")
        self.geometry("1300x820")
        self.minsize(1100, 700)
        self.configure(fg_color=COLORS["bg_dark"])

        # ── Estado interno ──
        self._libros: list[Libro] = []
        self._scraping: bool = False
        self._hilo: threading.Thread | None = None
        self._total_paginas: int = 50  
        self._pagina_actual: int = 0

        # ── Construcción de la UI ──
        self._construir_header()
        self._construir_layout_principal()
        self._construir_footer()

        # ── Conectar logger al widget de consola ──
        self._conectar_logger()

        self.protocol("WM_DELETE_WINDOW", self._al_cerrar)

    # ──────────────────────────────────────────
    # SECCIÓN: HEADER
    # ──────────────────────────────────────────
    def _construir_header(self):
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=0, height=72)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        separator = ctk.CTkFrame(self, fg_color=COLORS["accent"], height=3, corner_radius=0)
        separator.pack(fill="x", side="top")

        inner = ctk.CTkFrame(header, fg_color="transparent")
        inner.pack(expand=True, fill="both", padx=24, pady=12)

        ctk.CTkLabel(
            inner,
            text="📚  Book Scraper Pro",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=COLORS["text"],
        ).pack(side="left")

        ctk.CTkLabel(
            inner,
            text="books.toscrape.com  ·  ETL Engine v2.0",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLORS["text_muted"],
        ).pack(side="left", padx=(12, 0))

        # Badge de estado
        self._lbl_estado_badge = ctk.CTkLabel(
            inner,
            text="  ● EN REPOSO  ",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS["text_muted"],
            fg_color=COLORS["bg_dark"],
            corner_radius=12,
        )
        self._lbl_estado_badge.pack(side="right")

    # ──────────────────────────────────────────
    # SECCIÓN: LAYOUT PRINCIPAL (Sidebar + Main)
    # ──────────────────────────────────────────
    def _construir_layout_principal(self):
        contenedor = ctk.CTkFrame(self, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=0, pady=0)

        self._construir_sidebar(contenedor)
        self._construir_area_main(contenedor)

    def _construir_sidebar(self, parent):
        sidebar = ctk.CTkFrame(
            parent,
            width=280,
            fg_color=COLORS["bg_sidebar"],
            corner_radius=0,
        )
        sidebar.pack(side="left", fill="y", padx=0)
        sidebar.pack_propagate(False)

        # ── Sección Controles ──
        self._seccion_label(sidebar, "⚙  CONTROLES")

        self._btn_iniciar = ctk.CTkButton(
            sidebar,
            text="▶  Iniciar Scraping",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["success"],
            hover_color=COLORS["success_dark"],
            corner_radius=10,
            height=46,
            command=self._iniciar_scraping,
        )
        self._btn_iniciar.pack(fill="x", padx=18, pady=(4, 6))

        self._btn_detener = ctk.CTkButton(
            sidebar,
            text="⏹  Detener",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["bg_panel"],
            hover_color=COLORS["danger_dark"],
            text_color=COLORS["text_muted"],
            corner_radius=10,
            height=40,
            state="disabled",
            command=self._detener_scraping,
        )
        self._btn_detener.pack(fill="x", padx=18, pady=(0, 16))

        # ── Sección Configuración ──
        self._seccion_label(sidebar, "🔧  CONFIGURACIÓN")

        self._crear_campo(sidebar, "URL Base:", CONFIG.url_base, "url_entry", editable=False)
        self._crear_slider(sidebar, "Delay mín. (s):", CONFIG.delay_min, 0.1, 3.0, "slider_min")
        self._crear_slider(sidebar, "Delay máx. (s):", CONFIG.delay_max, 0.5, 5.0, "slider_max")
        self._crear_campo_int(sidebar, "Reintentos:", CONFIG.max_reintentos, "entry_reintentos")

        # ── Sección Estadísticas ──
        self._seccion_label(sidebar, "📊  ESTADÍSTICAS")

        stats_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        stats_frame.pack(fill="x", padx=18, pady=4)

        self._stat_total   = self._crear_stat_card(stats_frame, "Total Libros", "0")
        self._stat_disp    = self._crear_stat_card(stats_frame, "Disponibles", "0")
        self._stat_precio  = self._crear_stat_card(stats_frame, "Precio Prom.", "£0.00")
        self._stat_paginas = self._crear_stat_card(stats_frame, "Páginas", "0/50")

        # ── Exportación rápida ──
        self._seccion_label(sidebar, "💾  EXPORTAR")

        export_row = ctk.CTkFrame(sidebar, fg_color="transparent")
        export_row.pack(fill="x", padx=18, pady=4)

        ctk.CTkButton(
            export_row,
            text="📄 CSV",
            width=110,
            fg_color=COLORS["bg_panel"],
            hover_color=COLORS["accent_hover"],
            text_color=COLORS["accent"],
            border_color=COLORS["accent"],
            border_width=1,
            corner_radius=8,
            command=self._exportar_csv,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            export_row,
            text="📦 JSON",
            width=110,
            fg_color=COLORS["bg_panel"],
            hover_color=COLORS["accent_hover"],
            text_color=COLORS["accent"],
            border_color=COLORS["accent"],
            border_width=1,
            corner_radius=8,
            command=self._exportar_json,
        ).pack(side="left")

    def _construir_area_main(self, parent):
        main = ctk.CTkFrame(parent, fg_color=COLORS["bg_dark"], corner_radius=0)
        main.pack(side="left", fill="both", expand=True, padx=0)

        # TabView principal
        self._tabs = ctk.CTkTabview(
            main,
            fg_color=COLORS["bg_card"],
            segmented_button_fg_color=COLORS["bg_panel"],
            segmented_button_selected_color=COLORS["accent"],
            segmented_button_selected_hover_color=COLORS["accent_hover"],
            segmented_button_unselected_color=COLORS["bg_panel"],
            segmented_button_unselected_hover_color=COLORS["border"],
            text_color=COLORS["text"],
            corner_radius=12,
        )
        self._tabs.pack(fill="both", expand=True, padx=12, pady=12)

        self._tabs.add("  📋  Resultados  ")
        self._tabs.add("  🖥  Consola de Log  ")

        self._construir_tabla(self._tabs.tab("  📋  Resultados  "))
        self._construir_consola(self._tabs.tab("  🖥  Consola de Log  "))

    # ──────────────────────────────────────────
    # COMPONENTE: TABLA DE RESULTADOS
    # ──────────────────────────────────────────
    def _construir_tabla(self, parent):
        # Barra de búsqueda + filtros
        top_bar = ctk.CTkFrame(parent, fg_color="transparent")
        top_bar.pack(fill="x", padx=8, pady=(8, 4))

        self._search_var = tk.StringVar()
        self._search_var.trace("w", lambda *a: self._filtrar_tabla())

        ctk.CTkEntry(
            top_bar,
            placeholder_text="🔍  Buscar por título...",
            textvariable=self._search_var,
            width=300,
            fg_color=COLORS["bg_panel"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            placeholder_text_color=COLORS["text_muted"],
        ).pack(side="left")

        ctk.CTkLabel(
            top_bar,
            text="Filtrar por rating:",
            text_color=COLORS["text_muted"],
            font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=(18, 6))

        self._filtro_rating = ctk.CTkComboBox(
            top_bar,
            values=["Todos", "⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"],
            width=130,
            fg_color=COLORS["bg_panel"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            button_color=COLORS["accent"],
            dropdown_fg_color=COLORS["bg_card"],
            command=lambda _: self._filtrar_tabla(),
        )
        self._filtro_rating.set("Todos")
        self._filtro_rating.pack(side="left")

        self._lbl_conteo = ctk.CTkLabel(
            top_bar,
            text="0 resultados",
            text_color=COLORS["text_muted"],
            font=ctk.CTkFont(size=12),
        )
        self._lbl_conteo.pack(side="right")

        # Contenedor de la tabla con scrollbar
        tabla_frame = ctk.CTkFrame(parent, fg_color=COLORS["bg_panel"], corner_radius=10)
        tabla_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Estilos del Treeview
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Pro.Treeview",
            background=COLORS["bg_panel"],
            foreground=COLORS["text"],
            fieldbackground=COLORS["bg_panel"],
            bordercolor=COLORS["border"],
            rowheight=32,
            font=("Segoe UI", 11),
        )
        style.configure(
            "Pro.Treeview.Heading",
            background=COLORS["bg_card"],
            foreground=COLORS["accent"],
            font=("Segoe UI", 11, "bold"),
            bordercolor=COLORS["border"],
            relief="flat",
        )
        style.map("Pro.Treeview",
            background=[("selected", COLORS["accent"])],
            foreground=[("selected", "#ffffff")],
        )
        style.map("Pro.Treeview.Heading",
            background=[("active", COLORS["bg_dark"])],
        )

        # Scrollbars
        vsb = ttk.Scrollbar(tabla_frame, orient="vertical")
        hsb = ttk.Scrollbar(tabla_frame, orient="horizontal")

        columnas = ("titulo", "precio", "rating", "disponible", "enlace")
        self._tree = ttk.Treeview(
            tabla_frame,
            columns=columnas,
            show="headings",
            style="Pro.Treeview",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
        )

        # Cabeceras
        cabeceras = {
            "titulo":     ("📖  Título", 380, "w"),
            "precio":     ("💷  Precio", 90,  "center"),
            "rating":     ("⭐ Rating",  100,  "center"),
            "disponible": ("✅ Stock",    80,  "center"),
            "enlace":     ("🔗  Enlace",  260, "w"),
        }
        for col, (texto, ancho, anchor) in cabeceras.items():
            self._tree.heading(col, text=texto, command=lambda c=col: self._ordenar_tabla(c))
            self._tree.column(col, width=ancho, anchor=anchor, minwidth=60)

        # Tags de colores para filas alternas y disponibilidad
        self._tree.tag_configure("par",     background=COLORS["bg_panel"])
        self._tree.tag_configure("impar",   background="#1c2333")
        self._tree.tag_configure("agotado", foreground=COLORS["danger"])

        vsb.config(command=self._tree.yview)
        hsb.config(command=self._tree.xview)

        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tabla_frame.grid_rowconfigure(0, weight=1)
        tabla_frame.grid_columnconfigure(0, weight=1)

        # Abrir enlace al hacer doble click
        self._tree.bind("<Double-1>", self._abrir_enlace)
        self._sort_ascending: dict[str, bool] = {c: True for c in columnas}

    # ──────────────────────────────────────────
    # COMPONENTE: CONSOLA DE LOG
    # ──────────────────────────────────────────
    def _construir_consola(self, parent):
        top_bar = ctk.CTkFrame(parent, fg_color="transparent")
        top_bar.pack(fill="x", padx=8, pady=(8, 4))

        ctk.CTkLabel(
            top_bar,
            text="Historial en tiempo real",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text"],
        ).pack(side="left")

        ctk.CTkButton(
            top_bar,
            text="🗑  Limpiar",
            width=90,
            height=28,
            fg_color=COLORS["bg_panel"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_muted"],
            corner_radius=6,
            font=ctk.CTkFont(size=11),
            command=self._limpiar_consola,
        ).pack(side="right")

        consola_frame = ctk.CTkFrame(parent, fg_color=COLORS["bg_dark"], corner_radius=10)
        consola_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self._consola = tk.Text(
            consola_frame,
            wrap="word",
            state="disabled",
            bg=COLORS["bg_dark"],
            fg=COLORS["text"],
            font=("Consolas", 11),
            relief="flat",
            borderwidth=0,
            padx=12,
            pady=8,
            cursor="arrow",
        )

        vsb_c = ttk.Scrollbar(consola_frame, orient="vertical", command=self._consola.yview)
        self._consola.configure(yscrollcommand=vsb_c.set)

        # Tags de colores por nivel
        self._consola.tag_configure("INFO",    foreground=COLORS["tag_info"])
        self._consola.tag_configure("WARNING", foreground=COLORS["tag_warning"])
        self._consola.tag_configure("ERROR",   foreground=COLORS["tag_error"])
        self._consola.tag_configure("DEBUG",   foreground=COLORS["text_muted"])
        self._consola.tag_configure("SUCCESS", foreground=COLORS["tag_success"])
        self._consola.tag_configure("ts",      foreground="#475569")

        self._consola.pack(side="left", fill="both", expand=True)
        vsb_c.pack(side="right", fill="y")

    # ──────────────────────────────────────────
    # SECCIÓN: FOOTER (Barra de progreso)
    # ──────────────────────────────────────────
    def _construir_footer(self):
        sep = ctk.CTkFrame(self, fg_color=COLORS["border"], height=1, corner_radius=0)
        sep.pack(fill="x")

        footer = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=0, height=56)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        inner = ctk.CTkFrame(footer, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=18, pady=10)

        # Etiqueta de progreso
        self._lbl_progreso = ctk.CTkLabel(
            inner,
            text="Esperando inicio...",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"],
        )
        self._lbl_progreso.pack(side="left")

        # Barra de progreso
        self._barra = ctk.CTkProgressBar(
            inner,
            mode="determinate",
            progress_color=COLORS["accent"],
            fg_color=COLORS["bg_panel"],
            corner_radius=6,
            height=14,
        )
        self._barra.set(0)
        self._barra.pack(side="left", fill="x", expand=True, padx=18)

        # Porcentaje
        self._lbl_pct = ctk.CTkLabel(
            inner,
            text="0%",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["accent"],
            width=40,
        )
        self._lbl_pct.pack(side="left")

        # Timestamp
        self._lbl_hora = ctk.CTkLabel(
            inner,
            text=datetime.now().strftime("%H:%M:%S"),
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
        )
        self._lbl_hora.pack(side="right")
        self._actualizar_reloj()

    # ──────────────────────────────────────────
    # HELPERS DE UI
    # ──────────────────────────────────────────
    def _seccion_label(self, parent, texto: str):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=18, pady=(14, 4))
        ctk.CTkLabel(
            frame,
            text=texto,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=COLORS["text_muted"],
        ).pack(side="left")
        ctk.CTkFrame(frame, fg_color=COLORS["border"], height=1).pack(
            side="left", fill="x", expand=True, padx=(8, 0)
        )

    def _crear_campo(self, parent, label: str, valor: str, attr: str, editable=True):
        ctk.CTkLabel(parent, text=label, text_color=COLORS["text_muted"],
                     font=ctk.CTkFont(size=11)).pack(anchor="w", padx=18, pady=(4, 0))
        entry = ctk.CTkEntry(
            parent,
            fg_color=COLORS["bg_panel"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            state="normal" if editable else "disabled",
        )
        entry.insert(0, valor)
        entry.pack(fill="x", padx=18, pady=(2, 6))
        setattr(self, f"_{attr}", entry)

    def _crear_campo_int(self, parent, label: str, valor: int, attr: str):
        ctk.CTkLabel(parent, text=label, text_color=COLORS["text_muted"],
                     font=ctk.CTkFont(size=11)).pack(anchor="w", padx=18, pady=(4, 0))
        entry = ctk.CTkEntry(
            parent,
            fg_color=COLORS["bg_panel"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
        )
        entry.insert(0, str(valor))
        entry.pack(fill="x", padx=18, pady=(2, 6))
        setattr(self, f"_{attr}", entry)

    def _crear_slider(self, parent, label: str, valor: float, minv: float, maxv: float, attr: str):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(4, 0))
        ctk.CTkLabel(row, text=label, text_color=COLORS["text_muted"],
                     font=ctk.CTkFont(size=11)).pack(side="left")
        lbl_val = ctk.CTkLabel(row, text=f"{valor:.1f}s",
                               text_color=COLORS["accent"], font=ctk.CTkFont(size=11))
        lbl_val.pack(side="right")

        slider = ctk.CTkSlider(
            parent,
            from_=minv, to=maxv, number_of_steps=int((maxv - minv) / 0.1),
            fg_color=COLORS["bg_panel"], progress_color=COLORS["accent"],
            button_color=COLORS["accent"], button_hover_color=COLORS["accent_hover"],
            command=lambda v, l=lbl_val: l.configure(text=f"{v:.1f}s"),
        )
        slider.set(valor)
        slider.pack(fill="x", padx=18, pady=(2, 8))
        setattr(self, f"_{attr}", slider)

    def _crear_stat_card(self, parent, titulo: str, valor: str):
        card = ctk.CTkFrame(parent, fg_color=COLORS["bg_panel"], corner_radius=8)
        card.pack(fill="x", pady=3)
        ctk.CTkLabel(card, text=titulo, text_color=COLORS["text_muted"],
                     font=ctk.CTkFont(size=10)).pack(anchor="w", padx=10, pady=(6, 0))
        lbl = ctk.CTkLabel(card, text=valor, text_color=COLORS["text"],
                           font=ctk.CTkFont(size=16, weight="bold"))
        lbl.pack(anchor="w", padx=10, pady=(0, 6))
        return lbl

    # ──────────────────────────────────────────
    # LÓGICA: LOGGER → CONSOLA GUI
    # ──────────────────────────────────────────
    def _conectar_logger(self):
        logger = logging.getLogger("WebScraper")
        handler = GUILogHandler(self._escribir_consola_safe)
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)

    def _escribir_consola_safe(self, msg: str, level: str):
        """Thread-safe: despacha al hilo principal de Tkinter."""
        self.after(0, lambda: self._escribir_consola(msg, level))

    def _escribir_consola(self, msg: str, level: str):
        self._consola.configure(state="normal")
        tag = level if level in ("INFO", "WARNING", "ERROR", "DEBUG") else "INFO"
        self._consola.insert("end", msg + "\n", tag)
        self._consola.see("end")
        self._consola.configure(state="disabled")

    def _limpiar_consola(self):
        self._consola.configure(state="normal")
        self._consola.delete("1.0", "end")
        self._consola.configure(state="disabled")

    # ──────────────────────────────────────────
    # LÓGICA: SCRAPING EN HILO SEPARADO
    # ──────────────────────────────────────────
    def _iniciar_scraping(self):
        if self._scraping:
            return

        self._scraping = True

        # Limpiar estado anterior
        self._libros = []
        self._pagina_actual = 0
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._lbl_conteo.configure(text="0 resultados")

        # UI → estado activo
        self._btn_iniciar.configure(state="disabled", fg_color=COLORS["bg_panel"],
                                    text_color=COLORS["text_muted"])
        self._btn_detener.configure(state="normal", fg_color=COLORS["danger"],
                                    text_color="white")
        self._lbl_estado_badge.configure(text="  ● SCRAPING...  ", text_color=COLORS["success"],
                                         fg_color=COLORS["bg_dark"])

        # Leer configuración dinámica
        delay_min = self._slider_min.get()
        delay_max = self._slider_max.get()
        try:
            max_reintentos = int(self._entry_reintentos.get())
        except ValueError:
            max_reintentos = 3

        config = ScraperConfig(delay_min=delay_min, delay_max=delay_max,
                               max_reintentos=max_reintentos)
        self._scraper = ScraperLibros(config)

        # Lanzar en hilo daemon
        self._hilo = threading.Thread(
            target=self._hilo_scraping,
            daemon=True,
        )
        if self._hilo:
            self._hilo.start()

    def _hilo_scraping(self):
        """Ejecuta el scraper en un hilo secundario para no bloquear la UI."""
        try:
            libros = self._ejecutar_con_progreso()
            self.after(0, lambda: self._al_terminar(libros, error=None))
        except Exception as e:
            self.after(0, lambda: self._al_terminar([], error=str(e)))

    def _ejecutar_con_progreso(self) -> list["Libro"]:
        """Versión instrumentada de extraer_todos() que actualiza la UI en vivo."""
        from bs4 import BeautifulSoup  # type: ignore[import-untyped]
        from urllib.parse import urljoin

        todos: list[Libro] = []
        url_actual = self._scraper.config.url_base
        pagina = 1

        while url_actual and self._scraping:
            html = self._scraper._extraer_html(url_actual)
            if not html:
                break

            libros_pag = self._scraper._transformar_pagina(html, pagina)
            todos.extend(libros_pag)

            # Actualizar UI de forma thread-safe
            pag_cap = pagina
            from itertools import islice
            libros_cap = list(islice(todos, 0, None))  
            self.after(0, lambda p=pag_cap, l=libros_cap: self._actualizar_progreso(p, l))

            sopa = BeautifulSoup(html, "html.parser")
            btn = sopa.select_one("li.next > a")
            if btn:
                href_str = str(btn["href"])
                if url_actual:
                    url_actual = urljoin(url_actual, href_str)
                pagina = pagina + 1  # type: ignore[operator]
                self._scraper._espera_cortesia()
            else:
                break

        return todos

    def _actualizar_progreso(self, pagina: int, libros: list[Libro]):
        """Actualiza barra de progreso, tabla y estadísticas (hilo principal)."""
        self._pagina_actual = pagina
        pct = min(pagina / self._total_paginas, 1.0)
        self._barra.set(pct)
        self._lbl_pct.configure(text=f"{int(pct * 100)}%")
        self._lbl_progreso.configure(
            text=f"Página {pagina} / {self._total_paginas}  —  {len(libros)} libros extraídos"
        )

        # Añadir las filas nuevas a la tabla
        total_existente = len(self._tree.get_children())
        from itertools import islice
        nuevos_libros = list(islice(libros, total_existente, None))
        for i, libro in enumerate(nuevos_libros, start=total_existente):
            tag = "impar" if i % 2 else "par"
            tags = [tag] + (["agotado"] if not libro.disponible else [])
            estrellas = "★" * libro.calificacion + "☆" * (5 - libro.calificacion)
            stock = "✅ Sí" if libro.disponible else "❌ No"
            titulo_c = libro.titulo[:55] + "…" if len(libro.titulo) > 55 else libro.titulo
            self._tree.insert("", "end", values=(
                titulo_c,
                f"£{libro.precio_libras:.2f}",
                estrellas,
                stock,
                libro.enlace,
            ), tags=tags)

        # Estadísticas
        self._libros = libros
        self._actualizar_stats()

    def _actualizar_stats(self):
        if not self._libros:
            return
        precios = [l.precio_libras for l in self._libros]
        disp = sum(1 for l in self._libros if l.disponible)
        self._stat_total.configure(text=str(len(self._libros)))
        self._stat_disp.configure(text=str(disp))
        self._stat_precio.configure(text=f"£{sum(precios)/len(precios):.2f}")
        self._stat_paginas.configure(text=f"{self._pagina_actual}/{self._total_paginas}")
        self._lbl_conteo.configure(text=f"{len(self._libros)} resultados")

    def _detener_scraping(self):
        self._scraping = False
        self._escribir_consola("⚠️  Scraping detenido por el usuario.", "WARNING")

    def _al_terminar(self, libros: list[Libro], error: str | None):
        self._scraping = False
        self._libros = libros

        if error:
            self._escribir_consola(f"❌  Error: {error}", "ERROR")
        else:
            msg = f"✅  ¡Completado! {len(libros)} libros extraídos de todas las páginas."
            self._escribir_consola(msg, "SUCCESS")
            self._barra.set(1.0)
            self._lbl_pct.configure(text="100%")
            self._lbl_progreso.configure(text=f"Completado — {len(libros)} libros extraídos")

        # UI → estado reposo
        self._btn_iniciar.configure(state="normal", fg_color=COLORS["success"],
                                    text_color="white", text="▶  Iniciar Scraping")
        self._btn_detener.configure(state="disabled", fg_color=COLORS["bg_panel"],
                                    text_color=COLORS["text_muted"])
        self._lbl_estado_badge.configure(
            text="  ● COMPLETADO  " if not error else "  ● ERROR  ",
            text_color=COLORS["success"] if not error else COLORS["danger"],
        )
        self._actualizar_stats()

    # ──────────────────────────────────────────
    # FUNCIONES: FILTROS Y ORDENAMIENTO
    # ──────────────────────────────────────────
    def _filtrar_tabla(self):
        query = self._search_var.get().lower()
        rating_filter = self._filtro_rating.get()
        rating_num = rating_filter.count("⭐") if rating_filter != "Todos" else 0

        for item in self._tree.get_children():
            self._tree.delete(item)

        filtrados = [
            l for l in self._libros
            if query in l.titulo.lower()
            and (rating_num == 0 or l.calificacion == rating_num)
        ]
        self._lbl_conteo.configure(text=f"{len(filtrados)} resultados")

        for i, libro in enumerate(filtrados):
            tag = "impar" if i % 2 else "par"
            tags = [tag] + (["agotado"] if not libro.disponible else [])
            estrellas = "★" * libro.calificacion + "☆" * (5 - libro.calificacion)
            titulo_c = libro.titulo[:55] + "…" if len(libro.titulo) > 55 else libro.titulo
            self._tree.insert("", "end", values=(
                titulo_c,
                f"£{libro.precio_libras:.2f}",
                estrellas,
                "✅ Sí" if libro.disponible else "❌ No",
                libro.enlace,
            ), tags=tags)

    def _ordenar_tabla(self, columna: str):
        """Ordena la tabla al hacer click en el encabezado."""
        items = [(self._tree.set(k, columna), k) for k in self._tree.get_children("")]
        asc = self._sort_ascending.get(columna, True)
        items.sort(reverse=not asc)
        self._sort_ascending[columna] = not asc
        for idx, (_, k) in enumerate(items):
            self._tree.move(k, "", idx)
            tag = "impar" if idx % 2 else "par"
            current_tags = [t for t in self._tree.item(k, "tags") if t not in ("par", "impar")]
            self._tree.item(k, tags=[tag] + current_tags)

    def _abrir_enlace(self, event):
        import webbrowser
        seleccion = self._tree.selection()
        if seleccion:
            enlace = self._tree.item(seleccion[0], "values")[4]
            webbrowser.open(enlace)

    # ──────────────────────────────────────────
    # FUNCIONES: EXPORTACIÓN
    # ──────────────────────────────────────────
    def _exportar_csv(self):
        if not self._libros:
            messagebox.showwarning("Sin datos", "No hay libros para exportar. Ejecuta el scraper primero.")
            return
        ruta = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="precios_libros.csv",
        )
        if ruta:
            try:
                from dataclasses import asdict
                with open(ruta, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=list(asdict(self._libros[0]).keys()))
                    writer.writeheader()
                    for l in self._libros:
                        writer.writerow(asdict(l))
                messagebox.showinfo("Exportado", f"✅ CSV guardado en:\n{ruta}")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _exportar_json(self):
        if not self._libros:
            messagebox.showwarning("Sin datos", "No hay libros para exportar. Ejecuta el scraper primero.")
            return
        ruta = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile="precios_libros.json",
        )
        if ruta:
            try:
                from dataclasses import asdict
                payload = {
                    "metadata": {
                        "generado_en": datetime.now().isoformat(),
                        "total_registros": len(self._libros),
                    },
                    "libros": [asdict(l) for l in self._libros],
                }
                with open(ruta, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
                messagebox.showinfo("Exportado", f"✅ JSON guardado en:\n{ruta}")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    # ──────────────────────────────────────────
    # UTILIDADES
    # ──────────────────────────────────────────
    def _actualizar_reloj(self):
        self._lbl_hora.configure(text=datetime.now().strftime("%H:%M:%S"))
        self.after(1000, self._actualizar_reloj)

    def _al_cerrar(self):
        if self._scraping:
            if messagebox.askyesno("Cerrar", "El scraper está en ejecución. ¿Detener y salir?"):
                self._scraping = False
                self.destroy()
        else:
            self.destroy()


# ══════════════════════════════════════════════
# PUNTO DE ENTRADA
# ══════════════════════════════════════════════
if __name__ == "__main__":
    import io
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    app = ScraperApp()
    app.mainloop()
