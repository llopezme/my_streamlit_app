# my_streamlit_app/modules/data_loader.py
import pandas as pd
import os
import streamlit as st # Para usar st.success, st.error, st.stop

# @st.cache_data puede ayudar a Streamlit a no recargar los archivos si no cambian
@st.cache_data
def load_inventory_data(file_path):
    """
    Carga el archivo de inventario, valida columnas y tipos de datos.
    """
    try:
        df = pd.read_excel(file_path)
        expected_cols = ['Item', 'CurrentStock', 'LeadTime', 'StockSeguridad']
        if not all(col in df.columns for col in expected_cols):
            raise ValueError(f"Columnas esperadas faltantes en el archivo: {os.path.basename(file_path)}. Se esperan: {expected_cols}")
        df['Item'] = df['Item'].astype(str)
        # Asegurarse de que las columnas numéricas sean float para evitar errores
        df['CurrentStock'] = pd.to_numeric(df['CurrentStock'], errors='coerce').fillna(0)
        df['LeadTime'] = pd.to_numeric(df['LeadTime'], errors='coerce').fillna(0)
        df['StockSeguridad'] = pd.to_numeric(df['StockSeguridad'], errors='coerce').fillna(0)
        # st.success(f"Inventario cargado: {os.path.basename(file_path)}") # Comentado para evitar doble mensaje
        return df
    except FileNotFoundError:
        st.error(f"Error: Archivo no encontrado: {os.path.basename(file_path)}. Por favor, verifica la ruta.")
        st.stop() # Detiene la ejecución de Streamlit
    except ValueError as e:
        st.error(f"Error de formato en {os.path.basename(file_path)}: {e}. Revisa el contenido.")
        st.stop()
    except Exception as e:
        st.error(f"Ocurrió un error al cargar {os.path.basename(file_path)}: {e}")
        st.stop()

@st.cache_data
def load_consumption_data(file_path):
    """
    Carga el archivo de movimientos (consumos), valida columnas y convierte tipos.
    """
    try:
        df = pd.read_excel(file_path)
        expected_cols = ['Item', 'Site', 'Fecha', 'Movimientos']
        if not all(col in df.columns for col in expected_cols):
            raise ValueError(f"Columnas esperadas faltantes en el archivo: {os.path.basename(file_path)}. Se esperan: {expected_cols}")
        df['Item'] = df['Item'].astype(str)
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        df['Movimientos'] = pd.to_numeric(df['Movimientos'], errors='coerce').fillna(0)
        df.dropna(subset=['Fecha'], inplace=True) # Eliminar filas con fechas no válidas
        # st.success(f"Consumos cargados: {os.path.basename(file_path)}") # Comentado
        return df
    except FileNotFoundError:
        st.error(f"Error: Archivo no encontrado: {os.path.basename(file_path)}. Por favor, verifica la ruta.")
        st.stop()
    except ValueError as e:
        st.error(f"Error de formato en {os.path.basename(file_path)}: {e}. Revisa el contenido.")
        st.stop()
    except Exception as e:
        st.error(f"Ocurrió un error al cargar {os.path.basename(file_path)}: {e}")
        st.stop()

@st.cache_data
def load_characteristics_data(file_path):
    """
    Carga el archivo de características, valida columnas y tipos.
    """
    try:
        df = pd.read_excel(file_path)
        expected_cols = ['Item', 'Site', 'Descripcion', 'ADI', 'CV', 'Metodo', 'ABC Class']
        if not all(col in df.columns for col in expected_cols):
            raise ValueError(f"Columnas esperadas faltantes en el archivo: {os.path.basename(file_path)}. Se esperan: {expected_cols}")
        df['Item'] = df['Item'].astype(str)
        # Asegurarse de que las columnas numéricas sean float para evitar errores
        df['ADI'] = pd.to_numeric(df['ADI'], errors='coerce').fillna(0)
        df['CV'] = pd.to_numeric(df['CV'], errors='coerce').fillna(0)
        # st.success(f"Características cargadas: {os.path.basename(file_path)}") # Comentado
        return df
    except FileNotFoundError:
        st.error(f"Error: Archivo no encontrado: {os.path.basename(file_path)}. Por favor, verifica la ruta.")
        st.stop()
    except ValueError as e:
        st.error(f"Error de formato en {os.path.basename(file_path)}: {e}. Revisa el contenido.")
        st.stop()
    except Exception as e:
        st.error(f"Ocurrió un error al cargar {os.path.basename(file_path)}: {e}")
        st.stop()