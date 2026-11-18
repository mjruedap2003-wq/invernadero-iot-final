import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Configuración de página
st.set_page_config(
    page_title="Greenhouse IoT | Analítica Climática",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Estilos CSS personalizados (Estética Agritech Dark / Emerald)
st.markdown("""
<style>
    /* Fondo general y tipografía */
    .stApp {
        background-color: #0b1310;
        color: #e6f0ec;
    }
    /* Banner superior */
    .hero-banner {
        background: linear-gradient(135deg, #0f2920 0%, #163d2f 55%, #0d221b 100%);
        border: 1px solid #245c47;
        border-radius: 16px;
        padding: 26px 32px;
        margin-bottom: 24px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
    }
    .hero-badge {
        display: inline-block;
        background-color: rgba(46, 204, 113, 0.16);
        color: #2ecc71;
        border: 1px solid rgba(46, 204, 113, 0.4);
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.6px;
        margin-bottom: 10px;
    }
    .hero-title {
        font-size: 2rem;
        font-weight: 800;
        color: #ffffff;
        margin: 0 0 6px 0;
    }
    .hero-subtitle {
        font-size: 1rem;
        color: #a9c7bc;
        margin: 0;
    }
    /* Tarjetas KPI */
    .kpi-card {
        background: #111d18;
        border: 1px solid #1f3b30;
        border-left: 4px solid #2ecc71;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
    }
    .kpi-card.temp { border-left-color: #ff6b6b; }
    .kpi-card.hum  { border-left-color: #4dabf7; }
    .kpi-card.vent { border-left-color: #feca57; }
    .kpi-label {
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: #8fb3a5;
        margin-bottom: 6px;
    }
    .kpi-value {
        font-size: 1.85rem;
        font-weight: 700;
        color: #ffffff;
        line-height: 1.15;
    }
    .kpi-sub {
        font-size: 0.82rem;
        color: #7ea194;
        margin-top: 6px;
    }
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0e1814;
        border-right: 1px solid #1d352c;
    }
    /* Caja de subida */
    div[data-testid="stFileUploader"] {
        background-color: #111d18;
        border: 1px dashed #2e6f56;
        border-radius: 12px;
        padding: 12px;
    }
</style>
""", unsafe_allow_html=True)

# 3. Encabezado principal
st.markdown("""
<div class="hero-banner">
    <div class="hero-badge">SISTEMA DE TELEMETRÍA & TELECONTROL IOT</div>
    <div class="hero-title">🌱 Invernadero Hidropónico Inteligente</div>
    <p class="hero-subtitle">
        Panel de analítica histórica, evaluación de rangos óptimos de cultivo, diagnóstico de alertas y correlación climática.
    </p>
</div>
""", unsafe_allow_html=True)

# 4. Barra lateral de control
with st.sidebar:
    st.markdown("### ⚙️ Parámetros de Cultivo")
    st.caption("Ajusta los umbrales ideales para recalcular las alertas en tiempo real.")
    temp_min, temp_max = st.slider(
        "🌡️ Temperatura Óptima (°C)", 10.0, 40.0, (18.0, 28.0), step=0.5
    )
    hum_min, hum_max = st.slider(
        "💧 Humedad Relativa Óptima (%)", 20.0, 95.0, (50.0, 75.0), step=1.0
    )
    st.divider()
    st.markdown("### 📡 Arquitectura")
    st.markdown(
        "- **Nodo:** ESP32 + DHT22 + Servo SG90\n"
        "- **Broker:** ThingsBoard Cloud (MQTT)\n"
        "- **TSDB:** InfluxDB Cloud\n"
        "- **Visualización:** Grafana Cloud"
    )

# 5. Funciones de carga y limpieza inteligente del CSV de Grafana/InfluxDB
def generar_datos_demo():
    rng = pd.date_range(end=pd.Timestamp.now(), periods=60, freq="1min")
    np.random.seed(42)
    temp = np.clip(23 + np.cumsum(np.random.normal(0.05, 0.9, 60)), 15.5, 33.5)
    hum = np.clip(64 - (temp - 23) * 2.1 + np.random.normal(0, 2.5, 60), 38, 88)
    vent = np.where((temp > 27.5) | (hum > 76), 1, 0)
    return pd.DataFrame({
        "timestamp": rng,
        "temperatura": np.round(temp, 1),
        "humedad": np.round(hum, 1),
        "ventilacion": vent
    })

def procesar_csv(file):
    raw_lines = file.getvalue().decode("utf-8", errors="ignore").splitlines()
    skip = 0
    for i, line in enumerate(raw_lines):
        low = line.lower()
        if ("temperatura" in low and "humedad" in low) or ("_field" in low and "_value" in low):
            skip = i
            break
    file.seek(0)
    df = pd.read_csv(file, skiprows=skip)
    df.columns = [c.strip().lower() for c in df.columns]

    # Caso A: CSV exportado desde Grafana Explore sin pivot (_field, _value)
    if "_field" in df.columns and "_value" in df.columns:
        col_t = next((c for c in df.columns if "time" in c), None)
        df[col_t] = pd.to_datetime(df[col_t], errors="coerce")
        df["_value"] = pd.to_numeric(df["_value"], errors="coerce")
        df = df.dropna(subset=[col_t, "_value"])
        df["time_round"] = df[col_t].dt.round("1s")
        df = df.pivot_table(index="time_round", columns="_field", values="_value", aggfunc="mean").reset_index()
        df = df.rename(columns={"time_round": "timestamp"})
    else:
        # Caso B: CSV con columnas separadas (temperatura, humedad, ventilacion)
        col_t = next((c for c in df.columns if "time" in c or "fecha" in c), None)
        if col_t:
            df[col_t] = pd.to_datetime(df[col_t], errors="coerce")
            df = df.dropna(subset=[col_t]).sort_values(col_t).rename(columns={col_t: "timestamp"})

    for col in ["temperatura", "humedad", "ventilacion"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "temperatura" in df.columns and "humedad" in df.columns:
        df = df.dropna(subset=["temperatura", "humedad"]).sort_values("timestamp")
    return df

# 6. Zona de carga de archivo
col_up, col_demo = st.columns([3, 1])
with col_up:
    archivo = st.file_uploader("📂 Carga aquí el archivo CSV exportado desde Grafana Cloud", type=["csv"])
with col_demo:
    st.markdown("<br>", unsafe_allow_html=True)
    usar_demo = st.button("✨ Probar con datos demo", use_container_width=True)

if archivo is not None:
    df = procesar_csv(archivo)
    origen = f"Archivo cargado: `{archivo.name}`"
elif usar_demo:
    df = generar_datos_demo()
    origen = "Modo demostración interactiva (simulación de lote)"
else:
    st.info("👆 Sube tu archivo **.csv** exportado desde Grafana o presiona **✨ Probar con datos demo** para explorar el panel.")
    st.stop()

if df.empty or "temperatura" not in df.columns or "humedad" not in df.columns:
    st.error("El archivo no contiene columnas reconocibles de `temperatura` y `humedad`. Verifica que el CSV provenga de la medición `clima_invernadero`.")
    st.stop()

st.caption(f"🟢 {origen} · **{len(df)}** registros procesados")

# 7. Clasificación operativa
cond_temp = (df["temperatura"] < temp_min) | (df["temperatura"] > temp_max)
cond_hum = (df["humedad"] < hum_min) | (df["humedad"] > hum_max)
df["estado"] = np.where(
    cond_temp & cond_hum, "Crítico (Temp + Hum)",
    np.where(cond_temp, "Alerta Temperatura",
             np.where(cond_hum, "Alerta Humedad", "Óptimo"))
)

# 8. Tarjetas KPI superiores
t_mean, t_min_v, t_max_v = df["temperatura"].mean(), df["temperatura"].min(), df["temperatura"].max()
h_mean, h_min_v, h_max_v = df["humedad"].mean(), df["humedad"].min(), df["humedad"].max()
pct_opt = (df["estado"] == "Óptimo").mean() * 100
pct_vent = (df["ventilacion"] > 0).mean() * 100 if "ventilacion" in df.columns else 0.0

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""
    <div class="kpi-card temp">
        <div class="kpi-label">🌡️ Temperatura Media</div>
        <div class="kpi-value">{t_mean:.1f} °C</div>
        <div class="kpi-sub">Mín {t_min_v:.1f} °C · Máx {t_max_v:.1f} °C</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div class="kpi-card hum">
        <div class="kpi-label">💧 Humedad Media</div>
        <div class="kpi-value">{h_mean:.1f} %</div>
        <div class="kpi-sub">Mín {h_min_v:.1f} % · Máx {h_max_v:.1f} %</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">✅ Confort del Cultivo</div>
        <div class="kpi-value">{pct_opt:.1f} %</div>
        <div class="kpi-sub">{(df['estado'] == 'Óptimo').sum()} de {len(df)} lecturas en rango</div>
    </div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""
    <div class="kpi-card vent">
        <div class="kpi-label">🌀 Ventilación Activa</div>
        <div class="kpi-value">{pct_vent:.1f} %</div>
        <div class="kpi-sub">Compuerta servo abierta (90°)</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Estilo oscuro para gráficos Matplotlib
plt.rcParams.update({
    "figure.facecolor": "#111d18",
    "axes.facecolor": "#111d18",
    "axes.edgecolor": "#26473a",
    "axes.labelcolor": "#cde3da",
    "xtick.color": "#8fb3a5",
    "ytick.color": "#8fb3a5",
    "text.color": "#e6f0ec",
    "grid.color": "#1d382d",
    "grid.linestyle": "--",
    "grid.alpha": 0.6
})

# 9. Pestañas de análisis
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Evolución & Umbrales",
    "🚨 Alertas Operativas",
    "🔗 Correlación Climática",
    "🗂️ Tabla de Registros"
])

