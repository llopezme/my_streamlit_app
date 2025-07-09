# my_streamlit_app/modules/inventory_logic.py
import pandas as pd
from datetime import datetime

def process_movements(df_inventario: pd.DataFrame, df_movimientos: pd.DataFrame, df_caracteristicas: pd.DataFrame, initial_balance_date: datetime) -> pd.DataFrame:
    """
    Procesa los movimientos de inventario, calcula entradas/salidas y el saldo.
    Combina datos de inventario inicial, movimientos y características.
    """
    df_processed = pd.DataFrame()
    initial_stock_map = df_inventario.set_index('Item')['CurrentStock'].to_dict()
    
    # Obtener todos los ítems únicos de todos los archivos
    all_items = pd.concat([df_inventario['Item'], df_movimientos['Item'], df_caracteristicas['Item']]).unique()

    for item in all_items:
        initial_stock = initial_stock_map.get(item, 0)
        item_movements = df_movimientos[df_movimientos['Item'] == item].copy()
        item_movements = item_movements.sort_values(by='Fecha')

        if not item_movements.empty:
            # Crear una fila inicial para el saldo de cierre del día anterior
            initial_row = pd.DataFrame([{
                'Item': item,
                'Site': 'Inicial', # O el sitio por defecto si aplica, o simplemente N/A
                'Fecha': initial_balance_date,
                'Movimientos': 0,
                'Entradas': 0,
                'Salidas': 0
            }])
            df_item_combined = pd.concat([initial_row, item_movements], ignore_index=True)
            
            # Calcular Entradas y Salidas a partir de Movimientos
            df_item_combined['Entradas'] = df_item_combined['Movimientos'].apply(lambda x: x if x > 0 else 0)
            df_item_combined['Salidas'] = df_item_combined['Movimientos'].apply(lambda x: x if x < 0 else 0)
            
            df_item_combined = df_item_combined.sort_values(by='Fecha').reset_index(drop=True)
            
            # Calcular Saldo
            df_item_combined['Saldo'] = df_item_combined['Movimientos'].cumsum() + initial_stock
            # Asegurar que el saldo en la fecha inicial sea exactamente el initial_stock
            df_item_combined.loc[df_item_combined['Fecha'] == initial_balance_date, 'Saldo'] = initial_stock
            
            df_processed = pd.concat([df_processed, df_item_combined], ignore_index=True)
        elif item in initial_stock_map: # Ítems que están en inventario pero no tienen movimientos
            initial_row = pd.DataFrame([{
                'Item': item,
                'Site': 'Inicial', # O el sitio por defecto
                'Fecha': initial_balance_date,
                'Movimientos': 0,
                'Entradas': 0,
                'Salidas': 0,
                'Saldo': initial_stock
            }])
            df_processed = pd.concat([df_processed, initial_row], ignore_index=True)
    return df_processed
