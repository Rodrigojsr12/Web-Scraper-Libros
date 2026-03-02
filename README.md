<div align="center">
  <h1>📚 Book Scraper Pro</h1>
  <p>
    <strong>Motor ETL concurrente de alto rendimiento con Interfaz Gráfica (GUI)</strong><br>
    <em>Diseñado para extraer catálogos de libros masivos preservando la integridad de los datos</em>
  </p>

  <p>
    <img alt="Python Version" src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white">
    <img alt="CustomTkinter" src="https://img.shields.io/badge/GUI-CustomTkinter-00b4d8">
    <img alt="Requests" src="https://img.shields.io/badge/requests-HTTP-success">
    <img alt="BeautifulSoup" src="https://img.shields.io/badge/BeautifulSoup-HTML_Parsing-warning">
    <img alt="License" src="https://img.shields.io/badge/License-MIT-gray">
  </p>

  <img src="C:\Users\Rodrigo\.gemini\antigravity\brain\e9ab24fc-4c89-4bd6-8b57-7aaf1672da07\desktop_guess_screenshot_1772487772214.png" alt="Book Scraper Pro GUI Screenshot" width="800" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.5);">
</div>

<br>

## 📖 Tabla de Contenidos

- [Acerca del Proyecto](#-acerca-del-proyecto)
- [Características Principales](#-características-principales)
- [Arquitectura ETL & Componentes](#-arquitectura-etl--componentes)
- [Estructura del Repositorio](#-estructura-del-repositorio)
- [Instalación y Configuración](#-instalación-y-configuración)
- [Guía de Uso](#-guía-de-uso)
- [Formato de Datos de Salida](#-formato-de-datos-de-salida)
- [Manejo Avanzado de Errores](#%EF%B8%8F-manejo-avanzado-de-errores)

---

## 🎯 Acerca del Proyecto

**Book Scraper Pro** no es un simple script de web scraping; es una aplicación de escritorio completa de grado de producción diseñada para iterar sobre el sitio de demostración `books.toscrape.com`. 

El núcleo del software es un **motor ETL** (Extract, Transform, Load) totalmente disociado de la interfaz gráfica, lo que permite que el scraping ocurra en un hilo concurrente, manteniendo la interfaz visual fluida y responsiva.

---

## ✨ Características Principales

### 🖥️ Interfaz Moderna (GUI)
- Construida en **CustomTkinter**, con modo oscuro profesional y tipografía clara.
- Panel de control intuitivo con **Live Stats** (Totales, métricas de precio y stock).
- **Consola de Logs en Vivo:** Seguimiento codificado por colores del progreso interno.
- **Tabla Interactiva:** Grilla de paginación (`Treeview`) con soporte para ordenamientos, filtrados por rating y acceso directo al navegador haciendo doble click.

### ⚙️ Motor de Scraping Resiliente
- **Scraping Concurrente:** El backend corre en un hilo aislado (`threading.Thread`) para evitar bloqueos del UI (`freeze`).
- **Paginación Dinámica:** Usa comprobaciones a prueba de fallos y `urllib.parse.urljoin` genuino para resolver relativas como `/catalogue/page-2.html`.
- **Limpieza de Datos Exhaustiva:** Transforma valores brutos (ej: `"Three"` estrellas) a DataModels estructurados de Python usando `dataclasses`.

### 🛡️ Tolerancia a Fallos
- **Session Pooling:** Usa `requests.Session()` nativo reutilizando sockets TCP subyacentes.
- **Backoff Exponencial y Retry:** Configurables (ej. 3 reintentos) para evadir caídas aleatorias del servidor (HTTP 5xx).
- **Rate-Limiting (Espera de Cortesía):** Inyecta retrasos (delays) mínimos y máximos estocásticos para emular comportamiento humano y proteger el servidor.

---

## 🏗️ Arquitectura ETL & Componentes

La aplicación sigue el clásico patrón **Extract, Transform, Load**, modularizado en tres componentes lógicos:

1. **EXTRACT:** El scraper evalúa la URL base. Extrae el HTML crudo ignorando explícitamente compresiones forzadas (`Accept-Encoding` limpiado), lidiando con fallas de conectividad según las políticas predeterminadas.
2. **TRANSFORM:** `BeautifulSoup4` entra en acción seleccionando atributos CSS específicos de tarjetas de libros. Transforma datos irregulares en una clase `Libro` estandarizada.
3. **LOAD (Doble Vía):** 
    - *Volátil:* La GUI renderiza fila por fila el estado cargando datos asíncronamente en pantalla.
    - *Persistente:* Exporta a archivos `CSV` o `JSON` mediante rutinas serializadoras manuales a prueba de fallos.

---

## 🗂️ Estructura del Repositorio

El código fuente está modularizado para garantizar pruebas eficientes (Separation of Concerns).

```tree
📦 Web Scraper/
 ┣ 📜 gui.py               # Front-end: UI CustomTkinter controladora de hilos (Main entrypoint)
 ┣ 📜 scraper_precios.py   # Back-end: Motor ETL orquestador del scraping
 ┣ 📜 config.py            # Layer Config: Entidades Inmutables de dominio y DataClasses
 ┣ 📜 requirements.txt     # Dependencias de paquetes PyPI
 ┣ 📜 precios_libros.csv   # Persistencia: Exportación plana (Generado por usuario)
 ┣ 📜 precios_libros.json  # Persistencia: Exportación anidada (Generado por usuario)
 ┗ 📜 scraper.log          # Persistencia: Archivo log transaccional de auditoría
```

---

## 🚀 Instalación y Configuración

El proyecto requiere **Python 3.10 o superior** dado el uso extenso de *Type Hinting avanzado*.

1. **Clonar el proyecto y navegar al directorio raíz:**
   ```bash
   git clone <repo-url>
   cd "Web Scraper"
   ```

2. **(Opcional pero Recomendado) Crear Entorno Virtual:**
   ```bash
   python -m venv venv
   # En Windows: venv\Scripts\activate
   ```

3. **Instalar los paquetes requeridos:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 🎮 Guía de Uso

1. **Iniciar la Aplicación:**
   ```bash
   python gui.py
   ```
   > **Nota de consola (Windows Terminal):** La aplicación está programada con fallbacks para terminales CP-1252 antiguas inyectando codificación `UTF-8` en `sys.stdout`.
   
2. **Configuración en Tiempo Real:** 
   Estando en la pestaña principal, utiliza los sliders laterales de **Delay Mínimo/Máximo** y la caja de texto **Reintentos**. Cualquier ajuste tomará fuerza en el momento de iniciar.

3. **Iniciar Scraping:**
   Click en **▶ Iniciar Scraping**. Inmediatamente podrás monitorear:
   - La **Barra de Progreso** (estimada sobre 50 páginas).
   - Los **contadores de KPIs** vivos (Total, Stock, Precios).
   - El progreso por código en la vista "🖥 Consola de Log".

4. **Exploración:**
   Una vez obtenidos los datos, usa la barra de "Búsqueda" o el filtro "Rating ⭐" en la tabla principal. Haciendo "doble click" sobre cualquier fila se abrirá la URL del libro en tu navegador por defecto.

5. **Exportación Final:**
   Utiliza los controles "💾 EXPORTAR" para volcar simultáneamente todos los libros en archivo.

---

## 📊 Formato de Datos de Salida

Se incluyen dos métodos altamente tipados de exportar la base de datos resultante:

### Opción 1: CSV Estandarizado (`precios_libros.csv`)
Salida en tabla delimitada por comas, soportada nativamente por todos los motores de Excel/Google Sheets.

| titulo | precio_libras | disponible | calificacion | enlace |
| :--- | :--- | :--- | :--- | :--- |
| *A Light in the Attic* | `51.77` | `True` | `3` | `https://books...` |
| *Tipping the Velvet* | `53.74` | `True` | `1` | `https://books...` |

### Opción 2: JSON Altamente Tipado (`precios_libros.json`)
Ideal para migrar datos extraídos hacia APIs de terceros, bases de datos no relacionales, o motores analíticos que requieren el timestamp (metadata).

```json
{
  "metadata": {
    "generado_en": "2026-03-02T16:30:14.283199",
    "fuente": "https://books.toscrape.com/",
    "total_registros": 1000
  },
  "libros": [
    {
      "titulo": "A Light in the Attic",
      "precio_libras": 51.77,
      "disponible": true,
      "calificacion": 3,
      "enlace": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
    }
  ]
}
```

---

## ⚠️ Manejo Avanzado de Errores

El proyecto implementa un `logger` dual (FileHandler y una variante de sub-clase nativa GUI) que procesan errores así:
- **Timeouts/Errores de Conexión:** Registra una bitácora en tiempo real de los intentos (`[GET] int. X/Y`). Entrará en loop de *backoff multiplicador* ante la excepción `requests.exceptions.RequestException`.
- **Parsing Fallido:** Retornará un arreglo vacío hacia la GUI sin tumbar el hilo principal si la estructura HTML raíz de books.toscrape.com llegase a mutar. El error estará resguardado en `scraper.log` bajo el tag `[ERROR]`.
    
---
<br>
<p align="center">
  Hecho con excelencia analítica.
</p>
