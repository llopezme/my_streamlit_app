import streamlit as st
import pandas as pd
import os
from datetime import datetime
from PIL import Image # Importar la librería Pillow para manejar imágenes

# Importar funciones de tus módulos
from modules.data_loader import load_inventory_data, load_consumption_data, load_characteristics_data
from modules.inventory_logic import process_movements
from modules.outlier_detection import calculate_outliers_and_mean_without_outliers, display_outliers_table
from modules.utils import display_item_characteristics, display_movement_charts, display_movement_details

# --- Configuración de rutas de archivos (RELATIVAS) ---
BASE_PATH = os.path.dirname(__file__) # Ruta del directorio actual (donde está app.py)
DATA_FOLDER = os.path.join(BASE_PATH, "data") # Carpeta 'data' dentro del proyecto
ASSETS_FOLDER = os.path.join(BASE_PATH, "assets") # Carpeta 'assets' dentro del proyecto

# Nombres de archivos de datos
CONSUMOS_FILE_NAME = "consumos.xlsx"
INVENTARIO_FILE_NAME = "inventario.xlsx"
CARACTERISTICAS_FILE_NAME = "caracteristicas.xlsx"

# Nombre del archivo del logo
LOGO_FILE_NAME = "logo.png" # ¡Asegúrate de que este sea el nombre correcto de tu archivo de logo!

# Rutas completas a los archivos (válidas en cualquier entorno)
CONSUMOS_PATH = os.path.join(DATA_FOLDER, CONSUMOS_FILE_NAME)
INVENTARIO_PATH = os.path.join(DATA_FOLDER, INVENTARIO_FILE_NAME)
CARACTERISTICAS_PATH = os.path.join(DATA_FOLDER, CARACTERISTICAS_FILE_NAME)
LOGO_PATH = os.path.join(ASSETS_FOLDER, LOGO_FILE_NAME)

# Verifica que los archivos existan (para debug)
st.write("Rutas de archivos:")
st.write(f"Consumos: {CONSUMOS_PATH}")
st.write(f"Inventario: {INVENTARIO_PATH}")
st.write(f"Características: {CARACTERISTICAS_PATH}")
st.write(f"Logo: {LOGO_PATH}") # Mostrar la ruta del logo

# Fechas clave para la simulación y visualización
INITIAL_BALANCE_DATE = datetime(2022, 12, 31)
START_PLOT_DATE = datetime(2023, 1, 1)

# Configuración de la página de Streamlit
st.set_page_config(page_title="Análisis de Movimientos de Inventario", layout="wide")

