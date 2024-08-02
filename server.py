import socket
import threading
import json
import sys
import queue
import asyncio

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

async def send_message_to_client(model, ram, message):
    client_info = None
    client_socket = None

    with clients_lock:
        for client in clients:
            if client.client_info['model'] == model and client.client_info['RAM'] == ram:
                client_info = client.client_info
                client_socket = client.client_socket
                break

    if client_socket:
        try:
            client_socket.sendall(message.encode('utf-8'))
            print(f"Sent message to {client_info}: {message}")

            # Use asyncio to set a timeout
            try:
                response = await asyncio.wait_for(asyncio.get_event_loop().run_in_executor(None, client_socket.recv, 1024), timeout=5.0)
                response = response.decode('utf-8')
                if response:
                    print(f"Received response from {client_info}: {response}")
                    return True
                else:
                    print(f"No response from {client_info}")
                    return False
            except asyncio.TimeoutError:
                print(f"Timeout waiting for response from {client_info}")
                return False
        except Exception as e:
            print(f"Error communicating with {client_info}: {e}")
            return False
    else:
        print(f"Client with info '{model}, {ram}' not found.")
        return False

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

async def handle_commands():
    while server_running.is_set():
        try:
            command = command_queue.get_nowait()
            await process_command(command)
        except queue.Empty:
            await asyncio.sleep(0.1)

async def process_command(command):
    if command == "show clients":
        with clients_lock:
            if clients:
                print("Connected clients:")
                for client in clients:
                    print(f"Model: {client.client_info['model']}, RAM: {client.client_info['RAM']}")
            else:
                print("No clients connected.")
    elif command == "close server":
        server_running.clear()
        print("Server is shutting down...")
    elif command == "help":
        print("Available commands:")
        print("show clients")
        print("send message <model> <ram> <message>")
        print("close server")
        print("help")
    elif command.startswith("send message"):
        parts = command.split()
        if len(parts) < 5:
            print("Usage: send message <model> <ram> <message>")
        else:
            model = parts[2]
            ram = parts[3]
            message = " ".join(parts[4:])
            asyncio.create_task(send_message_to_client(model, ram, message))
    else:
        print("Unknown command. Type 'help' for a list of available commands.")

def input_thread():
    while server_running.is_set():
        command = input("Enter command: ").strip()
        command_queue.put(command)

if __name__ == "__main__":
    host = '142.93.207.109'
    port = 9999
    
    server_thread = threading.Thread(target=start_server, args=(host, port))
    server_thread.start()
    
    asyncio.get_event_loop().run_until_complete(handle_commands())
    
    input_thread = threading.Thread(target=input_thread)
    input_thread.start()
    
    input_thread.join()
    server_thread.join()
    
    print("Server has been shut down.")