with tab1:
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6.4), sharex=True)
    eje_x = df["timestamp"] if "timestamp" in df.columns else df.index

    # Temperatura
    ax1.plot(eje_x, df["temperatura"], color="#ff6b6b", linewidth=2.2, label="Temperatura (°C)")
    ax1.fill_between(eje_x, df["temperatura"], df["temperatura"].min() - 1, color="#ff6b6b", alpha=0.10)
    ax1.axhspan(temp_min, temp_max, color="#2ecc71", alpha=0.14, label=f"Zona Óptima ({temp_min}–{temp_max} °C)")
    ax1.set_ylabel("Temperatura (°C)", fontweight="bold")
    ax1.set_title("Comportamiento Térmico y Banda Ideal", loc="left", fontsize=11, fontweight="bold", pad=10)
    ax1.legend(loc="upper right", frameon=True, facecolor="#0e1814", edgecolor="#26473a")
    ax1.grid(True)

    # Humedad
    ax2.plot(eje_x, df["humedad"], color="#4dabf7", linewidth=2.2, label="Humedad Relativa (%)")
    ax2.fill_between(eje_x, df["humedad"], df["humedad"].min() - 2, color="#4dabf7", alpha=0.10)
    ax2.axhspan(hum_min, hum_max, color="#2ecc71", alpha=0.14, label=f"Zona Óptima ({hum_min}–{hum_max} %)")
    ax2.set_ylabel("Humedad (%)", fontweight="bold")
    ax2.set_xlabel("Marca de Tiempo (UTC)", fontweight="bold")
    ax2.set_title("Comportamiento Hídrico y Banda Ideal", loc="left", fontsize=11, fontweight="bold", pad=10)
    ax2.legend(loc="upper right", frameon=True, facecolor="#0e1814", edgecolor="#26473a")
    ax2.grid(True)

    plt.tight_layout()
    st.pyplot(fig)

