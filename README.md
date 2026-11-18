# invernadero-iot-final
<div align="center">

# 🌱 Invernadero Hidropónico Automatizado IoT
**Sistema integral de telemetría ambiental, telecontrol remoto, almacenamiento de series temporales y analítica en la nube.**

![ESP32](https://img.shields.io/badge/Hardware-ESP32-E7352C?style=for-the-badge&logo=espressif&logoColor=white)
![MQTT](https://img.shields.io/badge/Protocol-MQTT%20%2F%20RPC-660066?style=for-the-badge&logo=eclipse-mosquitto&logoColor=white)
![InfluxDB](https://img.shields.io/badge/Database-InfluxDB%20Cloud-22ADF6?style=for-the-badge&logo=influxdb&logoColor=white)
![Grafana](https://img.shields.io/badge/Monitoring-Grafana%20Cloud-F46800?style=for-the-badge&logo=grafana&logoColor=white)
![Streamlit](https://img.shields.io/badge/Analytics-Streamlit%20Cloud-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)

🔗 **[Ver Simulación en Wokwi](https://wokwi.com/projects/480982539043131393)** · 📊 **[Abrir App Analítica en Streamlit](https://invernadero-iot-final-5c6d5p2xvnfenrrn3xtbqx.streamlit.app/)**

</div>

---

## 📋 Descripción del Proyecto

Este proyecto implementa una arquitectura **IoT de extremo a extremo (*End-to-End*)** aplicada a la agricultura de precisión en un **invernadero hidropónico**. El sistema supervisa continuamente las condiciones microclimáticas críticas del cultivo (**Temperatura** y **Humedad Relativa**) y permite accionar de forma remota una **compuerta de ventilación** mediante comandos RPC desde la nube, almacenando todo el historial para su visualización y diagnóstico estadístico.

### 🏗️ Arquitectura del Sistema

```text
┌──────────────────────┐      MQTT (Telemetría / RPC)      ┌────────────────────────┐
│   ESP32 (Wokwi)      │ ◄───────────────────────────────► │   ThingsBoard Cloud    │
│ • Sensor DHT22       │                                   │ • Dashboard en Vivo    │
│ • Servomotor (90°)   │                                   │ • Switch Telecontrol   │
│ • LCD 16x2 I2C + LED │      HTTPS / REST API (Write)     ├────────────────────────┤
└──────────────────────┘ ────────────────────────────────► │    InfluxDB Cloud      │
                                                           │ • Bucket: invernadero  │
                                                           └───────────┬────────────┘
                                                                       │ Flux / SQL
                                                                       ▼
┌──────────────────────┐       Exportación CSV             ┌────────────────────────┐
│   Streamlit Cloud    │ ◄──────────────────────────────── │     Grafana Cloud      │
│ • KPIs y Umbrales    │                                   │ • Panel Temperatura    │
│ • Alertas y Pearson  │                                   │ • Panel Humedad        │
└──────────────────────┘                                   └────────────────────────┘
