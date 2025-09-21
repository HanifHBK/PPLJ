import socket
import time
import random

HOST = "localhost"  # Localhost
PORT = 11000
# Socket
s = socket.socket()

# Connect
s.connect((HOST, PORT))

# Interval for periodic data transmission (5 minutes)
interval = 60  # seconds

# Initialize the last transmission time
last_transmission_time = time.time()

while True:
    # Check if it's time to send periodic data
    if time.time() - last_transmission_time >= interval:
        # Generate random number between 1 and 100
        random_number = random.randint(1, 100)
        message = str(random_number)
        # Send the random number as a message
        s.send(message.encode())
        # Update the last transmission time
        last_transmission_time = time.time()

    # Wait for response or timeout
    try:
        s.settimeout(interval)  # Set the timeout to the interval duration
        data = s.recv(1024).decode()
        if data == "generate_temperature.":
            # Generate random number for temperature
            random_number = random.randint(1, 100)
            message = str(random_number) + " (onDemand)"
            # Send the random number as a message
            s.send(message.encode())
        elif not data:
            print("Connection closed by the server.")
            break
    except socket.timeout:
        print("No response received from the server within the interval.")
    except socket.error as e:
        print("Socket error:", e)
        break
    except Exception as e:
        print("Error:", e)
        break

s.close()  # Close the socket when done
