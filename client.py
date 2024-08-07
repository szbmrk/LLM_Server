import socket
import json
import platform
import requests
import time
import psutil
import os

def get_size(bytes, suffix="B"):
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f} {unit}{suffix}"
        bytes /= factor

def get_ram_info():
    svmem = psutil.virtual_memory()
    return get_size(svmem.total), get_size(svmem.available)

def get_vram_info():
    if platform.system() == "Windows":
        return get_size(0), get_size(0)
    elif platform.system() == "Linux":
        return get_size(0), get_size(0)
    else:
        return get_size(0), get_size(0)
    
def get_models():
    models = []
    for model in os.listdir("models"):
        if model.endswith(".gguf") and model != "example_model.gguf":
            models.append(get_model_info_from_filename(model))
    return models

def get_model_info_from_filename(filename):
    return { "model_name": filename }

def start_client(server_ip, server_port):
    while True:
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((server_ip, server_port))

            total_ram, free_ram = get_ram_info()
            total_vram, free_vram = get_vram_info()
            models = get_models()

            client_info = {
                "ram_info": {
                    "total_ram": total_ram,
                    "free_ram": free_ram,
                },
                "vram_info": {
                    "total_vram": total_vram,
                    "free_vram": free_vram,
                },
                "models": models,
            }

            client_info_json = json.dumps(client_info)
            client.send(client_info_json.encode('utf-8'))
            
            while True:
                try:
                    message = client.recv(1024).decode('utf-8')
                    if not message:
                        break
                    
                    port = 8080 
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