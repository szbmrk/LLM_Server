import socket
import threading
import json
import sys
import queue

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

def send_message_to_client(model, ram, message):
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

            client_socket.settimeout(5.0)  # Set a timeout for recv to prevent blocking
            try:
                response = client_socket.recv(1024).decode('utf-8')
                if response:
                    print(f"Received response from {client_info}: {response}")
                    return True
                else:
                    print(f"No response from {client_info}")
                    return False
            except socket.timeout:
                print(f"Timeout waiting for response from {client_info}")
                return False
        except Exception as e:
            print(f"Error communicating with {client_info}: {e}")
            return False
    else:
        print(f"Client with info '{model}, {ram}' not found.")
        return False

async def handle_commands():
    global server_running
    while server_running:
        command = await asyncio.get_event_loop().run_in_executor(None, input, "Enter command: ").strip()
        if command == "show clients":
            async with clients_lock:
                if clients:
                    print("Connected clients:")
                    for (model, ram), _ in clients.items():
                        print(f"Model: {model}, RAM: {ram}")
                else:
                    print("No clients connected.")
        elif command == "close server":
            server_running = False
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
                if await send_message_to_client(model, ram, message):
                    print("Message sent successfully and response received.")
                else:
                    print("Failed to send message or receive response.")
        else:
            print("Unknown command. Type 'help' for a list of available commands.")

async def main():
    host = '142.93.207.109'
    port = 9999
    
    server_thread = threading.Thread(target=start_server, args=(host, port))
    server_thread.start()
    
    command_thread = threading.Thread(target=handle_commands)
    command_thread.start()
    
    input_thread = threading.Thread(target=input_thread)
    input_thread.start()
    
    input_thread.join()
    command_thread.join()
    server_thread.join()
    
    print("Server has been shut down.")