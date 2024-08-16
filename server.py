import socket
import threading
import json
import queue
from flask import Flask, jsonify, request

app = Flask(__name__)

class Model:
    def __init__(self, filename, tokens, difficulty):
        self.filename = filename
        self.tokens = None
        self.difficulty = None
        self.free = True
        self.lock = threading.Lock()

    def set_busy(self):
        with self.lock:
            self.free = False

    def set_free(self):
        with self.lock:
            self.free = True

clients = []
server_running = threading.Event()

class Client:
    def __init__(self):
        self.client_address = None
        self.client_socket = None
        self.client_info = None
        self.models = []
        self.recv_queue = queue.Queue()

    def set_client_info(self, client_info):
        self.client_info = client_info
        self.models = [Model(model["filename"], model["tokens"], model["difficulty"]) for model in client_info["models"]]

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
                print(f"Received data from {client_info}: {data.decode('utf-8')}")
                client.recv_queue.put(data.decode('utf-8'))
            except socket.error as e:
                print(f"Socket error with {client_info}: {e}")
                break
    finally:
        if client in clients:
            clients.remove(client)
            print(f"Client {client_info} removed from clients list")
        client.client_socket.close()

def send_message_to_client(client, data):
    client_socket = client.client_socket
    client_info = client.client_info

    try:
        message = json.dumps({
            "model": data['model'],
            "prompt": data['prompt'],
            "context": data['context'],
            "n": data['n'],
            "temp": data['temp']
        })

        model = None
        for m in client.models:
            if m.filename == data['model']:
                model = m
                break

        client_socket.sendall(message.encode('utf-8'))
        print(f"Sent message to {data['model']}: {message}")
        model.set_busy()

        try:
            response = client.recv_queue.get(timeout=60)
            print(f"{client_info}: {response}")
            model.set_free()
            return json.loads(response)
        except queue.Empty:
            print(f"Timeout while waiting for response from {client_info}")
            model.set_free()
            return { "status": "Timeout" }

    except (socket.error, Exception) as e:
        print(f"Error sending message to {client_info}: {e}")
        if client in clients:
            clients.remove(client)
            print(f"Client {client_info} removed from clients list due to error")
        return { "status": "Error" }

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
    
    clients.append(client)
    
    return client

@app.route('/clients', methods=['GET'])
def get_clients():
    clients_list = [client.client_info for client in clients]
    return jsonify(clients_list)

@app.route('/send_message', methods=['POST'])
def api_send_message():
    data = request.json
    data_to_send = {}
    prompt = data.get('prompt')
    context = data.get('context')
    n = data.get('n')
    temp = data.get('temp')
    data_to_send['model'] = clients[0].models[0]["filename"]
    data_to_send['prompt'] = prompt
    data_to_send['context'] = context
    data_to_send['n'] = n
    data_to_send['temp'] = temp

    result_queue = queue.Queue()
    def send_message_task():
        if clients:
            response = send_message_to_client(clients[0], data_to_send)
            result_queue.put(response)

    thread = threading.Thread(target=send_message_task)
    thread.start()
    thread.join()

    response = result_queue.get()
    return jsonify({"status": "Message sent", "response": response}), 200

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