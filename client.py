import socket
import json
import platform
import requests
import time
import psutil
import os
import subprocess

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
        total_vram = int(input("Enter the total VRAM of your GPU in GB: "))
        free_vram = int(input("Enter the free VRAM of your GPU in GB: "))
        return get_size(total_vram), get_size(free_vram)
    
    elif platform.system() == "Linux":
        vram_info = 0, 0
        try:
            total_vram_nvidia = subprocess.check_output(
                "nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits", shell=True
            ).decode('utf-8').strip().split('\n')
            free_vram_nvidia = subprocess.check_output(
                "nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits", shell=True
            ).decode('utf-8').strip().split('\n')
            
            return get_size(total_vram_nvidia), get_size(free_vram_nvidia)

        except:
            vram_info = get_size(0), get_size(0)

        try:
            total_vram_amd = subprocess.check_output(
                "rocm-smi --showtotalmem | grep 'Total Memory' | awk '{print $4}'", shell=True
            ).decode('utf-8').strip().split('\n')
            free_vram_amd = subprocess.check_output(
                "rocm-smi --showmemuse | grep 'Free Memory' | awk '{print $4}'", shell=True
            ).decode('utf-8').strip().split('\n')
            
            return get_size(total_vram_amd), get_size(free_vram_amd)
        except:
            vram_info = get_size(0), get_size(0)

        return vram_info
    else:
        return get_size(0), get_size(0)
    
def get_models():
    models = []
    for model in os.listdir("models"):
        if model.endswith(".gguf") and model != "example_model.gguf":
            models.append(get_model_info_from_filename(model))
    return models

def get_model_info_from_filename(filename):
    #read models.csv
    with open("models.csv", "r") as f:
        lines = f.readlines()
        for line in lines:
            data = line.strip().split(";")
            if data[0] == filename:
                return { "filename": data[0], "tokens": data[1], "difficulty": data[2] }
    return { "filename": filename, "tokens": "", "difficulty": "" }

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
                    
                    response = ""

                    data = json.loads(message)
                    model = data["model"]
                    prompt = data["prompt"]
                    context = data["context"]

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