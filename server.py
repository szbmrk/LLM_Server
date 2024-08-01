import socket
import threading

# Dictionary to store client information and their sockets
clients_info = {}

def handle_client(client_socket, client_address, client_info):
    print(f"Connection from {client_address} has been established with info: {client_info}")
    
    while True:
        try:
            # Receive response from the client
            response = client_socket.recv(1024).decode('utf-8')
            if not response:
                break
            print(f"Received from {client_info}: {response}")
        except:
            break
    
    client_socket.close()
    del clients_info[client_info]
    print(f"Connection with {client_address} ({client_info}) closed.")

def send_message_to_client(client_info, message):
    client_socket = clients_info.get(client_info)
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
        client_info = client_socket.recv(1024).decode('utf-8')
        clients_info[client_info] = client_socket
        client_handler = threading.Thread(target=handle_client, args=(client_socket, client_address, client_info))
        client_handler.start()

if __name__ == "__main__":
    host = '142.93.207.109'  # Server IP address
    port = 9999            # Port to listen on
    threading.Thread(target=start_server, args=(host, port)).start()
    
    # Interactive loop for the server operator to send messages
    while True:
        client_info = input("Enter client info to send a message: ")
        message = input("Enter message to send: ")
        if send_message_to_client(client_info, message):
            print("Message sent successfully and response received.")
        else:
            print("Failed to send message or receive response.")
