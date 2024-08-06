import socket
import json
import sys
import requests
import time
import psutil
from py3nvml.py3nvml import nvmlInit, nvmlDeviceGetCount, nvmlDeviceGetHandleByIndex, nvmlDeviceGetMemoryInfo

def get_ram_info():
    ram_info = psutil.virtual_memory()
    return {
        'total_ram': ram_info.total,
        'available_ram': ram_info.available,
    }

def get_vram_info():
    try:
        nvmlInit()
        device_count = nvmlDeviceGetCount()
        vram_info_list = []
        for i in range(device_count):
            handle = nvmlDeviceGetHandleByIndex(i)
            memory_info = nvmlDeviceGetMemoryInfo(handle)
            vram_info_list.append({
                'total_vram': memory_info.total,
                'used_vram': memory_info.used,
                'free_vram': memory_info.free
            })
        return vram_info_list
    except Exception as e:
        print(f"Failed to get VRAM info: {e}")
        return []

def start_client(server_ip, server_port):
    while True:
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((server_ip, server_port))

            ram_info = get_ram_info()
            vram_info = get_vram_info()

            client_info = {
                "ram_info": ram_info,
                "vram_info": vram_info,
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