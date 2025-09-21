import requests
import tkinter as tk
from tkinter import messagebox, ttk
import matplotlib.pyplot as plt
import json
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
import base64
import re

SERVER_URL = "http://192.168.226.169"

username = None
password = None
public_key = None

# Function to encrypt message using server's public key
def encrypt_message(message):
    global public_key
    encrypted = public_key.encrypt(
        message.encode('utf-8'),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return base64.b64encode(encrypted).decode('utf-8')

def show_temperature_data():
    message = encrypt_message(json.dumps({"username": username, "password": password}))
    response = requests.post(f"{SERVER_URL}/temperature", data=message)
    data = response.json()
    show_data_window(data)

def show_data_window(data):
    data_window = tk.Toplevel(window, bg='#add8e6')
    data_window.title("Data Suhu")

    table = ttk.Treeview(data_window)
    table["columns"] = ("timestamp", "temperature")
    table.column("#0", width=0, stretch=tk.NO)
    table.column("timestamp", anchor=tk.CENTER, width=150)
    table.column("temperature", anchor=tk.CENTER, width=100)

    table.heading("#0", text="", anchor=tk.CENTER)
    table.heading("timestamp", text="Waktu", anchor=tk.CENTER)
    table.heading("temperature", text="Suhu", anchor=tk.CENTER)

    for timestamp, temperature in data:
        table.insert("", tk.END, values=(timestamp, temperature))

    table.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

def show_temperature_graph():
    message = encrypt_message(json.dumps({"username": username, "password": password}))
    response = requests.post(f"{SERVER_URL}/temperature", data=message)
    data = response.json()
    timestamps = [d[0][10:] for d in data[-20:]]
    temperatures = [float(re.match(r'^\d+(\.\d+)?', d[1]).group()) for d in data[-20:]]

    plt.plot(timestamps, temperatures, marker='o')
    plt.xlabel('Waktu')
    plt.ylabel('Suhu')
    plt.title('Data Suhu Terbaru')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.show()

def open_remote_control():
    def send_command(command):
        message = encrypt_message(json.dumps({"username": username, "password": password}))
        response = requests.post(f"{SERVER_URL}/control/{command}", data=message)
        current_temp = response.json()["current_temperature"]
        label_current_temp.config(text=f"Suhu AC Saat Ini: {current_temp} °C")

    remote_control_window = tk.Toplevel(window, bg='#add8e6')
    remote_control_window.title("Kontrol Jarak Jauh")

    message = encrypt_message(json.dumps({"username": username, "password": password}))
    response = requests.post(f"{SERVER_URL}/control/current", data=message)
    current_temp = response.json()["current_temperature"]

    label_current_temp = tk.Label(remote_control_window, text=f"Suhu AC Saat Ini: {current_temp} °C", bg='#add8e6')
    button_up = tk.Button(remote_control_window, text="NAIK", command=lambda: send_command("UP"))
    button_down = tk.Button(remote_control_window, text="TURUN", command=lambda: send_command("DOWN"))

    label_current_temp.pack(pady=10)
    button_up.pack(pady=10)
    button_down.pack(pady=10)

def get_current_temperature():
    message = encrypt_message(json.dumps({"username": username, "password": password}))
    response = requests.post(f"{SERVER_URL}/current_temperature", data=message)
    if response.status_code == 200:
        current_temp = response.json()["current_temperature"]
        messagebox.showinfo("Suhu Saat Ini", f"Suhu saat ini adalah {current_temp} °C")
    else:
        messagebox.showerror("Error", "Gagal mengambil suhu saat ini")

def request_log_file():
    message = encrypt_message(json.dumps({"username": username, "password": password}))
    response = requests.post(f"{SERVER_URL}/request_logfile", data=message)
    if response.status_code == 200:
        with open(f"log_{username}.txt", "wb") as log_file:
            log_file.write(response.content)
        messagebox.showinfo("Request Log File", "Log file berhasil disimpan di direktori yang sama dengan aplikasi.")
    else:
        messagebox.showerror("Request Log File", "Gagal meminta log file.")

def login():
    global username, password
    global public_key
    username = entry_username.get()
    password = entry_password.get()
    response = requests.post(f"{SERVER_URL}/login", json={"username": username, "password": password})
    try:
        response_json = response.json()
        if response.status_code == 200:
            public_key_pem = response.json()["public_key"].encode('utf-8')
            public_key = serialization.load_pem_public_key(public_key_pem)
            messagebox.showinfo("Login", "Login berhasil!")
            logged_in_frame.pack_forget()
            main_frame.pack()
        else:
            error_message = response_json.get("error", "Error tidak dikenal")
            if response.status_code == 401 and error_message == "Invalid username or password":
                error_message = "Nama pengguna atau kata sandi tidak valid"
            messagebox.showerror("Login Gagal", error_message)
    except json.decoder.JSONDecodeError:
        messagebox.showerror("Login Gagal", "Server error. Silakan coba lagi nanti.")

def logout():
    global username, password
    message = encrypt_message(json.dumps({"username": username, "password": password}))
    response = requests.post(f"{SERVER_URL}/logout", data=message)
    if response.status_code == 200:
        messagebox.showinfo("Logout", "Logout berhasil!")
        username = None
        password = None
        main_frame.pack_forget()
        logged_in_frame.pack()
    else:
        messagebox.showerror("Logout Gagal", response.json().get("error", "Error tidak dikenal"))

# UI Setup
window = tk.Tk()
window.title("Temperature Control App")
window.geometry("400x300")
window.configure(bg='#add8e6')

logged_in_frame = tk.Frame(window, bg='#add8e6')
main_frame = tk.Frame(window, bg='#add8e6')

label_username = tk.Label(logged_in_frame, text="Username", bg='#add8e6')
label_password = tk.Label(logged_in_frame, text="Password", bg='#add8e6')
entry_username = tk.Entry(logged_in_frame)
entry_password = tk.Entry(logged_in_frame, show="*")
button_login = tk.Button(logged_in_frame, text="Login", command=login)
label_username.grid(row=0, column=0, padx=5, pady=5)
label_password.grid(row=1, column=0, padx=5, pady=5)
entry_username.grid(row=0, column=1, padx=5, pady=5)
entry_password.grid(row=1, column=1, padx=5, pady=5)
button_login.grid(row=2, columnspan=2, padx=5, pady=5)

logged_in_frame.pack()

button_show_data = tk.Button(main_frame, text="Tampilkan Data Suhu", command=show_temperature_data)
button_show_graph = tk.Button(main_frame, text="Tampilkan Grafik", command=show_temperature_graph)
button_open_remote = tk.Button(main_frame, text="Kontrol Suhu AC", command=open_remote_control)
button_get_current_temp = tk.Button(main_frame, text="Tampilkan Suhu Saat Ini", command=get_current_temperature)
button_request_logfile = tk.Button(main_frame, text="Request Log File", command=request_log_file)
button_logout = tk.Button(main_frame, text="Logout", command=logout)

buttons = [button_show_data, button_show_graph, button_open_remote, button_get_current_temp, button_request_logfile, button_logout]

for i, button in enumerate(buttons):
    button.grid(row=i, column=0, padx=5, pady=5, sticky='ew')

main_frame.pack_forget()
window.mainloop()