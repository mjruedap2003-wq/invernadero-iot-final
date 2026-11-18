import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(
    page_title="Invernadero Hidropónico IoT - Análisis",
    page_icon="🌱",
    layout="wide"
)

st.title("🌱 Monitor Analítico — Invernadero Hidropónico Automatizado")
st.markdown(
    "Análisis operativo de telemetría (**Temperatura** y **Humedad Relativa**) y telecontrol "
    "(**Compuerta de Ventilación**) exportado desde **Grafana / InfluxDB**."
)

# Sidebar con parámetros operativos reales del invernadero
st.sidebar.header("⚙️ Rangos Óptimos de Operación")
temp_min, temp_max = st.sidebar.slider(
    "Rango óptimo de Temperatura (°C)", 10.0, 40.0, (18.0, 28.0), step=0.5
)
hum_min, hum_max = st.sidebar.slider(
    "Rango óptimo de Humedad Relativa (%)", 20.0, 95.0, (50.0, 75.0), step=1.0
)

archivo = st.file_uploader("📂 Sube el archivo CSV exportado de Grafana", type=["csv"])

def limpiar_csv_grafana(file):
    # Lee saltando líneas de anotación si vienen en formato Flux/InfluxDB
    raw_lines = file.getvalue().decode("utf-8", errors="ignore").splitlines()
    skip = 0
    for i, line in enumerate(raw_lines):
        if "temperatura" in line.lower() and "humedad" in line.lower():
            skip = i
            break
    file.seek(0)
    df = pd.read_csv(file, skiprows=skip)
    df.columns = [c.strip().lower() for c in df.columns]

    # Detectar columna de tiempo
    col_tiempo = next((c for c in df.columns if "time" in c or "fecha" in c), None)
    if col_tiempo:
        df[col_tiempo] = pd.to_datetime(df[col_tiempo], errors="coerce")
        df = df.dropna(subset=[col_tiempo]).sort_values(col_tiempo)
        df = df.rename(columns={col_tiempo: "timestamp"})

    for col in ["temperatura", "humedad", "ventilacion"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["temperatura", "humedad"])
    return df

if archivo is not None:
    df = limpiar_csv_grafana(archivo)

    if df.empty:
        st.error("No se encontraron registros válidos con columnas 'temperatura' y 'humedad'.")
        st.stop()

    # Clasificación de alertas operativas por umbral
    cond_temp = (df["temperatura"] < temp_min) | (df["temperatura"] > temp_max)
    cond_hum = (df["humedad"] < hum_min) | (df["humedad"] > hum_max)
    df["alerta_operativa"] = np.where(
        cond_temp & cond_hum, "Alerta Crítica (Temp + Hum)",
        np.where(cond_temp, "Alerta Temperatura (°C)",
                 np.where(cond_hum, "Alerta Humedad (%)", "Óptimo"))
    )

    # 1. KPIs Principales
    st.subheader("📊 Resumen Estadístico del Lote")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Temperatura Media", f"{df['temperatura'].mean():.1f} °C",
              f"Mín: {df['temperatura'].min():.1f} | Máx: {df['temperatura'].max():.1f}")
    k2.metric("Humedad Media", f"{df['humedad'].mean():.1f} %",
              f"Mín: {df['humedad'].min():.1f} | Máx: {df['humedad'].max():.1f}")
    pct_optimo = (df["alerta_operativa"] == "Óptimo").mean() * 100
    k3.metric("Tiempo en Rango Óptimo", f"{pct_optimo:.1f} %",
              f"{len(df)} lecturas totales")
    if "ventilacion" in df.columns:
        pct_vent = (df["ventilacion"] > 0).mean() * 100
        k4.metric("Ventilación Activa (ON)", f"{pct_vent:.1f} %", "Compuerta a 90°")
    else:
        k4.metric("Alertas Totales", f"{(df['alerta_operativa'] != 'Óptimo').sum()}")

    # 2. Evolución Temporal con Bandas de Umbral
    st.subheader("📈 Evolución Temporal y Umbrales del Invernadero")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    eje_x = df["timestamp"] if "timestamp" in df.columns else df.index

    ax1.plot(eje_x, df["temperatura"], color="#e74c3c", linewidth=1.8, label="Temperatura (°C)")
    ax1.axhspan(temp_min, temp_max, color="#2ecc71", alpha=0.15, label=f"Óptimo ({temp_min}-{temp_max} °C)")
    ax1.set_ylabel("Temperatura (°C)")
    ax1.legend(loc="upper right")
    ax1.grid(True, alpha=0.3)

    ax2.plot(eje_x, df["humedad"], color="#3498db", linewidth=1.8, label="Humedad (%)")
    ax2.axhspan(hum_min, hum_max, color="#2ecc71", alpha=0.15, label=f"Óptimo ({hum_min}-{hum_max} %)")
    ax2.set_ylabel("Humedad (%)")
    ax2.set_xlabel("Marca de Tiempo")
    ax2.legend(loc="upper right")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    st.pyplot(fig)

    # 3. Alertas por Umbral y Correlación
    col_izq, col_der = st.columns(2)

    with col_izq:
        st.subheader("🚨 Diagnóstico de Alertas por Umbral")
        conteo_alertas = df["alerta_operativa"].value_counts().reset_index()
        conteo_alertas.columns = ["Estado Operativo", "Registros"]
        st.dataframe(conteo_alertas, use_container_width=True, hide_index=True)

        fuera_rango = df[df["alerta_operativa"] != "Óptimo"]
        if not fuera_rango.empty:
            st.warning(f"Se detectaron **{len(fuera_rango)}** registros fuera de los umbrales configurados.")
            st.dataframe(fuera_rango.tail(10), use_container_width=True)
        else:
            st.success("Todas las lecturas se mantuvieron dentro de los rangos ideales.")

    with col_der:
        st.subheader("🔗 Correlación Temperatura vs. Humedad")
        corr = df["temperatura"].corr(df["humedad"])
        st.info(f"Coeficiente de correlación de Pearson ($r$): **{corr:.3f}**")
        fig2, ax = plt.subplots(figsize=(6, 4.2))
        sns.scatterplot(
            data=df, x="temperatura", y="humedad",
            hue="alerta_operativa", palette="Set1", ax=ax, s=60
        )
        ax.axvline(temp_min, color="gray", linestyle="--", alpha=0.6)
        ax.axvline(temp_max, color="gray", linestyle="--", alpha=0.6)
        ax.axhline(hum_min, color="gray", linestyle=":", alpha=0.6)
        ax.axhline(hum_max, color="gray", linestyle=":", alpha=0.6)
        ax.set_xlabel("Temperatura (°C)")
        ax.set_ylabel("Humedad Relativa (%)")
        ax.grid(True, alpha=0.3)
        st.pyplot(fig2)

else:
    st.info("👆 Sube el archivo CSV exportado desde tu panel de Grafana para iniciar el análisis.")
