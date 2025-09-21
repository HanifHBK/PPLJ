<img width="902" height="517" alt="image" src="https://github.com/user-attachments/assets/3c338b61-0e3d-4aaa-a1fb-5d6b8a58f1ad" /># Temperature Monitoring and Air Conditioner Control System

This repository contains the implementation of a **Temperature Monitoring and Control Application**, developed as part of the **EL4236 – Network Software Design** course project at Institut Teknologi Bandung.  

The system is designed with three main components:
- **Server (Python + Flask)** – handles communication, data storage, authentication, and control logic  
- **Client 1 (Raspberry Pi, Python GUI)** – user interface for monitoring temperature and controlling the AC  
- **Client 2 (NodeMCU + DHT22, Arduino C++)** – IoT device that reads temperature and sends it to the server  

> ⚡ My main contribution is the **Server implementation**, but the repository also includes code for both clients for completeness.

---

## Features
- **Temperature Monitoring**
  - Periodic data logging in CSV format
  - Real-time (on-demand) temperature requests
- **User Authentication**
  - Login/logout with asymmetric RSA key encryption
- **Air Conditioner Control**
  - Remote commands to increase or decrease the AC setpoint
- **Data Storage**
  - CSV logs for temperature
  - TXT logs for user activity and AC set temperature
- **Webserver (Flask)**
  - Simple HTML pages for login, monitoring, and control

---

## Repository Structure
.
├── Client1_Raspi.py # Client 1 (Raspberry Pi, Python Tkinter GUI)
├── Client2_NodeMCU.ino # Client 2 (NodeMCU + DHT22 sensor, Arduino IDE)
├── Dummy.py # Dummy client for testing
├── Server.py # Main server implementation (Flask + Socket)
├── Server_Komputer.py # Alternate server file (same as Server.py)
├── ac_temperature.txt # AC temperature log file
├── user.csv # User credentials (username, password)
├── data_*.csv # Logged temperature data with timestamps
├── log_admin.txt # User activity log file
└── EL4236_Laporan...pdf # Project report documentation


---

## How It Works
- **Client 2 (NodeMCU)** sends periodic temperature readings to the server via **Socket**.  
- **Server** stores the temperature in CSV files and provides APIs over **HTTP (Flask)** for Client 1.  
- **Client 1 (Raspberry Pi)** communicates with the server via HTTP to:  
  - Login / logout  
  - Request current temperature  
  - Display historical data (table + graph)  
  - Request log files  
  - Send AC control commands  

---

## Running the System

### 1. Start the Server
```bash
python3 Server.py
```
Runs Flask HTTP server on port 80
Opens Socket server on port 11000 for NodeMCU
### 2. Run Client 1 (Raspberry Pi)
```bash
python3 Client1_Raspi.py
```
Launches GUI application with login, monitoring, and AC control features.
3. Deploy Client 2 (NodeMCU)
Open Client2_NodeMCU.ino in Arduino IDE.
Configure WiFi SSID and password.
Upload to NodeMCU V3 (ESP8266) with DHT22 sensor attached.

## Contributors
Server (Python + Flask) – Muhammad Hanif Hibatullah
Client 1 (Raspberry Pi GUI) – Samuel Benyamin Niman
Client 2 (NodeMCU + DHT22) – Bayu Aji Nugroho

## License
This project was developed for academic purposes as part of EL4236 – Network Software Design at Institut Teknologi Bandung.
