#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <ESP32Servo.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <ArduinoJson.h>
#include <InfluxDbClient.h>
#include <InfluxDbCloud.h>

// 1. Credenciales WiFi Wokwi
const char* ssid = "Wokwi-GUEST";
const char* password = "";

// 2. Configuración ThingsBoard Cloud
const char* tb_server = "mqtt.thingsboard.cloud";
const char* tb_token  = "Token secreto";
const char* topic_pub = "v1/devices/me/telemetry";
const char* topic_sub = "v1/devices/me/rpc/request/+";

// 3. Configuración InfluxDB Cloud (Usa el Organization ID de la pestaña About)
#define INFLUXDB_URL "https://us-east-1-1.aws.cloud2.influxdata.com"
#define INFLUXDB_TOKEN "Token super largo pero mega secreto"
#define INFLUXDB_ORG "Grupo_com_fisica"
#define INFLUXDB_BUCKET "invernadero"
#define TZ_INFO "UTC-5"

// Cliente oficial InfluxDB con certificado raíz de InfluxData Cloud
InfluxDBClient clientInflux(INFLUXDB_URL, INFLUXDB_ORG, INFLUXDB_BUCKET, INFLUXDB_TOKEN, InfluxDbCloud2CACert);
Point sensorPoint("clima_invernadero");

// Pines Hardware
#define DHTPIN 15
#define DHTTYPE DHT22
#define SERVOPIN 13
#define LEDPIN 12

DHT dht(DHTPIN, DHTTYPE);
Servo compuertaServo;
LiquidCrystal_I2C lcd(0x27, 16, 2);
WiFiClient espClient;
PubSubClient clientMQTT(espClient);

unsigned long lastMsg = 0;
const long intervalo = 3000;
bool ventilacionActiva = false;

void actualizarLCD(float t, float h) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("T:" + String(t, 1) + "C H:" + String(h, 0) + "%");
  lcd.setCursor(0, 1);
  lcd.print(ventilacionActiva ? "Ventilacion: ON" : "Ventilacion: OFF");
}

void callback(char* topic, byte* payload, unsigned int length) {
  String mensaje = "";
  for (unsigned int i = 0; i < length; i++) {
    mensaje += (char)payload[i];
  }
  Serial.println("RPC recibido de ThingsBoard: " + mensaje);

  StaticJsonDocument<128> doc;
  DeserializationError error = deserializeJson(doc, mensaje);

  if (!error) {
    bool estado = doc["params"];
    ventilacionActiva = estado;

    if (ventilacionActiva) {
      compuertaServo.write(90);
      digitalWrite(LEDPIN, HIGH);
    } else {
      compuertaServo.write(0);
      digitalWrite(LEDPIN, LOW);
    }

    clientMQTT.publish(topic_pub, ventilacionActiva ? "{\"ventilacion\":true}" : "{\"ventilacion\":false}");
  }
}

void reconnectMQTT() {
  while (!clientMQTT.connected()) {
    String clientId = "ESP32-TB-" + String(esp_random(), HEX);
    if (clientMQTT.connect(clientId.c_str(), tb_token, NULL)) {
      Serial.println("Conectado a ThingsBoard Cloud!");
      clientMQTT.subscribe(topic_sub);
    } else {
      Serial.print("Fallo conexion TB rc=");
      Serial.println(clientMQTT.state());
      delay(2000);
    }
  }
}

void setup() {
  Serial.begin(115200);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
  }
  Serial.println("\nWiFi OK! IP: " + WiFi.localIP().toString());

  // Sincronizar reloj (necesario para certificados SSL de InfluxDB)
  timeSync(TZ_INFO, "pool.ntp.org", "time.nis.gov");

  // Validar conexión y credenciales de InfluxDB al arrancar
  if (clientInflux.validateConnection()) {
    Serial.print("Conectado a InfluxDB Cloud: ");
    Serial.println(clientInflux.getServerUrl());
  } else {
    Serial.print("Error conexion InfluxDB: ");
    Serial.println(clientInflux.getLastErrorMessage());
  }

  // Etiqueta fija del punto de medición
  sensorPoint.addTag("dispositivo", "ESP32_Invernadero");

  dht.begin();
  compuertaServo.attach(SERVOPIN);
  compuertaServo.write(0);
  pinMode(LEDPIN, OUTPUT);
  digitalWrite(LEDPIN, LOW);

  lcd.init();
  lcd.backlight();
  lcd.print("Invernadero IoT");

  clientMQTT.setServer(tb_server, 1883);
  clientMQTT.setKeepAlive(60);
  clientMQTT.setCallback(callback);
}

void loop() {
  if (!clientMQTT.connected()) {
    reconnectMQTT();
  }
  clientMQTT.loop();

  unsigned long now = millis();
  if (now - lastMsg >= intervalo) {
    lastMsg = now;

    float temp = dht.readTemperature();
    float hum = dht.readHumidity();

    if (!isnan(temp) && !isnan(hum)) {
      // 1. Publicar JSON en ThingsBoard (MQTT)
      StaticJsonDocument<128> doc;
      doc["temperatura"] = round(temp * 10) / 10.0;
      doc["humedad"] = round(hum * 10) / 10.0;
      doc["ventilacion"] = ventilacionActiva;

      char buffer[128];
      serializeJson(doc, buffer);
      clientMQTT.publish(topic_pub, buffer);
      Serial.println("MQTT ThingsBoard -> " + String(buffer));

      // 2. Enviar datos con marca de tiempo a InfluxDB Cloud
      sensorPoint.clearFields();
      sensorPoint.addField("temperatura", temp);
      sensorPoint.addField("humedad", hum);
      sensorPoint.addField("ventilacion", ventilacionActiva ? 1 : 0);

      if (clientInflux.writePoint(sensorPoint)) {
        Serial.println("InfluxDB -> Guardado OK!");
      } else {
        Serial.print("InfluxDB Error -> ");
        Serial.println(clientInflux.getLastErrorMessage());
      }

      actualizarLCD(temp, hum);
    }
  }
}