with tab2:
    c_izq, c_der = st.columns([1, 1.4])
    with c_izq:
        st.markdown("#### Distribución de Estados")
        resumen = df["estado"].value_counts().reset_index()
        resumen.columns = ["Diagnóstico", "Cantidad"]
        resumen["Porcentaje (%)"] = (resumen["Cantidad"] / len(df) * 100).round(1)
        st.dataframe(resumen, use_container_width=True, hide_index=True)

        fig_bar, ax_b = plt.subplots(figsize=(5.5, 3.6))
        paleta = {
            "Óptimo": "#2ecc71",
            "Alerta Temperatura": "#ff6b6b",
            "Alerta Humedad": "#4dabf7",
            "Crítico (Temp + Hum)": "#feca57"
        }
        colores = [paleta.get(x, "#95a5a6") for x in resumen["Diagnóstico"]]
        ax_b.barh(resumen["Diagnóstico"], resumen["Cantidad"], color=colores, height=0.55)
        ax_b.set_xlabel("Número de Registros")
        ax_b.grid(True, axis="x")
        plt.tight_layout()
        st.pyplot(fig_bar)

    with c_der:
        st.markdown("#### Eventos Fuera de Rango Detectados")
        anomalias = df[df["estado"] != "Óptimo"]
        if anomalias.empty:
            st.success("🎉 ¡Excelente! Todas las lecturas registradas se mantuvieron dentro de los rangos ideales del invernadero.")
        else:
            st.warning(f"⚠️ Se identificaron **{len(anomalias)}** mediciones que superaron los límites establecidos.")
            cols_ver = [c for c in ["timestamp", "temperatura", "humedad", "ventilacion", "estado"] if c in anomalias.columns]
            st.dataframe(anomalias[cols_ver].tail(15), use_container_width=True, hide_index=True)

