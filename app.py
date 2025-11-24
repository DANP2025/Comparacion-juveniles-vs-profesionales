import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import time # Importamos la librería time para simular la actualización

# --- CONSTANTES Y CONFIGURACIÓN INICIAL ---
# Nombre del archivo Excel del usuario. Debe estar en la misma carpeta que app.py
ARCHIVO_DATOS = "para ID.xlsx" 

# Nombres de las columnas, asumiendo que existen estos nombres en tu archivo Excel
# ¡AJUSTA ESTAS CONSTANTES SI LOS NOMBRES DE COLUMNA EN TU EXCEL SON DIFERENTES!
COL_JUGADOR = 'JUGADOR'
COL_CATEGORIA = 'CATEGORÍA'
COL_RM_SENTADILLA = 'RM SENTADILLA'
COL_VO2_MAX = 'VO2 MAX'

# Columnas sobre las que se calculará el Z-Score
COLS_ZSCORE = [COL_RM_SENTADILLA, COL_VO2_MAX]

# Jugadores específicos que se quieren comparar
JUGADORES_COMPARAR_DEFAULT = ['CALAGUA', 'OJEDA', 'ZEGARRA']
# Categorías de referencia sobre las que se calcula el Z-Score
CATEGORIAS_REFERENCIA = ['1 EQUIPO', 'SUB 17']

# Configuración de página para ancho completo y título, optimizado para web.
st.set_page_config(layout="wide", page_title="Análisis Comparativo de Z-Scores")

# Esquema de color para las categorías (ahora llamadas 'Categoría de Referencia')
COLOR_SCHEME = alt.Scale(
    domain=CATEGORIAS_REFERENCIA, 
    range=['#1f77b4', '#ff7f0e'] # Azul para 1 EQUIPO, Naranja para SUB 17
)

# --- FUNCIÓN DE CARGA DE DATOS (SIN CACHÉ PARA ACTUALIZACIÓN) ---
# Se elimina @st.cache_data para forzar la lectura del archivo en cada ejecución/interacción.
def load_data(file_path):
    """Carga y limpia el archivo Excel."""
    try:
        # Se agrega un pequeño retraso para asegurar que el sistema de archivos haya liberado el Excel si acaba de ser guardado
        time.sleep(0.5) 
        
        df = pd.read_excel(file_path, engine='openpyxl')

        # Convertir a cadena y limpiar posibles espacios
        df[COL_JUGADOR] = df[COL_JUGADOR].astype(str).str.strip()
        df[COL_CATEGORIA] = df[COL_CATEGORIA].astype(str).str.strip()
        
        # Eliminar filas donde al menos una de las columnas clave esté vacía
        df.dropna(subset=[COL_JUGADOR, COL_CATEGORIA] + COLS_ZSCORE, inplace=True)

        return df
    except FileNotFoundError:
        st.error(f"Error: No se encontró el archivo '{file_path}'. Asegúrate de que está en la misma carpeta que 'app.py'.")
        return pd.DataFrame()
    except KeyError as e:
        st.error(f"Error: La columna {e} no se encuentra en el archivo Excel. Verifica los nombres de columna en las constantes de 'app.py'.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Ocurrió un error al cargar los datos: {e}")
        return pd.DataFrame()

# --- FUNCIÓN DE CÁLCULO DE DOBLE Z-SCORE ---
def calculate_dual_zscore(df, target_players, reference_categories, value_cols):
    """
    Calcula el Z-Score de los jugadores objetivo contra las estadísticas (media/std)
    de cada una de las categorías de referencia.
    """
    
    # 1. Filtrar solo los jugadores objetivo (CALAGUA, OJEDA, ZEGARRA)
    df_targets = df[df[COL_JUGADOR].isin(target_players)].copy()
    
    # Lista para almacenar los resultados de cada comparación
    all_comparisons = []

    for ref_cat in reference_categories:
        # 2. Obtener la población de referencia para la categoría actual
        df_reference = df[df[COL_CATEGORIA] == ref_cat]
        
        if df_reference.empty:
            continue

        # 3. Calcular la media y desviación estándar (STD) para la categoría de referencia
        stats = df_reference[value_cols].agg(['mean', 'std']).T
        stats.columns = ['mean', 'std']
        
        # 4. Calcular el Z-Score de los jugadores objetivo contra estas estadísticas
        df_cat_zscore = df_targets.copy()
        
        for col in value_cols:
            mean = stats.loc[col, 'mean']
            std = stats.loc[col, 'std']
            
            new_col_name = f'Z-Score {col}'
            
            # Cálculo de Z-Score: (Valor - Media) / Desviación Estándar
            if std == 0 or np.isnan(std):
                # Si la desviación es cero (todos los valores son iguales), el Z-Score es 0
                df_cat_zscore[new_col_name] = 0
            else:
                df_cat_zscore[new_col_name] = (df_cat_zscore[col] - mean) / std
        
        # 5. Agregar una columna que indica la categoría de referencia utilizada
        df_cat_zscore['Categoría de Referencia'] = ref_cat
        all_comparisons.append(df_cat_zscore)

    if not all_comparisons:
        return pd.DataFrame()

    # 6. Combinar todos los resultados en un solo DataFrame
    df_final = pd.concat(all_comparisons, ignore_index=True)
    
    # Limpiar columnas originales de valor para evitar confusiones
    cols_to_drop = [col for col in value_cols if col in df_final.columns]
    return df_final.drop(columns=cols_to_drop, errors='ignore')

