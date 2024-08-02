import socket
import threading
import json

clients = []

isClientConnected = False

class Client:
    def __init__(self):
        self.client_info = {
            "model": "",
            "RAM": ""
        }
        self.client_socket = None
        self.client_address = None

    def set_client_info(self, model, RAM):
        self.client_info['model'] = model
        self.client_info['RAM'] = RAM

    def set_client_socket(self, client_socket):
        self.client_socket = client_socket

    def __eq__(self, other):
        return self.client_info == other.client_info


def handle_client(client_socket, client_address, client_info):
    print(f"Connection from {client_address} has been established with info: {client_info}")
    global isClientConnected
    isClientConnected = True

    while True:
        try:
            response = client_socket.recv(1024).decode('utf-8')
            if not response:
                break
            print(f"Received from {client_info}: {response}")
        except:
            break
    
    client_socket.close()

    for client in clients:
        if client.client_info == client_info:
            clients.remove(client)
            break

    if len(clients) == 0:
        isClientConnected = False

    print(f"Connection with {client_address} ({client_info}) closed.")

def send_message_to_client(model, ram, message):
    client_info = None
    client_socket = None

    for client in clients:
        if client.client_info['model'] == model and client.client_info['RAM'] == ram:
            client_info = client.client_info
            client_socket = client.client_socket
            break

    if client_socket:
        try:
            client_socket.send(message.encode('utf-8'))
            print(f"Sent message to {client_info}: {message}")

            # Wait for the client's response
            response = client_socket.recv(1024).decode('utf-8')
            if response:
                print(f"Received response from {client_info}: {response}")
                return True
            else:
                print(f"No response from {client_info}")
                return False
        except Exception as e:
            print(f"Error communicating with {client_info}: {e}")
            return False
    else:
        print(f"Client with info '{client_info}' not found.")
        return False

def start_server(host, port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(5)
    print(f"Server listening on {host}:{port}")
    
    while True:
        client_socket, client_address = server.accept()

        client = handle_incoming_client_info(client_socket)

        client_handler = threading.Thread(target=handle_client, args=(client_socket, client_address, client.client_info))
        client_handler.start()

def handle_incoming_client_info(client_socket):
    client_info_json = json.loads(client_socket.recv(1024).decode('utf-8'))
    client = Client()
    client.set_client_info(client_info_json['model'], client_info_json['RAM'])
    client.set_client_socket(client_socket)
    clients.append(client)
    return client


if __name__ == "__main__":
    host = '142.93.207.109'
    port = 9999            
    threading.Thread(target=start_server, args=(host, port)).start()
    
    while True:
        if isClientConnected:
            model = input("Enter MODEL to send a message: ")
            ram = input("Enter RAM of the client: ")
            message = input("Enter message to send: ")
            if send_message_to_client(model, ram, message):
                print("Message sent successfully and response received.")
            else:
                print("Failed to send message or receive response.")
