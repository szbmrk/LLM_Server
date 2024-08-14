import socket
import threading
import json
import queue
from flask import Flask, jsonify, request
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

clients = []
clients_lock = threading.Lock()
server_running = threading.Event()

class Model:
    def __init__(self, filename, tokens, difficulty):
        self.filename = filename
        self.tokens = tokens
        self.difficulty = difficulty
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
        self.send_lock = threading.Lock()
        self.recv_queue = queue.Queue()
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.models = []

    def set_client_info(self, client_info):
        self.client_info = client_info
        self.models = [Model(model["filename"], model["tokens", model["difficulty"]]) for model in client_info["models"]]

    def set_client_socket(self, client_socket):
        self.client_socket = client_socket

    def set_client_address(self, client_address):
        self.client_address = client_address

    def __eq__(self, other):
        return self.client_socket == other.client_socket

def handle_client(client):
    client_info = client.client_info
    try:
        while server_running.is_set():
            try:
                data = client.client_socket.recv(1024)
                if not data:
                    print(f"Client {client_info} disconnected")
                    break
                response = data.decode('utf-8')
                print(f"Received data from {client_info}: {response}")
                client.recv_queue.put(response)
                
                # Set the model back to free
                response_json = json.loads(response)
                model_filename = response_json.get('model')
                if model_filename:
                    for model in client.models:
                        if model.filename == model_filename:
                            model.set_free()
                            print(f"Model {model_filename} set back to free")
                            break
            except socket.error as e:
                print(f"Socket error with {client_info}: {e}")
                break
    finally:
        with clients_lock:
            if client in clients:
                clients.remove(client)
                print(f"Client {client_info} removed from clients list")
        client.client_socket.close()
        client.executor.shutdown(wait=False)

def send_message_to_client(client, model, data):
    client_socket = client.client_socket
    client_info = client.client_info

    with client.send_lock:
        try:
            message = json.dumps(data)
            client_socket.sendall(message.encode('utf-8'))
            print(f"Sent message to {data['model']}: {message}")
            model.set_busy()
            print(f"Model {model.filename} set to busy")

            try:
                response = client.recv_queue.get(timeout=60)
                print(f"{client_info}: {response}")
                return json.loads(response)
            except queue.Empty:
                print(f"Timeout while waiting for response from {client_info}")
                model.set_free()
                return {"status": "Timeout"}

        except (socket.error, Exception) as e:
            print(f"Error sending message to {client_info}: {e}")
            model.set_free()
            with clients_lock:
                if client in clients:
                    clients.remove(client)
                    print(f"Client {client_info} removed from clients list due to error")
            return {"status": "Error"}

def start_server(host, port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(5)
    print(f"Server listening on {host}:{port}")
    server_running.set()
    
    while server_running.is_set():
        try:
            server.settimeout(1.0)
            try:
                client_socket, client_address = server.accept()
                client = handle_incoming_client_info(client_socket, client_address)
                client_handler = threading.Thread(target=handle_client, args=(client,))
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

def handle_incoming_client_info(client_socket, client_address):
    client_info_json = json.loads(client_socket.recv(1024).decode('utf-8'))
    print(f"Received client info from {client_address}: {client_info_json}")
    client = Client()
    client.set_client_info(client_info_json)
    client.set_client_socket(client_socket)
    client.set_client_address(client_address)
    
    with clients_lock:
        clients.append(client)
    
    return client

@app.route('/clients', methods=['GET'])
def get_clients():
    with clients_lock:
        clients_list = [{
            "info": client.client_info,
            "models": [{"filename": model.filename, "free": model.free} for model in client.models]
        } for client in clients]
    return jsonify(clients_list)

@app.route('/send_message', methods=['POST'])
def api_send_message():
    data = request.json
    prompt = data.get('prompt')
    context = data.get('context')
    n = data.get('n')
    temp = data.get('temp')

    with clients_lock:
        if not clients:
            return jsonify({"status": "No clients connected"}), 400

        free_models = []
        for client in clients:
            free_models.extend([(client, model) for model in client.models if model.free])

        if not free_models:
            return jsonify({"status": "No free models available"}), 400

        futures = []
        for client, model in free_models:
            data_to_send = {
                'model': model.filename,
                'prompt': prompt,
                'context': context,
                'n': n,
                'temp': temp
            }
            future = client.executor.submit(send_message_to_client, client, model, data_to_send)
            futures.append(future)

        responses = [future.result() for future in futures]
        return jsonify({"status": "Messages sent", "responses": responses}), 200

@app.route('/shutdown', methods=['POST'])
def shutdown():
    server_running.clear()
    return jsonify({"status": "Server is shutting down..."}), 200

def run_flask():
    app.run(host='0.0.0.0', port=5000)

if __name__ == "__main__":
    host = '0.0.0.0'
    port = 9999
    
    server_thread = threading.Thread(target=start_server, args=(host, port))
    server_thread.start()
    
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    server_thread.join()
    flask_thread.join()
    
    print("Server has been shut down.")