# --- LÓGICA PRINCIPAL DE STREAMLIT ---
def main():
    st.title("📊 Análisis de Impacto: Comparativa de Z-Scores (Doble Referencia)")
    st.markdown("""
        Utiliza los filtros de la izquierda para analizar el rendimiento de los jugadores.
        
        **Interpretación Clave:** Cada barra muestra el rendimiento del jugador comparado con el promedio (Z=0) de la **Categoría de Referencia** seleccionada.
        * **Azul (`1 EQUIPO`):** Zscore del jugador en el 1 equipo
        * **Naranja (`SUB 17`):** Zscore del jugador en su categoría
    """)
    
    # --- BOTÓN DE RECARGA (Nuevo) ---
    col_button, col_spacer = st.columns([1, 4])
    with col_button:
        # Al presionar el botón, se fuerza una nueva ejecución del script
        if st.button("🔄 Actualizar Datos del Excel", help="Haz clic para recargar la información directamente desde 'para ID.xlsx'."):
            st.rerun() # Comando para forzar la reejecución del script
    
    with col_spacer:
        st.info("Presiona el botón de **Actualizar** si has modificado y guardado el archivo Excel.")

    # 1. Cargar datos
    # Como load_data no tiene caché, se ejecuta en cada interacción o al hacer clic en 'Actualizar'
    data = load_data(ARCHIVO_DATOS)

    if data.empty:
        return

    # --- FILTRO DINÁMICO INTERACTIVO (Sidebar) ---
    all_players = sorted(data[COL_JUGADOR].unique().tolist())
    all_metrics = [COL_RM_SENTADILLA, COL_VO2_MAX]
    
    # Filtrar jugadores solo de la lista inicial
    target_players_filtered = [p for p in JUGADORES_COMPARAR_DEFAULT if p in all_players]

    st.sidebar.header("Filtros Interactivos")
    
    # 1. Filtro dinámico de JUGADORES
    selected_players = st.sidebar.multiselect(
        "1. Jugadores a Graficar:",
        options=target_players_filtered,
        default=target_players_filtered,
        help="Selecciona los jugadores (CALAGUA, OJEDA, ZEGARRA)."
    )
    
    # 2. Filtro dinámico de CATEGORÍA DE REFERENCIA
    selected_references = st.sidebar.multiselect(
        "2. Categoría(s) de Referencia:",
        options=CATEGORIAS_REFERENCIA,
        default=CATEGORIAS_REFERENCIA,
        help="Define contra qué grupo se calcula el promedio (Z-Score)."
    )

    # 3. Filtro dinámico de MÉTRICAS
    selected_metrics = st.sidebar.multiselect(
        "3. Métrica(s) a Visualizar:",
        options=all_metrics,
        default=all_metrics,
        help="Permite enfocarse en una o dos variables."
    )

    if not selected_players or not selected_references or not selected_metrics:
        st.info("Por favor, completa la selección de jugadores, referencias y métricas.")
        return

    # 2. Calcular los Z-Scores con la lógica dual
    df_dual_zscore = calculate_dual_zscore(
        data, 
        selected_players, 
        selected_references, 
        all_metrics # Se usan todas las métricas para el cálculo, luego filtramos para la visualización
    )

    if df_dual_zscore.empty:
        st.warning("No hay datos disponibles para la combinación de jugadores y categorías de referencia seleccionadas.")
        return

    # 3. Preparar datos para el gráfico
    
    # Lista de columnas Z-Score para las métricas seleccionadas
    zscore_cols_to_melt = [f'Z-Score {col}' for col in selected_metrics]

    # Unpivot para tener las métricas en una sola columna
    df_chart = df_dual_zscore.melt(
        id_vars=[COL_JUGADOR, 'Categoría de Referencia'],
        value_vars=zscore_cols_to_melt,
        var_name='Métrica',
        value_name='Z_Score'
    )
    
    # Limpiar nombres de las métricas para el gráfico
    df_chart['Métrica'] = df_chart['Métrica'].str.replace('Z-Score ', '')
    df_chart = df_chart.rename(columns={'Categoría de Referencia': 'Referencia'})

    # --- FUNCIÓN DE GENERACIÓN DE GRÁFICOS (Modularizada) ---

    def create_comparison_chart(data, metric_name=None):
        
        if metric_name:
            chart_data = data[data['Métrica'] == metric_name].copy()
            chart_title = f"Z-Score Comparativo: {metric_name}"
        else:
            chart_data = data.copy()
            chart_title = "Z-Score Agrupado por Jugador y Métrica"

        # 1. Gráfico de Barras
        chart_bars = alt.Chart(chart_data).mark_bar().encode(
            # Eje X: Jugador (se usa como el grupo principal de barras)
            x=alt.X(COL_JUGADOR, title='Jugador'),
            
            # Desplazamiento X: REFERENCIA (coloca barras una al lado de la otra)
            xOffset=alt.XOffset('Referencia', title='Referencia'),
            
            # Eje Y: Z-Score (Puntuación Z)
            y=alt.Y('Z_Score', title='Puntuación Z (Z-Score)', scale=alt.Scale(domain=[-3, 3])),
            
            # Color: REFERENCIA
            color=alt.Color('Referencia', title='Referencia', scale=COLOR_SCHEME),
            
            tooltip=[COL_JUGADOR, 'Referencia', 'Métrica', alt.Tooltip('Z_Score', format=".3f")]
        ).properties(
            title=chart_title,
            # Ajustar tamaño de las barras para el agrupamiento
            width=alt.Step(90) 
        ) 

        # 2. Línea Cero (Media)
        zero_line = alt.Chart(pd.DataFrame({'Z_Score': [0]})).mark_rule(color='red', strokeDash=[5,5]).encode(
            y='Z_Score'
        )

        # 3. Etiquetas de Texto (Valor del Z-Score)
        # Usamos text para visualizar el valor exacto
        text_labels = alt.Chart(chart_data).mark_text(
            align='center',
            baseline='middle',
            dy=alt.expr("datum.Z_Score < 0 ? 15 : -10"), # Mover etiqueta arriba o abajo de la barra
            color='black',
            fontSize=11,
            fontWeight='bold'
        ).encode(
            x=alt.X(COL_JUGADOR),
            xOffset=alt.XOffset('Referencia'),
            y='Z_Score',
            text=alt.Text('Z_Score', format=".3f"), # Formato a 3 decimales
            opacity=alt.condition(alt.datum.Z_Score != 0, alt.value(1), alt.value(0)) # Ocultar si es 0
        )
        
        # 4. Combinar (Layer) todo
        final_chart = (chart_bars + zero_line + text_labels).interactive()
        
        return final_chart
    
    # --- CONSTRUCCIÓN FINAL ---

    charts = []
    
    if len(selected_metrics) == 1:
        # Si solo se selecciona una métrica, la mostramos en un gráfico grande
        chart = create_comparison_chart(df_chart, selected_metrics[0])
        charts.append(chart)
    else:
        # Si se seleccionan dos métricas, usamos Faceting/Concatenación para separarlas visualmente
        for metric in selected_metrics:
            charts.append(create_comparison_chart(df_chart, metric))

    if charts:
        # Concatenar todos los gráficos verticalmente
        final_visualization = alt.vconcat(*charts).resolve_scale(
            x='independent', # Mantenemos ejes X independientes si son métricas diferentes
            y='shared' # Mantenemos la escala Y compartida para comparación visual
        ).configure_legend(
            orient="top", titleOrient="left"
        )
        
        st.altair_chart(final_visualization, use_container_width=True)
    
    # Nota de ayuda para la interpretación
    st.markdown("""
        ---
        **Nota:** La línea roja discontinua representa la media ($Z=0$). Los valores exactos de Z-Score se muestran sobre o bajo cada barra para una lectura precisa.
    """)


if __name__ == "__main__":
    main()
