# my_streamlit_app/modules/utils.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def safe_get_value(df_row: pd.DataFrame, col: str):
    """
    Intenta obtener un valor de una columna de un DataFrame, devolviendo "N/A"
    si el DataFrame está vacío, la columna no existe o el valor es nulo.
    """
    if not df_row.empty and col in df_row.columns:
        # Asegurarse de que la serie de la columna no esté vacía antes de acceder a iloc[0]
        if not df_row[col].empty and pd.notna(df_row[col].iloc[0]):
            return str(df_row[col].iloc[0])
    return "N/A"

def display_item_characteristics(selected_item: str, df_caracteristicas: pd.DataFrame,
                                 df_inventario: pd.DataFrame, df_display: pd.DataFrame,
                                 mean_without_outliers_abs: float, upper_bound_outlier_abs: float):
    """
    Muestra la tabla de características del ítem seleccionado en Streamlit.
    """
    st.subheader("Características del Ítem Seleccionado:")
    
    # Verificar si la columna 'Site' existe en df_inventario al inicio
    if 'Site' not in df_inventario.columns:
        st.error("Error: La columna 'Site' no se encontró en el archivo de inventario. Por favor, verifica el nombre de la columna en 'inventario.xlsx' (sensibilidad a mayúsculas/minúsculas, espacios).")
        return # Detener la ejecución de la función si la columna crítica falta

    item_caracteristicas_row = df_caracteristicas[df_caracteristicas['Item'] == selected_item]
    item_inventario_row = df_inventario[df_inventario['Item'] == selected_item]

    total_salidas_item = df_display['Salidas'].abs().sum()

    # Calculate the initial balance (CurrentStock + StockSeguridad) for display
    initial_balance_for_display = 0
    if not item_inventario_row.empty and 'CurrentStock' in item_inventario_row.columns and 'StockSeguridad' in item_inventario_row.columns:
        initial_balance_for_display = item_inventario_row['CurrentStock'].iloc[0] + item_inventario_row['StockSeguridad'].iloc[0]

    if not item_caracteristicas_row.empty or not item_inventario_row.empty:
        # Corrected: Get 'Site' from df_inventario as per user's clarification
        site_val = safe_get_value(item_inventario_row, 'Site') 
        descripcion_val = safe_get_value(item_caracteristicas_row, 'Descripcion')
        adi_val = safe_get_value(item_caracteristicas_row, 'ADI')
        cv_val = safe_get_value(item_caracteristicas_row, 'CV')
        metodo_val = safe_get_value(item_caracteristicas_row, 'Metodo')
        abc_class_val = safe_get_value(item_caracteristicas_row, 'ABC Class')
        lead_time_val = safe_get_value(item_inventario_row, 'LeadTime')
        stock_seguridad_val = safe_get_value(item_inventario_row, 'StockSeguridad')

        carac_data = {
            "Métrica": [
                "Item", "Site", "Descripción", "ADI", "CV", "Método", "ABC Class",
                "Lead Time", "Stock de seguridad", "Saldo Inicial", "Salidas de Inventario",
                "Media sin Outliers (Salidas)",
                "Límite Superior Outlier (Salidas)"
            ],
            "Valor": [
                selected_item,
                site_val,
                descripcion_val,
                adi_val,
                cv_val,
                metodo_val,
                abc_class_val,
                lead_time_val,
                stock_seguridad_val,
                str(initial_balance_for_display), # Display the calculated initial balance
                str(total_salidas_item),
                f"{mean_without_outliers_abs:.2f}",
                f"{upper_bound_outlier_abs:.2f}"
            ]
        }
        st.dataframe(pd.DataFrame(carac_data).set_index("Métrica"))
    else:
        st.warning(f"No se encontró información completa de características para el Ítem: **{selected_item}** en los archivos 'caracteristicas.xlsx' o 'inventario.xlsx'.")


def display_movement_charts(selected_item: str, df_display: pd.DataFrame):
    """
    Muestra el gráfico de entradas y salidas, y el saldo en Streamlit.
    """
    st.subheader("Gráfico de Entradas, Salidas y Saldo:")
    fig = go.Figure()

    # Add Entradas as Bar
    fig.add_trace(go.Bar(
        x=df_display['Fecha'], y=df_display['Entradas'], name='Entradas',
        marker_color='rgb(49,130,189)',
        hovertemplate='Fecha: %{x|%Y-%m-%d}<br>Entradas: %{y}<extra></extra>'
    ))

    # Add Salidas as Bar
    fig.add_trace(go.Bar(
        x=df_display['Fecha'], y=df_display['Salidas'], name='Salidas',
        marker_color='rgb(204,0,0)',
        hovertemplate='Fecha: %{x|%Y-%m-%d}<br>Salidas: %{y}<extra></extra>'
    ))

    # Add Saldo as Line
    fig.add_trace(go.Scatter(
        x=df_display['Fecha'], y=df_display['Saldo'], mode='lines', name='Saldo',
        line=dict(color='rgb(0,128,0)', width=2), # Green line for balance
        hovertemplate='Fecha: %{x|%Y-%m-%d}<br>Saldo: %{y}<extra></extra>'
    ))

    fig.update_layout(
        title=f'Movimientos y Saldo de "{selected_item}" a lo largo del tiempo',
        xaxis_title="Fecha", yaxis_title="Cantidad (Unidades)",
        legend_title="Leyenda", hovermode="x unified", barmode='relative'
    )
    fig.update_xaxes(
        rangeselector_buttons=list([
            dict(count=1, label="1m", step="month", stepmode="backward"),
            dict(count=6, label="6m", step="month", stepmode="backward"),
            dict(count=1, label="YTD", step="year", stepmode="todate"),
            dict(count=1, label="1y", step="year", stepmode="backward"),
            dict(step="all")
        ])
    )
    st.plotly_chart(fig, use_container_width=True)


def display_movement_details(df_display: pd.DataFrame):
    """
    Muestra la tabla de detalle de movimientos en Streamlit.
    """
    st.subheader("Detalle de Movimientos:")
    # Include 'Saldo' in the displayed dataframe
    st.dataframe(df_display[['Fecha', 'Entradas', 'Salidas', 'Movimientos', 'Saldo', 'Site']].sort_values(by='Fecha').set_index('Fecha'))
