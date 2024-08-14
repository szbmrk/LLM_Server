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
        self.message_queue = queue.Queue()
        self.running = True

    def set_client_info(self, client_info):
        self.client_info = client_info

    def set_client_socket(self, client_socket):
        self.client_socket = client_socket

    def set_client_address(self, client_address):
        self.client_address = client_address

    def __eq__(self, other):
        return self.client_socket == other.client_socket

    def start_sending_thread(self):
        sending_thread = threading.Thread(target=self._send_messages)
        sending_thread.start()

    def _send_messages(self):
        while self.running:
            try:
                message = self.message_queue.get(timeout=1)
                if message:
                    with self.send_lock:
                        self.client_socket.sendall(message.encode('utf-8'))
                        print(f"Sent message")
            except queue.Empty:
                continue

    def stop(self):
        self.running = False

def handle_client(client):
    client_info = client.client_info
    client.start_sending_thread()
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
        client.stop()
        with clients_lock:
            if client in clients:
                clients.remove(client)
                print(f"Client {client_info} removed from clients list")
        client.client_socket.close()

def send_message_to_client(client, data):
    try:
        message = json.dumps({
            "model": data['model'],
            "prompt": data['prompt'],
            "context": data['context'],
            "n": data['n'],
            "temp": data['temp']
        })

        client.message_queue.put(message)
        print(f"Message queued for {data['model']}: {message}")

        try:
            response = client.recv_queue.get(timeout=60)
            print(f"{client.client_info}: {response}")
            return json.loads(response)
        except queue.Empty:
            print(f"Timeout while waiting for response from {client.client_info}")
            return {"status": "Timeout"}

    except (socket.error, Exception) as e:
        print(f"Error sending message to {client.client_info}: {e}")
        with clients_lock:
            if client in clients:
                clients.remove(client)
                print(f"Client {client.client_info} removed from clients list due to error")
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
    data_to_send['model'] = clients[0].client_info["models"][0]["filename"]
    data_to_send['prompt'] = prompt
    data_to_send['context'] = context
    data_to_send['n'] = n
    data_to_send['temp'] = temp
    with clients_lock:
        if clients:
            response = send_message_to_client(clients[0], data_to_send)
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