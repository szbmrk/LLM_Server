import socket
import threading
import json
import queue
from flask import Flask, jsonify, request

app = Flask(__name__)

clients = []
clients_lock = threading.Lock()
server_running = threading.Event()

class Client:
    def __init__(self):
        self.client_address = None
        self.client_socket = None
        self.client_info = None
        self.send_lock = threading.Lock()
        self.recv_queue = queue.Queue()
        self.request_id = 0
        self.pending_requests = {}

    def set_client_info(self, client_info):
        self.client_info = client_info

    def set_client_socket(self, client_socket):
        self.client_socket = client_socket

    def set_client_address(self, client_address):
        self.client_address = client_address

    def get_next_request_id(self):
        self.request_id += 1
        return self.request_id

    def add_pending_request(self, request_id):
        self.pending_requests[request_id] = queue.Queue()

    def get_pending_response(self, request_id, timeout=60):
        try:
            response = self.pending_requests[request_id].get(timeout=timeout)
            del self.pending_requests[request_id]
            return response
        except queue.Empty:
            del self.pending_requests[request_id]
            return {"status": "Timeout"}

    def put_pending_response(self, request_id, response):
        if request_id in self.pending_requests:
            self.pending_requests[request_id].put(response)

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
        with clients_lock:
            if client in clients:
                clients.remove(client)
                print(f"Client {client_info} removed from clients list")
        client.client_socket.close()

def send_message_to_client(client, model, prompt, context):
    request_id = client.get_next_request_id()
    client.add_pending_request(request_id)

    with client.send_lock:
        try:
            message = json.dumps({
                "id": request_id,
                "model": model,
                "prompt": prompt,
                "context": context,
            })

            client.client_socket.sendall(message.encode('utf-8'))
            print(f"Sent message to {client.client_info}: {message}")

            response = client.get_pending_response(request_id)
            print(f"{client.client_info}: {response}")
            return response

        except (socket.error, Exception) as e:
            print(f"Error sending message to {client.client_info}: {e}")
            with clients_lock:
                if client in clients:
                    clients.remove(client)
                    print(f"Client {client.client_info} removed from clients list due to error")
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
        clients_list = [client.client_info for client in clients]
    return jsonify(clients_list)

@app.route('/send_message', methods=['POST'])
def api_send_message():
    data = request.json
    prompt = data.get('prompt')
    context = data.get('context')
    with clients_lock:
        if clients:
            response = send_message_to_client(clients[0], clients[0].client_info["models"][0]["filename"], prompt, context)
            return jsonify({"status": "Message sent", "response": response}), 200
        else:
            return jsonify({"status": "No clients connected"}), 400

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