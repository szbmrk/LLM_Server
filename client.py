import socket
import json

def start_client(server_ip, server_port):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((server_ip, server_port))
    
    with open('client_info.json', 'r') as file:
        client_info = json.load(file)

    client_info = json.dumps(client_info)

    client.send(client_info.encode('utf-8'))
    
    while True:
        message = client.recv(1024).decode('utf-8')
        if not message:
            break
        print(f"Received from server: {message}")
        
        response = f"Client Processed message: {message}"
        client.send(response.encode('utf-8'))

if __name__ == "__main__":
    server_ip = '142.93.207.109'  
    server_port = 9999          
    start_client(server_ip, server_port)
