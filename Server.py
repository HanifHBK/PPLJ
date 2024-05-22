from flask import Flask, request, jsonify
import csv
from datetime import datetime
import threading
import socket
import os

app = Flask(__name__)

global_ac_temperature = 25
credentials = {}
temperature_data = []

def get_current_date_formatted():
    return datetime.now().strftime('%d%m%y')

# Load user credentials from CSV file
def load_user_credentials():
    global credentials
    with open('user.csv', mode='r') as file:
        reader = csv.reader(file)
        credentials = {rows[0]: rows[1] for rows in reader}

load_user_credentials()

# Load temperature data from CSV at startup
def load_temperature_data():
    filename = f"data_{get_current_date_formatted()}.csv"
    temperature_data = []
    if not os.path.exists(filename):
        # Create an empty CSV file if it doesn't exist
        with open(filename, mode='w', newline=''):
            pass
    try:
        with open(filename, mode='r') as file:
            reader = csv.reader(file)
            temperature_data = [row for row in reader]
    except FileNotFoundError:
        pass
    return temperature_data

load_temperature_data()

def save_temperature_data(timestamp, temperature):
    filename = f"data_{get_current_date_formatted()}.csv"
    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, temperature])

def authenticate(username, password):
    return credentials.get(username) == password

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    if authenticate(username, password):
        return jsonify({"message": "Login successful"})
    else:
        return jsonify({"error": "Invalid username or password"}), 401

@app.route('/temperature', methods=['POST'])
def get_temperature():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    if not authenticate(username, password):
        return jsonify({"error": "Invalid credentials"}), 401

    temperature_data = load_temperature_data()
    return jsonify(temperature_data)

@app.route('/control/<command>', methods=['POST'])
def control_ac(command):
    data = request.json
    username = data.get("username")
    password = data.get("password")
    if not authenticate(username, password):
        return jsonify({"error": "Invalid credentials"}), 401

    global global_ac_temperature
    if command == "UP":
        global_ac_temperature += 1
    elif command == "DOWN":
        global_ac_temperature -= 1
    return jsonify({"current_temperature": global_ac_temperature})

@app.route('/control/current', methods=['POST'])
def get_current_temperature():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    if not authenticate(username, password):
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({"current_temperature": global_ac_temperature})

# Function to handle Arduino client requests
def handle_arduino_client(c, addr):
    try:
        while True:
            data = c.recv(1024).decode()
            if not data:
                print(f"Arduino client {addr} disconnected")
                break
            else:
                print(f"Data received from Arduino client {addr}: {data}")
                timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                save_temperature_data(timestamp, data)
    except ConnectionResetError:
        print(f"Arduino client {addr} disconnected")
    finally:
        c.close()

# Start the server for Arduino clients
def start_arduino_server():
    HOST = "localhost"
    PORT_ARDUINO = 8088
    s_arduino = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s_arduino.bind((HOST, PORT_ARDUINO))
    s_arduino.listen()
    print("Arduino server started on port", PORT_ARDUINO)

    while True:
        c_arduino, addr_arduino = s_arduino.accept()
        print(f"Arduino client {addr_arduino} connected")
        threading.Thread(target=handle_arduino_client, args=(c_arduino, addr_arduino)).start()

if __name__ == '__main__':
    arduino_server_thread = threading.Thread(target=start_arduino_server)
    arduino_server_thread.start()
    app.run(host="0.0.0.0", port=80, debug=False)
