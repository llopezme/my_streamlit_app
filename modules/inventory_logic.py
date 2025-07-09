# my_streamlit_app/modules/inventory_logic.py
import pandas as pd
from datetime import datetime

def process_movements(df_inventario: pd.DataFrame, df_movimientos: pd.DataFrame, df_caracteristicas: pd.DataFrame, initial_balance_date: datetime) -> pd.DataFrame:
    """
    Procesa los movimientos de inventario, calcula entradas/salidas y el saldo diario.
    Combina datos de inventario inicial, movimientos y características.
    """
    # 1. Calcular el saldo inicial para cada ítem (CurrentStock + StockSeguridad)
    df_inventario['InitialBalance'] = df_inventario['CurrentStock'] + df_inventario['StockSeguridad']
    initial_balance_map = df_inventario.set_index('Item')['InitialBalance'].to_dict()

    # Asegurarse de que 'Fecha' sea tipo datetime en df_movimientos
    df_movimientos['Fecha'] = pd.to_datetime(df_movimientos['Fecha'])

    # Calcular Entradas y Salidas
    df_movimientos['Entradas'] = df_movimientos['Movimientos'].apply(lambda x: x if x > 0 else 0)
    df_movimientos['Salidas'] = df_movimientos['Movimientos'].apply(lambda x: x if x < 0 else 0)

    df_processed_list = []

    # Obtener todos los ítems únicos de todos los archivos para asegurar que todos se procesen
    # Esto incluye ítems que solo están en inventario pero no tienen movimientos.
    all_items = pd.concat([df_inventario['Item'], df_movimientos['Item']]).unique()

    for item in all_items:
        initial_bal = initial_balance_map.get(item, 0) # Obtener el saldo inicial para el ítem

        # Filtrar movimientos para el ítem actual
        item_movements = df_movimientos[df_movimientos['Item'] == item].copy()

        if item_movements.empty:
            # Si no hay movimientos para el ítem, pero tiene un saldo inicial, añadir solo una fila con el saldo inicial
            if item in initial_balance_map:
                df_item_daily = pd.DataFrame([{
                    'Item': item,
                    'Fecha': initial_balance_date,
                    'Movimientos': 0,
                    'Entradas': 0,
                    'Salidas': 0,
                    'Saldo': initial_bal
                }])
                df_processed_list.append(df_item_daily)
            continue # Pasar al siguiente ítem si no hay movimientos ni saldo inicial

        # Determinar el rango de fechas para este ítem
        # El rango debe empezar en initial_balance_date y terminar en la última fecha de movimiento
        # o initial_balance_date si no hay movimientos posteriores.
        start_date_for_item = initial_balance_date
        end_date_for_item = item_movements['Fecha'].max()

        # Crear un rango de fechas diario continuo para el ítem
        full_date_range = pd.date_range(start=start_date_for_item, end=end_date_for_item, freq='D')
        
        # Agrupar movimientos por día y sumar para obtener el movimiento neto diario
        # También sumar Entradas y Salidas por día
        daily_summary = item_movements.groupby('Fecha').agg(
            Movimientos=('Movimientos', 'sum'),
            Entradas=('Entradas', 'sum'),
            Salidas=('Salidas', 'sum')
        ).reset_index()

        # Crear un DataFrame con todas las fechas del rango y fusionar los movimientos diarios
        df_item_daily = pd.DataFrame({'Fecha': full_date_range})
        df_item_daily['Item'] = item
        df_item_daily = pd.merge(df_item_daily, daily_summary, on='Fecha', how='left')
        
        # Rellenar los días sin movimientos con 0
        df_item_daily[['Movimientos', 'Entradas', 'Salidas']] = df_item_daily[['Movimientos', 'Entradas', 'Salidas']].fillna(0)

        # Ordenar por fecha para el cálculo acumulativo
        df_item_daily = df_item_daily.sort_values(by='Fecha').reset_index(drop=True)

        # Calcular el Saldo diario
        # El saldo en la initial_balance_date es el initial_bal.
        # Para las fechas posteriores, es el saldo del día anterior + los movimientos del día actual.
        
        # Encontrar el índice de la initial_balance_date en el DataFrame diario
        initial_date_idx = df_item_daily[df_item_daily['Fecha'] == initial_balance_date].index

        if not initial_date_idx.empty:
            # Si la initial_balance_date está en el DataFrame, establecer su saldo
            df_item_daily.loc[initial_date_idx[0], 'Saldo'] = initial_bal
            
            # Calcular el saldo para los días siguientes
            for i in range(initial_date_idx[0] + 1, len(df_item_daily)):
                df_item_daily.loc[i, 'Saldo'] = df_item_daily.loc[i-1, 'Saldo'] + df_item_daily.loc[i, 'Movimientos']
        else:
            # Este caso no debería ocurrir si full_date_range se construye correctamente
            # incluyendo initial_balance_date. Pero como fallback, si no se encuentra,
            # asumimos que el primer saldo es el initial_bal y hacemos un cumsum.
            df_item_daily['Saldo'] = initial_bal + df_item_daily['Movimientos'].cumsum()

        df_processed_list.append(df_item_daily)

    if df_processed_list:
        df_processed = pd.concat(df_processed_list, ignore_index=True)
    else:
        # Si no hay ítems en absoluto, retornar un DataFrame vacío con las columnas esperadas
        df_processed = pd.DataFrame(columns=['Item', 'Fecha', 'Movimientos', 'Entradas', 'Salidas', 'Saldo'])

    return df_processed.sort_values(by=['Item', 'Fecha']).reset_index(drop=True)

