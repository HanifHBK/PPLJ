from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from functools import wraps
import csv
from datetime import datetime
import threading
import socket
import os
import time
import json
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
import base64

## Inisialisasi app Flask dengan
app = Flask(__name__)
app.secret_key = 'testing'

# RSA key untuk asymmetric key (bagian private key)
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)
# Public key pair
public_key = private_key.public_key()

# Serialize the public key for sending to the client
public_key_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

# Decrypt message
def decrypt_message(encrypted_message):
    decrypted_message = private_key.decrypt(
        base64.b64decode(encrypted_message)
        ,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return decrypted_message.decode('utf-8')

# File AC temperature (sehingga saat server restart nilainya tetap sama)
ac_temperature_file = 'ac_temperature.txt'

# Load temperature AC
def load_ac_temperature():
    if os.path.exists(ac_temperature_file):
        with open(ac_temperature_file, 'r') as file:
            return int(file.read().strip())
    return 25  # Default Temperature kalau tidak ada file

# Save temperature AC saat ada perubahan
def save_ac_temperature(temperature):
    with open(ac_temperature_file, 'w') as file:
        file.write(str(temperature))

global_ac_temperature = load_ac_temperature()
credentials = {} # Username Password
temperature_data = [] 
client_log_files = {} # Log Files

# Nantinya digunakan untuk bagian get_temperature
arduino_c = None

# Penanggalan
def get_current_date_formatted():
    return datetime.now().strftime('%d%m%y')

# User Credential dari file CSV
def load_user_credentials():
    global credentials
    with open('user.csv', mode='r') as file:
        reader = csv.reader(file)
        credentials = {rows[0]: rows[1] for rows in reader}

# Load User Credential hanya dilakukan sekali di awal, jadi saat server update manual
# Server harus dinyalakan ulang untuk load yang baru
load_user_credentials() 

# Fungsi untuk membaca data temperature
def load_temperature_data():
    filename = f"data_{get_current_date_formatted()}.csv"
    temperature_data = []
    if not os.path.exists(filename):
        with open(filename, mode='w', newline=''):
            pass
    try:
        with open(filename, mode='r') as file:
            reader = csv.reader(file)
            temperature_data = [row for row in reader]
    except FileNotFoundError:
        pass
    return temperature_data

# Startup 
temperature_data = load_temperature_data()

# Update data temperature
def save_temperature_data(timestamp, temperature):
    filename = f"data_{get_current_date_formatted()}.csv"
    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, temperature])

# Fungsi autentikasi user
def authenticate(username, password):
    return credentials.get(username) == password

# Log client activity
def log_client_activity(user, message):
    if user in client_log_files:
        with open(client_log_files[user], 'a') as log_file:
            log_file.write(message + "\n")

# Fungsi untuk akses langsung dari web
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# Routing web (render html untuk WebServer)
@app.route('/')
def index():
    return render_template('index.html')
@app.route('/login')
def login_page():
    return render_template('login.html')
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')
@app.route('/temperature')
@login_required
def temperature():
    return render_template('temperature.html', temperature_data=load_temperature_data())
@app.route('/control')
@login_required
def control():
    return render_template('control.html', ac_temperature=global_ac_temperature)
@app.route('/controlUP')
@login_required
def controlUP():
    global global_ac_temperature
    global_ac_temperature += 1
    return redirect(url_for('control'))
@app.route('/controlDOWN')
@login_required
def controlDOWN():
    global global_ac_temperature
    global_ac_temperature -= 1
    return redirect(url_for('control'))
@app.route('/graph')
@login_required
def graph():
    return render_template('graph.html', temperature_data=load_temperature_data())
@app.route('/get_current')
@login_required
def get_current_temperature_page():
    temperatureX = request.args.get('temperatureX', 'No temperature data')
    return render_template('get_current.html', temperature=temperatureX)
