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
        # Se ha añadido 'Site' a las columnas esperadas
        expected_cols = ['Item', 'CurrentStock', 'LeadTime', 'StockSeguridad', 'Site'] 
        if not all(col in df.columns for col in expected_cols):
            # Mejorar el mensaje de error para mostrar las columnas encontradas vs. esperadas
            found_cols = df.columns.tolist()
            missing_cols = [col for col in expected_cols if col not in found_cols]
            raise ValueError(f"Columnas esperadas faltantes en el archivo: {os.path.basename(file_path)}. "
                             f"Columnas esperadas: {expected_cols}. Columnas encontradas: {found_cols}. "
                             f"Faltan: {missing_cols}")
        df['Item'] = df['Item'].astype(str)
        # Asegurarse de que las columnas numéricas sean float para evitar errores
        df['CurrentStock'] = pd.to_numeric(df['CurrentStock'], errors='coerce').fillna(0)
        df['LeadTime'] = pd.to_numeric(df['LeadTime'], errors='coerce').fillna(0)
        df['StockSeguridad'] = pd.to_numeric(df['StockSeguridad'], errors='coerce').fillna(0)
        # No es necesario convertir 'Site' a string si ya es de tipo objeto/string en el excel
        # df['Site'] = df['Site'].astype(str) # Descomentar si es necesario asegurar tipo string
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
            found_cols = df.columns.tolist()
            missing_cols = [col for col in expected_cols if col not in found_cols]
            raise ValueError(f"Columnas esperadas faltantes en el archivo: {os.path.basename(file_path)}. "
                             f"Columnas esperadas: {expected_cols}. Columnas encontradas: {found_cols}. "
                             f"Faltan: {missing_cols}")
        df['Item'] = df['Item'].astype(str)
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        df['Movimientos'] = pd.to_numeric(df['Movimientos'], errors='coerce').fillna(0)
        df.dropna(subset=['Fecha'], inplace=True) # Eliminar filas con fechas no válidas
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
            found_cols = df.columns.tolist()
            missing_cols = [col for col in expected_cols if col not in found_cols]
            raise ValueError(f"Columnas esperadas faltantes en el archivo: {os.path.basename(file_path)}. "
                             f"Columnas esperadas: {expected_cols}. Columnas encontradas: {found_cols}. "
                             f"Faltan: {missing_cols}")
        df['Item'] = df['Item'].astype(str)
        # Asegurarse de que las columnas numéricas sean float para evitar errores
        df['ADI'] = pd.to_numeric(df['ADI'], errors='coerce').fillna(0)
        df['CV'] = pd.to_numeric(df['CV'], errors='coerce').fillna(0)
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
