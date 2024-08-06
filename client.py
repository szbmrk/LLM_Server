import socket
import json
import sys
import requests
import time

def start_client(server_ip, server_port):
    while True:
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((server_ip, server_port))

            file_index = 0
            if len(sys.argv) > 1:
                file_index = int(sys.argv[1])

            with open(f"client_info{str(file_index)}.json", 'r') as file:
                client_info = json.load(file)

            port = client_info["port"]
            client_info = json.dumps(client_info)

            client.send(client_info.encode('utf-8'))
            
            while True:
                try:
                    message = client.recv(1024).decode('utf-8')
                    if not message:
                        break
                    
                    url = f"http://127.0.0.1:{port}/completion"
                    data = {
                        "prompt": message,
                        "n_predict": 32,
                    }
                    response = requests.post(url, data=json.dumps(data))
                    response = response.json()['content']
                    client.send(response.encode('utf-8'))
                except (socket.error, requests.exceptions.RequestException) as e:
                    print(f"Error during message handling: {e}")
                    break

        except socket.error as e:
            print(f"Connection failed: {e}")
            time.sleep(5)

        finally:
            client.close()
            print("Disconnected from server, retrying in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    server_ip = '142.93.207.109'  
    server_port = 9999          
    start_client(server_ip, server_port)
