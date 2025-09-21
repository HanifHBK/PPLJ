#include <ESP8266WiFi.h> //library esp8266
#include <DHT.h> //library sensor DHT22
#include <Ticker.h> //library timer nodemcu

// inisialisasi sensor DHT22
#define DHTPIN D4     
#define DHTTYPE DHT22   
DHT dht(DHTPIN, DHTTYPE); 
float temp; // variabel suhu

//variabel utk wifi dan tcp ip
const char* ssid     = "Irman"; // SSID Wifi
const char* password = "3.14159265"; // Password Wifi
const char* server = "192.168.226.169"; // IP Server
const int port = 11000; // 

WiFiClient client;

//variabel timer nodemcu
Ticker ticker;
volatile unsigned long detik = 0;
volatile unsigned long menit = 0;

// interupsi timer & data sensor di kirim sesuai timer
void ICACHE_RAM_ATTR onTimer() {
  detik++;
  if (detik >= 60) { //jumlah detik dalam 1 menit
    detik = 0;
    menit++;
  }
  if (menit >= 30){ //jumlah menit, atur sesuai berapa lama rentang waktu pengiriman berkala
    menit = 0;
    // Kirim data ke server melalui socket
    sendDataToServer(temp, false); //kirim data suhu berkala 30 menit
  }
}

void setup() {
  Serial.begin(115200);
  delay(500);
  dht.begin();

  // Setup timer dengan interval 1 detik (1000ms)
  ticker.attach(1, onTimer);

  // Koneksi ke WiFi
  Serial.println();
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  // Menampilkan IP klien arduino
  Serial.println("");
  Serial.println("WiFi connected");  
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
  delay(5000);

  // Koneksi ke server
  Serial.print("Connecting to ");
  Serial.println(server);
  if (!client.connect(server, port)) {
    Serial.println("Connection failed");
    return;
  } else {
    Serial.println("Connected to server");
    temp = dht.readTemperature(); //baca data suhu di awal koneksi
    sendDataToServer(temp, false); // Kirim data suhu awal koneksi
  }
}

// void baca suhu dan kirim data ke server
void sendDataToServer(float temp, bool onDemand) {
  if (client.connected()) {
    String data = String(temp);
    if(onDemand){
      client.print(data + " (onDemand)");  //Kirim data ke server berdasar permintaan
    } else {
      client.print(data);  //Kirim data ke server berdasar waktu berkala
    }
    Serial.print("Data sent: " + data); //tampilan di serial monitor
    Serial.println(" Celcius");
  } else {
    Serial.println("Connection to server lost");
    // Reconnect jika gagal
    if (!client.connect(server, port)) {
      Serial.println("Reconnection failed");
    } else {
      Serial.println("Reconnected to server");
    }
  }
}

void loop() {
  // Baca dan simpan sensor
  temp = dht.readTemperature(); 

  // Menerima perintah permintaan suhu saat ini (realtime)
  String currentLine = ""; //variabel perintah
    while (client.connected()) {
      if (client.available()) {
        char c = client.read(); //baca karakter huruf dari serial
        if (currentLine == "generate_temperature") {
            Serial.print("server meminta data suhu --> ");
            sendDataToServer(temp, true);
            currentLine = "";
            break;
        }
        if (c != '\r') {
          currentLine += c;
        }
      }
    }
    delay(100);
}

