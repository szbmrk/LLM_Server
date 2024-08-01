import socket

def start_client(server_ip, server_port, client_info):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((server_ip, server_port))
    
    # Send initial information to the server
    client.send(client_info.encode('utf-8'))
    
    while True:
        # Receive message from the server
        message = client.recv(1024).decode('utf-8')
        if not message:
            break
        print(f"Received from server: {message}")
        
        # React to the server's message
        response = f"Client Processed message: {message}"
        client.send(response.encode('utf-8'))

if __name__ == "__main__":
    server_ip = '142.93.207.109'  # Server IP address
    server_port = 9999          # Port server is listening on
    client_info = "LLama3"  # Replace with actual client info
    start_client(server_ip, server_port, client_info)
