# my_streamlit_app/modules/inventory_logic.py
import pandas as pd
from datetime import datetime
# import streamlit as st # Eliminado: no es necesario si no se usan st.info/write/dataframe aquí

def process_movements(df_inventario: pd.DataFrame, df_movimientos: pd.DataFrame, df_caracteristicas: pd.DataFrame, initial_balance_date: datetime) -> pd.DataFrame:
    """
    Procesa los movimientos de inventario, calcula entradas/salidas y el saldo diario.
    Combina datos de inventario inicial, movimientos y características, asegurando que 'Site' se propague.
    """
    # --- START: Robustness checks for 'Item' column and DataFrame emptiness ---
    if 'Item' not in df_inventario.columns:
        raise ValueError("La columna 'Item' no se encontró en el DataFrame de inventario (df_inventario). Por favor, verifica el archivo 'inventario.xlsx'.")
    if 'Item' not in df_movimientos.columns:
        raise ValueError("La columna 'Item' no se encontró en el DataFrame de movimientos (df_movimientos). Por favor, verifica el archivo 'consumos.xlsx'.")
    
    # Ensure 'Item' columns are strings and handle potential NaNs before setting index or concatenating
    df_inventario['Item'] = df_inventario['Item'].astype(str).fillna('')
    df_movimientos['Item'] = df_movimientos['Item'].astype(str).fillna('')
    # --- END: Robustness checks for 'Item' column and DataFrame emptiness ---

    # 1. Calcular el saldo inicial para cada ítem (CurrentStock + StockSeguridad)
    # Asegurarse de que 'Site' esté en df_inventario antes de usarlo
    if 'Site' not in df_inventario.columns:
        df_inventario['Site'] = 'N/A_Inventario' 

    # Ensure 'CurrentStock' and 'StockSeguridad' are numeric before addition
    df_inventario['CurrentStock'] = pd.to_numeric(df_inventario['CurrentStock'], errors='coerce').fillna(0)
    df_inventario['StockSeguridad'] = pd.to_numeric(df_inventario['StockSeguridad'], errors='coerce').fillna(0)

    df_inventario['InitialBalance'] = df_inventario['CurrentStock'] + df_inventario['StockSeguridad']
    
    # Initialize maps, handling cases where df_inventario might be empty
    initial_balance_map = {}
    item_site_map = {}
    
    if not df_inventario.empty:
        # --- CRITICAL CHECK: Verificar si hay ítems duplicados en df_inventario antes de set_index ---
        duplicate_items = df_inventario[df_inventario.duplicated(subset=['Item'], keep=False)]
        if not duplicate_items.empty:
            # st.error("ERROR CRÍTICO: Se encontraron ítems duplicados en el archivo de inventario ('inventario.xlsx') en la columna 'Item'.")
            # st.write("Ítems duplicados en inventario:")
            # st.dataframe(duplicate_items)
            raise ValueError("Ítems duplicados encontrados en df_inventario. No se puede crear un índice único.")

        try:
            initial_balance_map = df_inventario.set_index('Item')['InitialBalance'].to_dict()
            item_site_map = df_inventario.set_index('Item')['Site'].to_dict()
        except KeyError as e:
            # st.error(f"ERROR: KeyError al crear mapas: {e}. Esto podría indicar problemas con la columna 'Item' o 'Site' después de fillna, o si el índice resultante no es único.")
            raise # Re-lanzar el error para que Streamlit lo capture
        except Exception as e:
            # st.error(f"ERROR: Ocurrió un error inesperado al crear mapas: {e}. Tipo de error: {type(e).__name__}")
            raise
    
    # Asegurarse de que 'Fecha' sea tipo datetime en df_movimientos
    df_movimientos['Fecha'] = pd.to_datetime(df_movimientos['Fecha'])

    # Calcular Entradas y Salidas en df_movimientos
    df_movimientos['Entradas'] = df_movimientos['Movimientos'].apply(lambda x: x if x > 0 else 0)
    df_movimientos['Salidas'] = df_movimientos['Movimientos'].apply(lambda x: x if x < 0 else 0)

    df_processed_list = []

    # Handle case where both df_inventario and df_movimientos might be empty
    if df_inventario.empty and df_movimientos.empty:
        return pd.DataFrame(columns=['Item', 'Fecha', 'Movimientos', 'Entradas', 'Salidas', 'Site', 'Saldo'])

    # Obtener todos los ítems únicos de todos los archivos para asegurar que todos se procesen
    items_from_inventario = df_inventario['Item'].unique().tolist() if not df_inventario.empty else []
    items_from_movimientos = df_movimientos['Item'].unique().tolist() if not df_movimientos.empty else []
    
    # Combine and get unique items, filtering out any empty strings that might have resulted from fillna('')
    all_items = [item for item in pd.Series(items_from_inventario + items_from_movimientos).unique() if item != '']
    if not all_items:
        return pd.DataFrame(columns=['Item', 'Fecha', 'Movimientos', 'Entradas', 'Salidas', 'Site', 'Saldo'])


    for item in all_items:
        # Skip processing if item is an empty string (from fillna('') on empty 'Item' values)
        if item == '':
            continue

        initial_bal = initial_balance_map.get(item, 0)
        default_site = item_site_map.get(item, 'N/A') 

        try:
            item_movements = df_movimientos[df_movimientos['Item'] == item].copy()
        except KeyError as e:
            # st.error(f"ERROR: KeyError al filtrar item_movements por 'Item': {e}.")
            raise
        except Exception as e:
            # st.error(f"ERROR: Ocurrió un error inesperado al filtrar item_movements: {e}. Tipo de error: {type(e).__name__}")
            raise

        # Determinar el rango de fechas para este ítem
        start_date_for_item = initial_balance_date
        if not item_movements.empty:
            end_date_for_item = item_movements['Fecha'].max()
        else:
            end_date_for_item = initial_balance_date 

        full_date_range = pd.date_range(start=start_date_for_item, end=end_date_for_item, freq='D')
        
        # Crear un DataFrame base con todas las fechas del rango para el ítem
        df_item_daily = pd.DataFrame({'Fecha': full_date_range, 'Item': item})
        
        # Ensure 'Site' column exists in item_movements before grouping
        if 'Site' not in item_movements.columns:
            item_movements['Site'] = default_site 

        try:
            # CORRECCIÓN CLAVE: Incluir 'Item' en la agrupación para que esté presente en daily_movements_agg
            daily_movements_agg = item_movements.groupby(['Fecha', 'Site', 'Item']).agg(
                Movimientos=('Movimientos', 'sum'),
                Entradas=('Entradas', 'sum'),
                Salidas=('Salidas', 'sum')
            ).reset_index()
        except Exception as e:
            # st.error(f"ERROR: Ocurrió un error inesperado al agrupar daily_movements_agg: {e}. Tipo de error: {type(e).__name__}")
            raise

        try:
            df_item_combined = pd.merge(
                df_item_daily,
                daily_movements_agg,
                on=['Fecha', 'Item'], 
                how='left'
            )
        except Exception as e:
            # st.error(f"ERROR: Ocurrió un error inesperado al hacer merge en df_item_combined: {e}. Tipo de error: {type(e).__name__}")
            raise

        df_item_combined[['Movimientos', 'Entradas', 'Salidas']] = df_item_combined[['Movimientos', 'Entradas', 'Salidas']].fillna(0)
        df_item_combined['Site'] = df_item_combined['Site'].fillna(default_site)

        df_item_combined = df_item_combined.sort_values(by='Fecha').reset_index(drop=True)

        # Calcular Saldo
        # Asegurarse de que 'Saldo' exista antes de intentar establecer valores
        if 'Saldo' not in df_item_combined.columns:
            df_item_combined['Saldo'] = 0.0 # Inicializar si no existe

        df_item_combined.loc[df_item_combined['Fecha'] == initial_balance_date, 'Saldo'] = initial_bal
        
        try:
            df_item_combined['DailyTotalMovimientosForSaldo'] = df_item_combined.groupby('Fecha')['Movimientos'].transform('sum')
        except Exception as e:
            # st.error(f"ERROR: Ocurrió un error inesperado al calcular DailyTotalMovimientosForSaldo: {e}. Tipo de error: {type(e).__name__}")
            raise

        temp_saldo = pd.Series(index=df_item_combined.index, dtype=float)
        
        initial_idx = df_item_combined[df_item_combined['Fecha'] == initial_balance_date].index
        if not initial_idx.empty:
            temp_saldo.loc[initial_idx[0]] = initial_bal
            for i in range(initial_idx[0] + 1, len(df_item_combined)):
                temp_saldo.loc[i] = temp_saldo.loc[i-1] + df_item_combined.loc[i, 'DailyTotalMovimientosForSaldo']
            for i in range(initial_idx[0] - 1, -1, -1):
                temp_saldo.loc[i] = temp_saldo.loc[i+1] - df_item_combined.loc[i+1, 'DailyTotalMovimientosForSaldo']

            df_item_combined['Saldo'] = temp_saldo
        else:
            df_item_combined['Saldo'] = initial_bal + df_item_combined['DailyTotalMovimientosForSaldo'].cumsum()

        df_item_combined.drop(columns=['DailyTotalMovimientosForSaldo'], inplace=True)

        df_processed_list.append(df_item_combined)


    if df_processed_list:
        df_processed = pd.concat(df_processed_list, ignore_index=True)
    else:
        df_processed = pd.DataFrame(columns=['Item', 'Fecha', 'Movimientos', 'Entradas', 'Salidas', 'Site', 'Saldo'])

    if 'Site' in df_processed.columns:
        df_processed['Site'] = df_processed['Site'].astype(str)
    else:
        df_processed['Site'] = 'N/A' 

    return df_processed.sort_values(by=['Item', 'Fecha']).reset_index(drop=True)