@app.route('/getCurrent')
@login_required
def getCurrent():
    global arduino_c
    try:
        arduino_c.send("generate_temperature.".encode())
        time.sleep(1)
        temperature = temperature_data[-1][1]
        return redirect(url_for('get_current_temperature_page', temperatureX = str(temperature)))
    except Exception as e:
        return redirect(url_for('get_current_temperature_page', temperatureX = "Gagal terhubung ke NodeMCU"))
@app.route('/requestlog')
@login_required
def reqlog():
    return render_template('requestlog.html')
@app.route('/logoutweb')
@login_required
def logoutweb():
    session.clear()
    return render_template('login.html')
@app.route('/requestlogweb', methods=['POST'])
def requestlogweb():
    ip = request.remote_addr
    log_filename = client_log_files.get(session['username'])
    if log_filename is None:
        return jsonify({"error": "Tidak ada file log yang tersedia untuk klien ini"}), 404
    with open(log_filename, 'r') as log_file:
        log_content = log_file.read()
    log_client_activity(session['username'], f"{ip} - - [{datetime.now().strftime('%d/%b/%Y %H:%M:%S')}] \"POST /requestlogweb HTTP/1.1\" 200 -")
    return log_content, 200, {'Content-Type': 'text/plain; charset=utf-8'}

# Routing dari App
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    ip = request.remote_addr

    if authenticate(username, password):
        session['username'] = username  # Store username in session
        session['logged_in'] = True  # Mark the user as logged in
        log_filename = f"log_{username}.txt"
        if not os.path.exists(log_filename):
            with open(log_filename, 'w') as log_file:
                log_file.write(f"Log File Client {username}:\n")
        client_log_files[username] = log_filename
        log_client_activity(username, f"{ip} - - [{datetime.now().strftime('%d/%b/%Y %H:%M:%S')}] \"POST /login HTTP/1.1\" 200 -")
        return jsonify({"message": "Login berhasil", "public_key": public_key_pem.decode('utf-8')})
    else:
        return jsonify({"error": "Username atau password salah"}), 401

@app.route('/temperature', methods=['POST'])
def get_temperature():
    encrypted_data = request.data
    data = json.loads(decrypt_message(encrypted_data))
    username = data.get("username")
    password = data.get("password")
    ip = request.remote_addr

    if not authenticate(username, password):
        return jsonify({"error": "Kredensial tidak valid"}), 401

    temperature_data = load_temperature_data()
    log_client_activity(username, f"{ip} - - [{datetime.now().strftime('%d/%b/%Y %H:%M:%S')}] \"POST /temperature HTTP/1.1\" 200 -")
    return jsonify(temperature_data)

@app.route('/control/<command>', methods=['POST'])
def control_ac(command):
    encrypted_data = request.data
    data = json.loads(decrypt_message(encrypted_data))
    username = data.get("username")
    password = data.get("password")
    ip = request.remote_addr

    if not authenticate(username, password):
        return jsonify({"error": "Kredensial tidak valid"}), 401

    global global_ac_temperature
    if command == "UP":
        global_ac_temperature += 1
    elif command == "DOWN":
        global_ac_temperature -= 1
    
    save_ac_temperature(global_ac_temperature)
    global_ac_temperature = load_ac_temperature()
    log_client_activity(username, f"{ip} - - [{datetime.now().strftime('%d/%b/%Y %H:%M:%S')}] \"POST /control/{command} HTTP/1.1\" 200 -")
    return jsonify({"current_temperature": global_ac_temperature})

@app.route('/control/current', methods=['POST'])
def get_ac_temperature():
    encrypted_data = request.data
    data = json.loads(decrypt_message(encrypted_data))
    username = data.get("username")
    password = data.get("password")
    ip = request.remote_addr
    global global_ac_temperature
    if not authenticate(username, password):
        return jsonify({"error": "Kredensial tidak valid"}), 401
    global_ac_temperature = load_ac_temperature()
    log_client_activity(username, f"{ip} - - [{datetime.now().strftime('%d/%b/%Y %H:%M:%S')}] \"POST /control/current HTTP/1.1\" 200 -")
    return jsonify({"current_temperature": global_ac_temperature})

