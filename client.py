import socket
import json
import platform
import subprocess
import time
import os
from dotenv import load_dotenv
import psutil

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
        total_vram = input("Enter the total VRAM of your GPU in GB: ")
        free_vram = input("Enter the free VRAM of your GPU in GB: ")
        return f"{total_vram} GB", f"{free_vram} GB"
    
    elif platform.system() == "Linux":
        return _get_vram_info_linux()
    
    else:
        return get_size(0), get_size(0)

def _get_vram_info_linux():
    try:
        total_vram_nvidia = subprocess.check_output(
            "nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits", shell=True
        ).decode('utf-8').strip()
        free_vram_nvidia = subprocess.check_output(
            "nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits", shell=True
        ).decode('utf-8').strip()
        return get_size(int(total_vram_nvidia) * 1024 * 1024), get_size(int(free_vram_nvidia) * 1024 * 1024)
    except subprocess.CalledProcessError:
        pass

    try:
        total_vram_amd = subprocess.check_output(
            "rocm-smi --showtotalmem | grep 'Total Memory' | awk '{print $4}'", shell=True
        ).decode('utf-8').strip()
        free_vram_amd = subprocess.check_output(
            "rocm-smi --showmemuse | grep 'Free Memory' | awk '{print $4}'", shell=True
        ).decode('utf-8').strip()
        return get_size(int(total_vram_amd) * 1024 * 1024), get_size(int(free_vram_amd) * 1024 * 1024)
    except subprocess.CalledProcessError:
        return get_size(0), get_size(0)

def get_models():
    models = []
    path = os.getenv('MODELS_PATH')
    if path and os.path.exists(path):
        for model in os.listdir(path):
            if model.endswith(".gguf"):
                models.append(get_model_info_from_filename(model))
    return models

def get_model_info_from_filename(filename):
    with open("models.csv", "r") as f:
        for line in f:
            data = line.strip().split(";")
            if data[0] == filename:
                return {"filename": data[0], "tokens": data[1], "difficulty": data[2]}
    return {"filename": filename, "tokens": "", "difficulty": ""}

def handle_server_message(client, message):
    response = {"answer": "No response", "status": "Error"}

    try:
        data = json.loads(message)
        model = data["model"]
        prompt = data["prompt"]
        context = data["context"]

        models_path = os.getenv('MODELS_PATH')
        llamacpp_path = os.getenv(f'LLAMACPP_PATH_{platform.system()}')

        if models_path and llamacpp_path:
            command = f"{llamacpp_path} -m {models_path}/{model} -p \"{prompt}\" -c \"{context}\" -n 100 --temp 0.1 --repeat_penalty 1.1"
            
            result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            response["answer"] = result.stdout if result.returncode == 0 else result.stderr
            response["status"] = "Success" if result.returncode == 0 else "Error"
    except (subprocess.CalledProcessError, Exception) as e:
        response["answer"] = f"Error: {e}"

    client.send(json.dumps(response).encode('utf-8'))

def start_client(server_ip, server_port):
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
                client.connect((server_ip, server_port))

                total_ram, free_ram = get_ram_info()
                total_vram, free_vram = get_vram_info()
                models = get_models()

                client_info = {
                    "ram_info": {"total_ram": total_ram, "free_ram": free_ram},
                    "vram_info": {"total_vram": total_vram, "free_vram": free_vram},
                    "models": models,
                }

                client.send(json.dumps(client_info).encode('utf-8'))
                
                while True:
                    message = client.recv(1024).decode('utf-8')
                    if not message:
                        break
                    
                    handle_server_message(client, message)

        except socket.error as e:
            print(f"Connection failed: {e}")
            time.sleep(5)
        finally:
            print("Disconnected from server, retrying in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    load_dotenv()
    server_ip = '142.93.207.109'
    server_port = 9999
    start_client(server_ip, server_port)