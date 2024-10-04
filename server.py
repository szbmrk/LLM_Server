import socket
import threading
import json
import queue
from dotenv import load_dotenv
import os
from flask import Flask, jsonify, request

app = Flask(__name__)

class Model:
    def __init__(self, filename, file_size, context_window, coding, reasoning, creativity, speed):
        self.filename = filename
        self.file_size = file_size
        self.context_window = context_window
        self.coding = coding
        self.reasoning = reasoning
        self.creativity = creativity
        self.speed = speed
        self.free = True
        self.lock = threading.Lock()

    def set_busy(self):
        with self.lock:
            self.free = False

    def set_free(self):
        with self.lock:
            self.free = True

class Client:
    def __init__(self):
        self.client_address = None
        self.client_socket = None
        self.client_info = None
        self.models = []
        self.recv_queue = queue.Queue()

    def set_client_info(self, client_info):
        self.client_info = client_info
        self.models = [Model(model["filename"], model["file_size"], model["context_window"], model["coding"], model["reasoning"], model["creativity"], model["speed"]) for model in client_info["models"]]

    def set_client_socket(self, client_socket):
        self.client_socket = client_socket

    def set_client_address(self, client_address):
        self.client_address = client_address

    def __eq__(self, other):
        return self.client_socket == other.client_socket

clients = []
server_running = threading.Event()

def handle_client(client):
    try:
        while server_running.is_set():
            data = receive_data_from_client(client)
            if data:
                try:
                    json_data = json.loads(data)
                    if "ram_info" in json_data and "vram_info" in json_data:
                        client.client_info["ram_info"] = json_data["ram_info"]
                        client.client_info["vram_info"] = json_data["vram_info"]
                        print(f"Updated client info for {client.client_address}: RAM: {json_data['ram_info']}, VRAM: {json_data['vram_info']}")
                    else:
                        client.recv_queue.put(data)
                except json.JSONDecodeError:
                    client.recv_queue.put(data)
            else:
                break
    finally:
        remove_client(client)
        client.client_socket.close()

def receive_data_from_client(client):
    try:
        data = client.client_socket.recv(1024)
        if data:
            print(f"Received data from {client.client_info}: {data.decode('utf-8')}")
            return data.decode('utf-8')
        else:
            print(f"Client {client.client_info} disconnected")
            return None
    except socket.error as e:
        print(f"Socket error with {client.client_info}: {e}")
        return None

def send_message_to_client(client, data):
    try:
        model = find_model(client, data['model'])
        if not model:
            return {"status": "Model not found"}

        message = create_message(data)
        client.client_socket.sendall(message.encode('utf-8'))
        print(f"Sent message to {client.client_info}: {message}")

        model.set_busy()
        response = wait_for_response(client)
        model.set_free()

        return response if response else {"status": "Timeout"}
    except (socket.error, Exception) as e:
        print(f"Error sending message to {client.client_info}: {e}")
        remove_client(client)
        return {"status": "Error"}

def find_model(client, model_filename):
    for model in client.models:
        if model.filename == model_filename:
            return model
    return None

def create_message(data):
    return json.dumps({
        "model": data['model'],
        "prompt": data['prompt'],
        "context": data['context'],
        "n": data['n'],
        "temp": data['temp']
    })

def wait_for_response(client):
    try:
        return json.loads(client.recv_queue.get(timeout=60))
    except queue.Empty:
        print(f"Timeout while waiting for response from {client.client_info}")
        return None

def start_server(host, port):
    server_socket = setup_server_socket(host, port)
    server_running.set()

    while server_running.is_set():
        try:
            server_socket.settimeout(5.0)
            handle_incoming_connection(server_socket)
        except Exception as e:
            print(f"Error: {e}")
            break

    close_all_clients()
    server_socket.close()
    print("Server closed.")

def setup_server_socket(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"Server listening on {host}:{port}")
    return server_socket

def handle_incoming_connection(server_socket):
    try:
        client_socket, client_address = server_socket.accept()
        client = handle_incoming_client_info(client_socket, client_address)
        threading.Thread(target=handle_client, args=(client,)).start()
    except socket.timeout:
        pass

def handle_incoming_client_info(client_socket, client_address):
    client_info_json = json.loads(client_socket.recv(4096).decode('utf-8'))
    print(f"Received client info from {client_address}: {client_info_json}")

    client = Client()
    client.set_client_info(client_info_json)
    client.set_client_socket(client_socket)
    client.set_client_address(client_address)

    clients.append(client)
    return client

def remove_client(client):
    if client in clients:
        clients.remove(client)
        print(f"Client {client.client_info} removed from clients list")

def close_all_clients():
    for client in clients:
        client.client_socket.close()

@app.route('/clients', methods=['GET'])
def get_clients():
    return jsonify([client.client_info for client in clients])

@app.route('/send_message', methods=['POST'])
def api_send_message():
    if len(clients) == 0:
        return jsonify({"response": "No clients available", "status": "error"}), 404
    
    data = request.json
    data_to_send = {
        'model': clients[0].models[0].filename,
        'prompt': data.get('prompt'),
        'context': data.get('context'),
        'n': data.get('n'),
        'temp': data.get('temp')
    }

    api_key = data.get('api_key')

    if not api_key:
        return jsonify({"response": "API key is required", "status": "error"}), 400

    if api_key != os.getenv('API_KEY'):
        return jsonify({"response": "Invalid API key", "status": "error"}), 401

    response = send_message_to_first_client(data_to_send)
    return jsonify({"response": response}), 200

def send_message_to_first_client(data_to_send):
    result_queue = queue.Queue()

    def send_message_task():
        if clients:
            response = send_message_to_client(clients[0], data_to_send)
            result_queue.put(response)

    thread = threading.Thread(target=send_message_task)
    thread.start()
    thread.join()

    return result_queue.get()

@app.route('/shutdown', methods=['POST'])
def shutdown():
    server_running.clear()
    return jsonify({"status": "Server is shutting down..."}), 200

def run_flask():
    app.run(host='0.0.0.0', port=5000)

if __name__ == "__main__":
    load_dotenv()

    host = '0.0.0.0'
    port = 8080

    threading.Thread(target=start_server, args=(host, port)).start()
    threading.Thread(target=run_flask).start()