@app.route('/current_temperature', methods=['POST'])
def get_current_temperature():
    encrypted_data = request.data
    data = json.loads(decrypt_message(encrypted_data))
    username = data.get("username")
    password = data.get("password")
    ip = request.remote_addr
    
    if not authenticate(username, password):
        return jsonify({"error": "Kredensial tidak valid"}), 401

    global arduino_c
    
    try:
        arduino_c.send("generate_temperature.".encode())
        time.sleep(1)
        temperature = temperature_data[-1][1]
        log_client_activity(username, f"{ip} - - [{datetime.now().strftime('%d/%b/%Y %H:%M:%S')}] \"POST /current_temperature HTTP/1.1\" 200 -")
        return jsonify({"current_temperature": temperature}), 200
    
    except Exception as e:
        return jsonify({"error": f"Gagal berkomunikasi dengan klien NodeMCU: {str(e)}"}), 500

@app.route('/request_logfile', methods=['POST'])
def request_logfile():
    encrypted_data = request.data
    data = json.loads(decrypt_message(encrypted_data))
    username = data.get("username")
    password = data.get("password")
    ip = request.remote_addr

    if not authenticate(username, password):
        return jsonify({"error": "Kredensial tidak valid"}), 401

    log_filename = client_log_files.get(username)
    if log_filename is None:
        return jsonify({"error": "Tidak ada file log yang tersedia untuk klien ini"}), 404

    with open(log_filename, 'r') as log_file:
        log_content = log_file.read()

    log_client_activity(username, f"{ip} - - [{datetime.now().strftime('%d/%b/%Y %H:%M:%S')}] \"POST /request_logfile HTTP/1.1\" 200 -")

    return log_content, 200, {'Content-Type': 'text/plain; charset=utf-8'}

@app.route('/logout', methods=['POST'])
def logout():
    encrypted_data = request.data
    data = json.loads(decrypt_message(encrypted_data))
    username = data.get("username")
    password = data.get("password")
    ip = request.remote_addr

    if authenticate(username, password):
        log_client_activity(username, f"{ip} - - [{datetime.now().strftime('%d/%b/%Y %H:%M:%S')}] \"POST /logout HTTP/1.1\" 200 -")
        client_log_files.pop(username, None)
        session.clear()  # Clear the session
        return jsonify({"message": "Logout berhasil"})
    else:
        return jsonify({"error": "Kredensial tidak valid"}), 401

# Fungsi untuk menangani permintaan klien Arduino (NodeMCU)
def handle_arduino_client(c, addr):
    global arduino_c
    arduino_c = c
    try:
        while True:
            data = c.recv(1024).decode()
            if not data:
                print(f"Klien NodeMCU {addr} terputus")
                break
            else:
                print(f"Data diterima dari klien NodeMCU {addr}: {data}")
                timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                save_temperature_data(timestamp, data)
                temperature_data.append([timestamp, data])  # Tambahkan data suhu baru
    except ConnectionResetError:
        print(f"Klien NodeMCU {addr} terputus")
    finally:
        c.close()

# Mulai server untuk klien Arduino
def start_arduino_server():
    HOST = "0.0.0.0"
    PORT_ARDUINO = 11000
    s_arduino = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s_arduino.bind((HOST, PORT_ARDUINO))
    s_arduino.listen()
    print("Server NodeMCU dimulai di port", PORT_ARDUINO)

    while True:
        c_arduino, addr_arduino = s_arduino.accept()
        print(f"Klien NodeMCU {addr_arduino} terhubung")
        threading.Thread(target=handle_arduino_client, args=(c_arduino, addr_arduino)).start()

# Menjalankan Server (Arduino threading dan Flask di main)
if __name__ == '__main__':
    try:
        arduino_server_thread = threading.Thread(target=start_arduino_server)
        arduino_server_thread.daemon = True 
        arduino_server_thread.start()
        app.run(host="0.0.0.0", port=80, debug=False)
    except KeyboardInterrupt:
        print("Shutting Down Server...")