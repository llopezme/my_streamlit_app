# my_streamlit_app/modules/utils.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def display_item_characteristics(selected_item: str, df_caracteristicas: pd.DataFrame, 
                                 df_inventario: pd.DataFrame, df_display: pd.DataFrame,
                                 mean_without_outliers_abs: float, upper_bound_outlier_abs: float):
    """
    Muestra la tabla de características del ítem seleccionado en Streamlit.
    """
    st.subheader("Características del Ítem Seleccionado:")
    
    item_caracteristicas_row = df_caracteristicas[df_caracteristicas['Item'] == selected_item]
    item_inventario_row = df_inventario[df_inventario['Item'] == selected_item]

    total_salidas_item = df_display['Salidas'].abs().sum()

    if not item_caracteristicas_row.empty and not item_inventario_row.empty:
        carac_data = {
            "Métrica": [
                "Item", "Site", "Descripción", "ADI", "CV", "Método", "ABC Class",
                "Lead Time", "Stock de seguridad", "Salidas de Inventario",
                "Media sin Outliers (Salidas)",
                "Límite Superior Outlier (Salidas)"
            ],
            "Valor": [
                selected_item,
                item_caracteristicas_row['Site'].iloc[0],
                item_caracteristicas_row['Descripcion'].iloc[0],
                item_caracteristicas_row['ADI'].iloc[0],
                item_caracteristicas_row['CV'].iloc[0],
                item_caracteristicas_row['Metodo'].iloc[0],
                item_caracteristicas_row['ABC Class'].iloc[0],
                item_inventario_row['LeadTime'].iloc[0],
                item_inventario_row['StockSeguridad'].iloc[0], # Columna renombrada a 'StockSeguridad'
                total_salidas_item,
                f"{mean_without_outliers_abs:.2f}",
                f"{upper_bound_outlier_abs:.2f}"
            ]
        }
        st.dataframe(pd.DataFrame(carac_data).set_index("Métrica"))
    else:
        st.warning(f"No se encontró información completa de características para el Ítem: **{selected_item}** en los archivos 'caracteristicas.xlsx' o 'inventario.xlsx'.")


def display_movement_charts(selected_item: str, df_display: pd.DataFrame):
    """
    Muestra el gráfico de entradas y salidas en Streamlit.
    """
    st.subheader("Gráfico de Entradas y Salidas:")
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_display['Fecha'], y=df_display['Entradas'], name='Entradas',
        marker_color='rgb(49,130,189)',
        hovertemplate='Fecha: %{x|%Y-%m-%d}<br>Entradas: %{y}<extra></extra>'
    ))

    fig.add_trace(go.Bar(
        x=df_display['Fecha'], y=df_display['Salidas'], name='Salidas',
        marker_color='rgb(204,0,0)',
        hovertemplate='Fecha: %{x|%Y-%m-%d}<br>Salidas: %{y}<extra></extra>'
    ))

    fig.update_layout(
        title=f'Entradas y Salidas de "{selected_item}" a lo largo del tiempo',
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
    st.dataframe(df_display[['Fecha', 'Entradas', 'Salidas', 'Site']].sort_values(by='Fecha').set_index('Fecha'))
