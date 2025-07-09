# my_streamlit_app/modules/inventory_logic.py
import pandas as pd
from datetime import datetime

def process_movements(df_inventario: pd.DataFrame, df_movimientos: pd.DataFrame, df_caracteristicas: pd.DataFrame, initial_balance_date: datetime) -> pd.DataFrame:
    """
    Procesa los movimientos de inventario, calcula entradas/salidas y el saldo diario.
    Combina datos de inventario inicial, movimientos y características, asegurando que 'Site' se propague.
    """
    # --- DEBUG: Mostrar columnas y estado de DataFrames al inicio de la función ---
    print("\n--- DEBUG: Dentro de process_movements (Inicio de la función) ---")
    print("Columnas de df_inventario al inicio:", df_inventario.columns.tolist())
    print("df_inventario está vacío al inicio:", df_inventario.empty)
    print("Columnas de df_movimientos al inicio:", df_movimientos.columns.tolist())
    print("df_movimientos está vacío al inicio:", df_movimientos.empty)
    print("-------------------------------------------\n")
    # --- FIN DEBUG ---

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
        initial_balance_map = df_inventario.set_index('Item')['InitialBalance'].to_dict()
        item_site_map = df_inventario.set_index('Item')['Site'].to_dict()

    # Asegurarse de que 'Fecha' sea tipo datetime en df_movimientos
    df_movimientos['Fecha'] = pd.to_datetime(df_movimientos['Fecha'])

    # Calcular Entradas y Salidas en df_movimientos
    df_movimientos['Entradas'] = df_movimientos['Movimientos'].apply(lambda x: x if x > 0 else 0)
    df_movimientos['Salidas'] = df_movimientos['Movimientos'].apply(lambda x: x if x < 0 else 0)

    df_processed_list = []

    # Handle case where both df_inventario and df_movimientos might be empty
    if df_inventario.empty and df_movimientos.empty:
        print("DEBUG: Ambos df_inventario y df_movimientos están vacíos. Retornando DataFrame vacío.")
        return pd.DataFrame(columns=['Item', 'Fecha', 'Movimientos', 'Entradas', 'Salidas', 'Site', 'Saldo'])

    # Obtener todos los ítems únicos de todos los archivos para asegurar que todos se procesen
    items_from_inventario = df_inventario['Item'].unique().tolist() if not df_inventario.empty else []
    items_from_movimientos = df_movimientos['Item'].unique().tolist() if not df_movimientos.empty else []
    
    # Combine and get unique items, filtering out any empty strings that might have resulted from fillna('')
    all_items = [item for item in pd.Series(items_from_inventario + items_from_movimientos).unique() if item != '']
    print(f"DEBUG: all_items para procesar: {all_items}")


    for item in all_items:
        print(f"\n--- DEBUG: Procesando ítem: '{item}' ---")
        # Skip processing if item is an empty string (from fillna('') on empty 'Item' values)
        if item == '':
            print("DEBUG: Ítem vacío encontrado, saltando.")
            continue

        initial_bal = initial_balance_map.get(item, 0)
        default_site = item_site_map.get(item, 'N/A') 
        print(f"DEBUG: Saldo inicial para '{item}': {initial_bal}, Site por defecto: '{default_site}'")

        item_movements = df_movimientos[df_movimientos['Item'] == item].copy()
        print(f"DEBUG: Columnas de item_movements para '{item}': {item_movements.columns.tolist()}")
        print(f"DEBUG: item_movements para '{item}' está vacío: {item_movements.empty}")
        if not item_movements.empty:
            print(f"DEBUG: Primeras 3 filas de item_movements para '{item}':\n{item_movements.head(3)}")


        # Determinar el rango de fechas para este ítem
        start_date_for_item = initial_balance_date
        if not item_movements.empty:
            end_date_for_item = item_movements['Fecha'].max()
        else:
            end_date_for_item = initial_balance_date 
        print(f"DEBUG: Rango de fechas para '{item}': {start_date_for_item} a {end_date_for_item}")

        full_date_range = pd.date_range(start=start_date_for_item, end=end_date_for_item, freq='D')
        
        # Crear un DataFrame base con todas las fechas del rango para el ítem
        df_item_daily = pd.DataFrame({'Fecha': full_date_range, 'Item': item})
        print(f"DEBUG: Columnas de df_item_daily para '{item}': {df_item_daily.columns.tolist()}")
        
        # Ensure 'Site' column exists in item_movements before grouping
        if 'Site' not in item_movements.columns:
            print(f"DEBUG: Columna 'Site' no encontrada en item_movements para '{item}'. Asignando default_site.")
            item_movements['Site'] = default_site 

        daily_movements_agg = item_movements.groupby(['Fecha', 'Site']).agg(
            Movimientos=('Movimientos', 'sum'),
            Entradas=('Entradas', 'sum'),
            Salidas=('Salidas', 'sum')
        ).reset_index()
        print(f"DEBUG: Columnas de daily_movements_agg para '{item}': {daily_movements_agg.columns.tolist()}")

        df_item_combined = pd.merge(
            df_item_daily,
            daily_movements_agg,
            on=['Fecha', 'Item'], 
            how='left'
        )
        print(f"DEBUG: Columnas de df_item_combined después del merge para '{item}': {df_item_combined.columns.tolist()}")
        print(f"DEBUG: df_item_combined para '{item}' está vacío: {df_item_combined.empty}")

        df_item_combined[['Movimientos', 'Entradas', 'Salidas']] = df_item_combined[['Movimientos', 'Entradas', 'Salidas']].fillna(0)
        df_item_combined['Site'] = df_item_combined['Site'].fillna(default_site)
        print(f"DEBUG: Columnas de df_item_combined después de fillna para '{item}': {df_item_combined.columns.tolist()}")

        df_item_combined = df_item_combined.sort_values(by='Fecha').reset_index(drop=True)

        # Calcular Saldo
        df_item_combined.loc[df_item_combined['Fecha'] == initial_balance_date, 'Saldo'] = initial_bal
        
        df_item_combined['DailyTotalMovimientosForSaldo'] = df_item_combined.groupby('Fecha')['Movimientos'].transform('sum')

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
        print(f"DEBUG: Ítem '{item}' procesado y añadido a la lista.")

    if df_processed_list:
        df_processed = pd.concat(df_processed_list, ignore_index=True)
        print(f"DEBUG: Columnas de df_processed final antes de return: {df_processed.columns.tolist()}")
    else:
        df_processed = pd.DataFrame(columns=['Item', 'Fecha', 'Movimientos', 'Entradas', 'Salidas', 'Site', 'Saldo'])
        print("DEBUG: df_processed_list estaba vacío. Retornando DataFrame vacío con columnas predefinidas.")

    if 'Site' in df_processed.columns:
        df_processed['Site'] = df_processed['Site'].astype(str)
    else:
        df_processed['Site'] = 'N/A' 
        print("DEBUG: La columna 'Site' no estaba en df_processed, se añadió como 'N/A'.")

    print("--- DEBUG: Fin de process_movements ---")
    return df_processed.sort_values(by=['Item', 'Fecha']).reset_index(drop=True)