with tab3:
    corr_val = df["temperatura"].corr(df["humedad"])
    c_m1, c_m2 = st.columns([1.4, 1])
    with c_m1:
        fig_sc, ax_s = plt.subplots(figsize=(7, 4.6))
        paleta_sc = {
            "Óptimo": "#2ecc71",
            "Alerta Temperatura": "#ff6b6b",
            "Alerta Humedad": "#4dabf7",
            "Crítico (Temp + Hum)": "#feca57"
        }
        sns.scatterplot(
            data=df, x="temperatura", y="humedad",
            hue="estado", palette=paleta_sc, s=75, edgecolor="#0b1310", linewidth=0.6, ax=ax_s
        )
        ax_s.axvspan(temp_min, temp_max, color="#2ecc71", alpha=0.07)
        ax_s.axhspan(hum_min, hum_max, color="#2ecc71", alpha=0.07)
        ax_s.set_xlabel("Temperatura Ambiental (°C)", fontweight="bold")
        ax_s.set_ylabel("Humedad Relativa (%)", fontweight="bold")
        ax_s.set_title("Mapa de Dispersión Temperatura vs. Humedad", loc="left", fontweight="bold")
        ax_s.legend(title="Estado", facecolor="#0e1814", edgecolor="#26473a")
        ax_s.grid(True)
        plt.tight_layout()
        st.pyplot(fig_sc)

    with c_m2:
        st.markdown("#### Interpretación Física")
        st.metric("Coeficiente de Pearson (r)", f"{corr_val:.3f}")
        if corr_val < -0.4:
            st.info("📉 **Correlación inversa moderada/fuerte:** Al aumentar la temperatura dentro del invernadero, la humedad relativa tiende a descender (comportamiento psicrométrico esperado).")
        elif corr_val > 0.4:
            st.info("📈 **Correlación directa:** Ambas variables aumentaron o disminuyeron simultáneamente durante el periodo registrado.")
        else:
            st.info("⚖️ **Correlación débil/independiente:** Las variaciones de temperatura y humedad operaron de forma desacoplada o regulada por la ventilación.")

        st.markdown("#### Estadística Descriptiva")
        cols_num = [c for c in ["temperatura", "humedad", "ventilacion"] if c in df.columns]
        st.dataframe(df[cols_num].describe().round(2), use_container_width=True)

with tab4:
    st.markdown("#### Historial Completo Procesado")
    st.dataframe(df, use_container_width=True, hide_index=True)
    csv_limpio = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Descargar dataset procesado (.csv)",
        data=csv_limpio,
        file_name="invernadero_analizado.csv",
        mime="text/csv"
    )