# --- Mostrar el Logo y la nota en la barra lateral ---
with st.sidebar:
    try:
        # Cargar la imagen del logo
        logo = Image.open(LOGO_PATH)
        # Mostrar el logo en la barra lateral
        st.image(logo, width=150) # Puedes ajustar el ancho según necesites
        # Mostrar la nota con texto más pequeño
        st.markdown("<p style='font-size: small; text-align: center;'>Un producto de Management Consultants de Guatemala</p>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"Advertencia: El archivo del logo no se encontró en la ruta: {LOGO_PATH}")
    except Exception as e:
        st.error(f"Error al cargar el logo: {e}")

st.title("Análisis de Entradas y Salidas de Inventario por Ítem")
st.write("""
Esta aplicación visualiza los movimientos de inventario (entradas y salidas)
para cada ítem, con un saldo inicial y mostrando los datos a partir del **01 de enero de 2023**.
""")

try:
    # --- Carga de datos ---
    st.subheader("Cargando datos...")
    df_inventario = load_inventory_data(INVENTARIO_PATH)
    df_caracteristicas = load_characteristics_data(CARACTERISTICAS_PATH)
    df_movimientos = load_consumption_data(CONSUMOS_PATH)
    st.success("Todos los archivos cargados exitosamente.")
    
    # --- Procesamiento de movimientos ---
    st.subheader("Procesando movimientos y calculando saldo...")
    df_processed = process_movements(df_inventario, df_movimientos, df_caracteristicas, INITIAL_BALANCE_DATE)
    st.success("Datos procesados y saldos calculados.")

    # --- Selección de Ítem ---
    items_unicos_procesados = df_processed['Item'].unique()
    search_query = st.text_input(
        "Escribe el Ítem que quieres buscar:",
        help="Ej: A123. Presiona Enter después de escribir."
    ).strip()

    selected_item = None
    if search_query:
        matching_items = [
            item for item in items_unicos_procesados
            if str(item).lower() == search_query.lower()
        ]

        if matching_items:
            selected_item = matching_items[0]
            if len(matching_items) > 1:
                st.warning(f"Se encontraron múltiples ítems que coinciden exactamente con '{search_query}'. Mostrando el primero: {selected_item}")
        else:
            st.warning(f"El Ítem '{search_query}' no se encontró. Por favor, verifica el nombre o intenta con otro.")
            # Si no se encuentra, df_filtered no se define en este bloque, se manejará abajo.

    if selected_item:
        df_filtered = df_processed[df_processed['Item'] == selected_item].copy()
        df_display = df_filtered[df_filtered['Fecha'] >= START_PLOT_DATE].copy()

        if not df_display.empty:
            st.subheader(f"Movimientos para el Ítem: **{selected_item}** (a partir del {START_PLOT_DATE.strftime('%d-%m-%Y')})")

            # Cálculo de outliers y media sin outliers (delegado al módulo)
            upper_bound_outlier_abs, mean_without_outliers_abs, df_salidas_para_outliers = \
                calculate_outliers_and_mean_without_outliers(df_display)

            # --- Contenedor de Columnas para "Características" y "Outliers" ---
            col1, col2 = st.columns(2)

            with col1:
                display_item_characteristics(
                    selected_item, df_caracteristicas, df_inventario, df_display,
                    mean_without_outliers_abs, upper_bound_outlier_abs
                )
            with col2:
                display_outliers_table(selected_item, df_salidas_para_outliers, upper_bound_outlier_abs)

            # --- Gráfico y Tabla de Datos detallados ---
            display_movement_charts(selected_item, df_display)
            display_movement_details(df_display)

        else: # Si df_display está vacío (no hay datos después de START_PLOT_DATE)
            st.warning(f"El Ítem: **{selected_item}** no tiene movimientos registrados a partir del {START_PLOT_DATE.strftime('%d-%m-%Y')}.")
            if not df_filtered.empty and df_filtered['Fecha'].min() < START_PLOT_DATE:
                st.info(f"El último saldo disponible antes del {START_PLOT_DATE.strftime('%d-%m-%Y')} (fecha: {df_filtered['Fecha'].max().strftime('%Y-%m-%d')}) para este ítem es: {df_filtered['Saldo'].iloc[-1]}.")

    else:
        st.info("Por favor, escribe el nombre de un Ítem en el campo de texto para ver sus movimientos.")

except FileNotFoundError as e:
    st.error(f"Error: Uno de los archivos Excel no se encontró. {e}")
    st.info(f"Asegúrate de que '{INVENTARIO_FILE_NAME}', '{CONSUMOS_FILE_NAME}' y '{CARACTERISTICAS_FILE_NAME}' estén en: `{DATA_FOLDER}`")
except ValueError as e:
    st.error(f"Error en el formato de los archivos Excel: {e}")
    st.info(f"""Revisa los nombres de las columnas en tus archivos Excel:
    - '{CONSUMOS_FILE_NAME}': 'Item', 'Site', 'Fecha', 'Movimientos'.
    - '{INVENTARIO_FILE_NAME}': 'Item', 'CurrentStock', 'LeadTime', 'StockSeguridad'.
    - '{CARACTERISTICAS_FILE_NAME}': 'Item', 'Site', 'Descripcion', 'ADI', 'CV', 'Metodo', 'ABC Class'.""")
except Exception as e:
    st.error(f"Ocurrió un error inesperado: {e}. Esto podría deberse a un problema con los datos en tus archivos Excel que no se ajustan al tipo esperado.")
    st.info("""Verifica los tipos de datos en tus columnas:
    'Item', 'CurrentStock', 'Movimientos', 'Fecha', 'LeadTime', 'StockSeguridad',
    'Descripcion', 'ADI', 'CV', 'Metodo', 'ABC Class' en tus archivos Excel.""")

st.markdown("""
---
_Aplicación creada con Streamlit, Pandas y Plotly para análisis de inventario._
""")
