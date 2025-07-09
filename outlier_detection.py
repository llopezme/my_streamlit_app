# my_streamlit_app/modules/outlier_detection.py
import pandas as pd
import streamlit as st

def calculate_outliers_and_mean_without_outliers(df_display_filtered_by_date: pd.DataFrame):
    """
    Calcula el límite superior de outliers y la media de salidas sin outliers
    para el DataFrame filtrado por fecha.
    Retorna: upper_bound_outlier_abs, mean_without_outliers_abs, df_salidas_para_outliers
    """
    df_salidas_para_outliers = df_display_filtered_by_date[df_display_filtered_by_date['Movimientos'] < 0].copy()
    
    upper_bound_outlier_abs = 0.0
    mean_without_outliers_abs = 0.0

    if not df_salidas_para_outliers.empty:
        salidas_abs = df_salidas_para_outliers['Movimientos'].abs()

        if not salidas_abs.empty and salidas_abs.nunique() > 1: # Asegurar que hay variabilidad para calcular cuartiles
            Q1_salidas_abs = salidas_abs.quantile(0.25)
            Q3_salidas_abs = salidas_abs.quantile(0.75)
            IQR_salidas_abs = Q3_salidas_abs - Q1_salidas_abs
            upper_bound_outlier_abs = Q3_salidas_abs + 1.5 * IQR_salidas_abs

            # Filtrar los valores que NO son outliers para la media
            non_outlier_salidas_abs = salidas_abs[salidas_abs <= upper_bound_outlier_abs]
            if not non_outlier_salidas_abs.empty:
                mean_without_outliers_abs = non_outlier_salidas_abs.mean()
        elif not salidas_abs.empty: # Caso de salidas con un solo valor único o sin variabilidad
            mean_without_outliers_abs = salidas_abs.mean()
            upper_bound_outlier_abs = salidas_abs.max() # Si no hay variabilidad, el límite superior es el máximo

    return upper_bound_outlier_abs, mean_without_outliers_abs, df_salidas_para_outliers


def display_outliers_table(selected_item: str, df_salidas_para_outliers: pd.DataFrame, upper_bound_outlier_abs: float):
    """
    Muestra el título, la tabla de outliers (si existen), el límite superior
    y la explicación de la fórmula en Streamlit.
    """
    st.subheader("Outliers Detectados (Salidas/Consumos Inusualmente Altos):") # Título de la tabla de outliers
    
    if not df_salidas_para_outliers.empty:
        # Re-filtra las salidas para los outliers usando el límite ya calculado
        df_outliers_superiores_salidas = df_salidas_para_outliers[
            df_salidas_para_outliers['Movimientos'].abs() > upper_bound_outlier_abs
        ].copy()

        if not df_outliers_superiores_salidas.empty:
            st.dataframe(
                df_outliers_superiores_salidas[['Item', 'Fecha', 'Movimientos']]
                .rename(columns={'Movimientos': 'Outlier'}) # Renombra la columna para la salida
                .sort_values(by='Fecha')
                .set_index('Fecha')
            )
        else:
            st.info(f"No se detectaron outliers superiores (salidas/consumos inusualmente altos) para el Ítem: **{selected_item}** en el período de visualización.")
        
        # Esta sección (límite y fórmula) se muestra si hay datos de salida
        # para calcular outliers, independientemente de si se encontraron outliers específicos.
        st.write(f"El **Límite Superior** para identificar outliers de salidas para este ítem es: **{upper_bound_outlier_abs:.2f}** unidades (en valor absoluto).")
        st.markdown(r"""
        ### Fórmula Utilizada (Método IQR):
        Un movimiento de salida (consumo) se considera un **outlier superior** si su **valor absoluto** es mayor que:
        $$ \text{Límite Superior Outlier} = Q3 + 1.5 \times IQR $$
        Donde:
        * $Q3$: Es el tercer cuartil (percentil 75) del valor absoluto de las salidas.
        * $IQR$: Es el Rango Intercuartílico, calculado como la diferencia entre el tercer cuartil ($Q3$) y el primer cuartil ($Q1$) del valor absoluto de las salidas ($IQR = Q3 - Q1$).
        """)
    else: # Este else corresponde al 'if not df_salidas_para_outliers.empty:' principal
        st.info(f"No hay movimientos de salida para el Ítem: **{selected_item}** en el período de visualización para analizar outliers.")
