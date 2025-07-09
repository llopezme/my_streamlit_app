# my_streamlit_app/modules/inventory_logic.py
import pandas as pd
from datetime import datetime

def process_movements(df_inventario: pd.DataFrame, df_movimientos: pd.DataFrame, df_caracteristicas: pd.DataFrame, initial_balance_date: datetime) -> pd.DataFrame:
    """
    Procesa los movimientos de inventario, calcula entradas/salidas y el saldo diario.
    Combina datos de inventario inicial, movimientos y características, asegurando que 'Site' se propague.
    """
    # 1. Calcular el saldo inicial para cada ítem (CurrentStock + StockSeguridad)
    # Asegurarse de que 'Site' esté en df_inventario antes de usarlo
    if 'Site' not in df_inventario.columns:
        # Si 'Site' no está en df_inventario, se asigna un valor por defecto
        df_inventario['Site'] = 'N/A_Inventario' 
        # Considera si esto debería ser un error fatal o una advertencia en app.py si 'Site' es crítico aquí.

    df_inventario['InitialBalance'] = df_inventario['CurrentStock'] + df_inventario['StockSeguridad']
    initial_balance_map = df_inventario.set_index('Item')['InitialBalance'].to_dict()
    item_site_map = df_inventario.set_index('Item')['Site'].to_dict() # Mapa para obtener el sitio por defecto del inventario

    # Asegurarse de que 'Fecha' sea tipo datetime en df_movimientos
    df_movimientos['Fecha'] = pd.to_datetime(df_movimientos['Fecha'])

    # Calcular Entradas y Salidas en df_movimientos
    df_movimientos['Entradas'] = df_movimientos['Movimientos'].apply(lambda x: x if x > 0 else 0)
    df_movimientos['Salidas'] = df_movimientos['Movimientos'].apply(lambda x: x if x < 0 else 0)

    df_processed_list = []

    # Obtener todos los ítems únicos de todos los archivos para asegurar que todos se procesen
    all_items = pd.concat([df_inventario['Item'], df_movimientos['Item']]).unique()

    for item in all_items:
        initial_bal = initial_balance_map.get(item, 0)
        default_site = item_site_map.get(item, 'N/A') # Obtener el sitio por defecto del inventario

        item_movements = df_movimientos[df_movimientos['Item'] == item].copy()

        # Determinar el rango de fechas para este ítem
        start_date_for_item = initial_balance_date
        if not item_movements.empty:
            end_date_for_item = item_movements['Fecha'].max()
        else:
            end_date_for_item = initial_balance_date # Si no hay movimientos, el rango es solo la fecha inicial

        full_date_range = pd.date_range(start=start_date_for_item, end=end_date_for_item, freq='D')
        
        # Crear un DataFrame base con todas las fechas del rango para el ítem
        df_item_daily = pd.DataFrame({'Fecha': full_date_range, 'Item': item})
        
        # Agrupar movimientos por Fecha y Site, sumando las cantidades
        # Esto es crucial para mantener 'Site' en el resumen diario si hay movimientos.
        # Si un ítem tiene movimientos de múltiples sitios en un día, esto creará múltiples filas para ese día.
        daily_movements_agg = item_movements.groupby(['Fecha', 'Site']).agg(
            Movimientos=('Movimientos', 'sum'),
            Entradas=('Entradas', 'sum'),
            Salidas=('Salidas', 'sum')
        ).reset_index()

        # Fusionar el resumen de movimientos diario (incluyendo Site) con el DataFrame de todas las fechas
        # Usamos un merge 'left' para mantener todas las fechas del rango completo.
        df_item_combined = pd.merge(
            df_item_daily,
            daily_movements_agg,
            on=['Fecha', 'Item'], # Fusionar por Fecha e Item
            how='left'
        )

        # Rellenar los valores NaN para Movimientos, Entradas, Salidas con 0 para los días sin actividad
        df_item_combined[['Movimientos', 'Entradas', 'Salidas']] = df_item_combined[['Movimientos', 'Entradas', 'Salidas']].fillna(0)
        
        # Rellenar los valores NaN en 'Site' con el sitio por defecto del inventario para el ítem
        # Si un día no tuvo movimientos, su 'Site' será NaN después del merge.
        # Lo rellenamos con el sitio por defecto del ítem desde el inventario.
        df_item_combined['Site'] = df_item_combined['Site'].fillna(default_site)

        # Ordenar por fecha para el cálculo acumulativo del saldo
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
            # Calcular hacia adelante
            for i in range(initial_idx[0] + 1, len(df_item_combined)):
                temp_saldo.loc[i] = temp_saldo.loc[i-1] + df_item_combined.loc[i, 'DailyTotalMovimientosForSaldo']
            # Calcular hacia atrás (si hay fechas antes de initial_balance_date que no deberían tener saldo)
            # Aunque con full_date_range empezando en initial_balance_date, esto no debería ser necesario.
            # Sin embargo, si la primera fecha en df_item_combined es anterior a initial_balance_date, esto es útil.
            for i in range(initial_idx[0] - 1, -1, -1):
                temp_saldo.loc[i] = temp_saldo.loc[i+1] - df_item_combined.loc[i+1, 'DailyTotalMovimientosForSaldo']

            df_item_combined['Saldo'] = temp_saldo
        else:
            # Fallback si initial_balance_date no está en el rango (debería ser manejado por full_date_range)
            df_item_combined['Saldo'] = initial_bal + df_item_combined['DailyTotalMovimientosForSaldo'].cumsum()

        # Eliminar la columna temporal
        df_item_combined.drop(columns=['DailyTotalMovimientosForSaldo'], inplace=True)

        df_processed_list.append(df_item_combined)

    if df_processed_list:
        df_processed = pd.concat(df_processed_list, ignore_index=True)
    else:
        # Si no hay ítems en absoluto, retornar un DataFrame vacío con las columnas esperadas
        df_processed = pd.DataFrame(columns=['Item', 'Fecha', 'Movimientos', 'Entradas', 'Salidas', 'Site', 'Saldo'])

    # Asegurar que la columna 'Site' sea de tipo string en el DataFrame final
    if 'Site' in df_processed.columns:
        df_processed['Site'] = df_processed['Site'].astype(str)
    else:
        df_processed['Site'] = 'N/A' # Si por alguna razón sigue faltando, añadirla como 'N/A'

    return df_processed.sort_values(by=['Item', 'Fecha']).reset_index(drop=True)
