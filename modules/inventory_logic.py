# my_streamlit_app/modules/inventory_logic.py
import pandas as pd
from datetime import datetime

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
    # Convertir a string y rellenar NaN con cadena vacía para evitar errores en set_index o unique()
    df_inventario['Item'] = df_inventario['Item'].astype(str).fillna('')
    df_movimientos['Item'] = df_movimientos['Item'].astype(str).fillna('')
    # --- END: Robustness checks for 'Item' column and DataFrame emptiness ---

    # 1. Calcular el saldo inicial para cada ítem (CurrentStock + StockSeguridad)
    # Asegurarse de que 'Site' esté en df_inventario antes de usarlo
    if 'Site' not in df_inventario.columns:
        # Si 'Site' no está en df_inventario, se asigna un valor por defecto
        df_inventario['Site'] = 'N/A_Inventario' 
        # Considera si esto debería ser un error fatal o una advertencia en app.py si 'Site' es crítico aquí.

    # Ensure 'CurrentStock' and 'StockSeguridad' are numeric before addition
    df_inventario['CurrentStock'] = pd.to_numeric(df_inventario['CurrentStock'], errors='coerce').fillna(0)
    df_inventario['StockSeguridad'] = pd.to_numeric(df_inventario['StockSeguridad'], errors='coerce').fillna(0)

    df_inventario['InitialBalance'] = df_inventario['CurrentStock'] + df_inventario['StockSeguridad']
    
    # Check for empty df_inventario before setting index to avoid errors
    if df_inventario.empty:
        initial_balance_map = {}
        item_site_map = {}
    else:
        initial_balance_map = df_inventario.set_index('Item')['InitialBalance'].to_dict()
        item_site_map = df_inventario.set_index('Item')['Site'].to_dict() # Mapa para obtener el sitio por defecto del inventario

    # Asegurarse de que 'Fecha' sea tipo datetime en df_movimientos
    df_movimientos['Fecha'] = pd.to_datetime(df_movimientos['Fecha'])

    # Calcular Entradas y Salidas en df_movimientos
    df_movimientos['Entradas'] = df_movimientos['Movimientos'].apply(lambda x: x if x > 0 else 0)
    df_movimientos['Salidas'] = df_movimientos['Movimientos'].apply(lambda x: x if x < 0 else 0)

    df_processed_list = []

    # Handle case where both df_inventario and df_movimientos might be empty
    if df_inventario.empty and df_movimientos.empty:
        # Return an empty DataFrame with all expected columns if no data is available
        return pd.DataFrame(columns=['Item', 'Fecha', 'Movimientos', 'Entradas', 'Salidas', 'Site', 'Saldo'])

    # Obtener todos los ítems únicos de todos los archivos para asegurar que todos se procesen
    # Handle cases where one of the DFs might be empty or missing 'Item' after previous checks
    items_from_inventario = df_inventario['Item'].unique() if not df_inventario.empty else []
    items_from_movimientos = df_movimientos['Item'].unique() if not df_movimientos.empty else []
    all_items = pd.Series(list(items_from_inventario) + list(items_from_movimientos)).unique()


    for item in all_items:
        # Skip processing if item is an empty string (from fillna('') on empty 'Item' values)
        if item == '':
            continue

        initial_bal = initial_balance_map.get(item, 0)
        default_site = item_site_map.get(item, 'N/A') # Obtener el sitio por defecto del inventario

        item_movements = df_movimientos[df_movimientos['Item'] == item].copy()

        # Determinar el rango de fechas para este ítem
        start_date_for_item = initial_balance_date
        if not item_movements.empty:
            end_date_for_item = item_movements['Fecha'].max()
        else:
            end_date_for_item = initial_balance_date # If no movements, the range is just the initial date

        full_date_range = pd.date_range(start=start_date_for_item, end=end_date_for_item, freq='D')
        
        # Crear un DataFrame base con todas las fechas del rango para el ítem
        df_item_daily = pd.DataFrame({'Fecha': full_date_range, 'Item': item})
        
        # Agrupar movements by Fecha and Site, summing quantities
        # This is crucial to keep 'Site' in the daily summary if there are movements.
        # If an item has movements from multiple sites on one day, this will create multiple rows for that day.
        # Ensure 'Site' column exists in item_movements before grouping
        if 'Site' not in item_movements.columns:
            # If 'Site' is missing in item_movements for some reason, assign the default site
            item_movements['Site'] = default_site 

        daily_movements_agg = item_movements.groupby(['Fecha', 'Site']).agg(
            Movimientos=('Movimientos', 'sum'),
            Entradas=('Entradas', 'sum'),
            Salidas=('Salidas', 'sum')
        ).reset_index()

        # Merge the daily movements summary (including Site) with the full date range DataFrame
        # Use a 'left' merge to keep all dates from the full range.
        df_item_combined = pd.merge(
            df_item_daily,
            daily_movements_agg,
            on=['Fecha', 'Item'], # Merge by Fecha and Item
            how='left'
        )

        # Fill NaN values for Movimientos, Entradas, Salidas with 0 for days without activity
        df_item_combined[['Movimientos', 'Entradas', 'Salidas']] = df_item_combined[['Movimientos', 'Entradas', 'Salidas']].fillna(0)
        
        # Fill NaN values in 'Site' with the default site from inventory for the item
        # If a day had no movements, its 'Site' will be NaN after the merge.
        # Fill it with the item's default site from inventory.
        df_item_combined['Site'] = df_item_combined['Site'].fillna(default_site)

        # Sort by date for cumulative balance calculation
        df_item_combined = df_item_combined.sort_values(by='Fecha').reset_index(drop=True)

        # Calcular Saldo
        # El saldo inicial para la initial_balance_date
        df_item_combined.loc[df_item_combined['Fecha'] == initial_balance_date, 'Saldo'] = initial_bal
        
        # Calcular el saldo para las fechas posteriores
        # Necesitamos sumar los movimientos diarios totales para el saldo, no por sitio si hay múltiples.
        # Creamos una columna temporal con los movimientos totales por día para el cálculo del saldo.
        df_item_combined['DailyTotalMovimientosForSaldo'] = df_item_combined.groupby('Fecha')['Movimientos'].transform('sum')

        # Usar un enfoque iterativo para el saldo para asegurar la acumulación correcta
        temp_saldo = pd.Series(index=df_item_combined.index, dtype=float)
        
        # Encontrar el índice de la fecha inicial de balance
        initial_idx = df_item_combined[df_item_combined['Fecha'] == initial_balance_date].index
        if not initial_idx.empty:
            temp_saldo.loc[initial_idx[0]] = initial_bal
            # Calculate forward
            for i in range(initial_idx[0] + 1, len(df_item_combined)):
                temp_saldo.loc[i] = temp_saldo.loc[i-1] + df_item_combined.loc[i, 'DailyTotalMovimientosForSaldo']
            # Calculate backward (if there are dates before initial_balance_date that should not have balance)
            # Although with full_date_range starting at initial_balance_date, this should not be necessary.
            # However, if the first date in df_item_combined is earlier than initial_balance_date, this is useful.
            for i in range(initial_idx[0] - 1, -1, -1):
                temp_saldo.loc[i] = temp_saldo.loc[i+1] - df_item_combined.loc[i+1, 'DailyTotalMovimientosForSaldo']

            df_item_combined['Saldo'] = temp_saldo
        else:
            # Fallback if initial_balance_date is not in the range (should be handled by full_date_range)
            df_item_combined['Saldo'] = initial_bal + df_item_combined['DailyTotalMovimientosForSaldo'].cumsum()

        # Remove the temporary column
        df_item_combined.drop(columns=['DailyTotalMovimientosForSaldo'], inplace=True)

        df_processed_list.append(df_item_combined)

    if df_processed_list:
        df_processed = pd.concat(df_processed_list, ignore_index=True)
    else:
        # If no items at all, return an empty DataFrame with expected columns
        df_processed = pd.DataFrame(columns=['Item', 'Fecha', 'Movimientos', 'Entradas', 'Salidas', 'Site', 'Saldo'])

    # Ensure 'Site' column is of string type in the final DataFrame
    if 'Site' in df_processed.columns:
        df_processed['Site'] = df_processed['Site'].astype(str)
    else:
        df_processed['Site'] = 'N/A' # If for some reason it's still missing, add it as 'N/A'

    return df_processed.sort_values(by=['Item', 'Fecha']).reset_index(drop=True)
