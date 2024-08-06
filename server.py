import socket
import threading
import json
import queue
from flask import Flask, jsonify, request

app = Flask(__name__)

clients = []
clients_lock = threading.Lock()
server_running = threading.Event()
command_queue = queue.Queue()

class Client:
    def __init__(self):
        self.client_info = {
            "model": "",
            "RAM": ""
        }
        self.client_socket = None
        self.send_lock = threading.Lock()

    def set_client_info(self, model, RAM):
        self.client_info['model'] = model
        self.client_info['RAM'] = RAM

    def set_client_socket(self, client_socket):
        self.client_socket = client_socket

    def __eq__(self, other):
        return self.client_info == other.client_info

def handle_client(client_socket, client_address, client_info):
    print(f"Connection from {client_address} has been established with info: {client_info}")

    while server_running.is_set():
        try:
            client_socket.settimeout(1.0)  # Set a timeout for recv to prevent blocking
            response = client_socket.recv(1024).decode('utf-8')
            if not response:
                break
            print(f"Received from {client_info}: {response}")
        except socket.timeout:
            continue
        except Exception as e:
            print(f"Error receiving from {client_info}: {e}")
            break
    
    client_socket.close()

    with clients_lock:
        for client in clients:
            if client.client_info == client_info:
                clients.remove(client)
                break

    print(f"Connection with {client_address} ({client_info}) closed.")

def send_message_to_client(client, message):
    client_socket = client.client_socket
    client_info = client.client_info

    with client.send_lock:
        try:
            client_socket.sendall(message.encode('utf-8'))
            print(f"Sent message to {client_info}: {message}")

            response = client_socket.recv(1024).decode('utf-8')
            if response:
                print(f"{client_info}: {response}")
                return response
            else:
                print(f"No response from {client_info}")
                return "No response"
        except Exception as e:
            print(f"Error sending message to {client_info}: {e}")
            return str(e)
        
def start_server(host, port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(5)
    print(f"Server listening on {host}:{port}")
    server_running.set()
    
    while server_running.is_set():
        try:
            server.settimeout(1.0)  # Set timeout to allow periodic checks of server_running
            try:
                client_socket, client_address = server.accept()
                client = handle_incoming_client_info(client_socket)
                client_handler = threading.Thread(target=handle_client, args=(client_socket, client_address, client.client_info))
                client_handler.start()
            except socket.timeout:
                continue
        except Exception as e:
            print(f"Error: {e}")
            break
    
    with clients_lock:
        for client in clients:
            client.client_socket.close()
    
    server.close()
    print("Server closed.")

def handle_incoming_client_info(client_socket):
    client_info_json = json.loads(client_socket.recv(1024).decode('utf-8'))
    client = Client()
    client.set_client_info(client_info_json['model'], client_info_json['RAM'])
    client.set_client_socket(client_socket)
    
    with clients_lock:
        clients.append(client)
    
    return client

@app.route('/clients', methods=['GET'])
def get_clients():
    with clients_lock:
        clients_list = [{"model": client.client_info['model'], "RAM": client.client_info['RAM']} for client in clients]
    return jsonify(clients_list)

@app.route('/send_message', methods=['POST'])
def api_send_message():
    data = request.json
    model = data.get('model')
    ram = data.get('ram')
    message = data.get('message')
    with clients_lock:
        for client in clients:
            if client.client_info['model'] == model and client.client_info['RAM'] == ram:
                response = send_message_to_client(client, message)
                return jsonify({"status": "Message sent", "response": response}), 200
    return jsonify({"error": "Client not found"}), 404

@app.route('/shutdown', methods=['POST'])
def shutdown():
    server_running.clear()
    return jsonify({"status": "Server is shutting down..."}), 200

def run_flask():
    app.run(host='0.0.0.0', port=9998)

if __name__ == "__main__":
    host = '142.93.207.109'
    port = 9999
    
    server_thread = threading.Thread(target=start_server, args=(host, port))
    server_thread.start()
    
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    
    server_thread.join()
    flask_thread.join()
    
    print("Server has been shut down.")