import psutil
import platform
import subprocess
import winreg

def get_size(bytes, suffix="B"):
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f} {unit}{suffix}"
        bytes /= factor

def get_ram_info():
    svmem = psutil.virtual_memory()
    return get_size(svmem.total), get_size(svmem.available)

def get_gpu_info():
    if platform.system() == "Windows":
        return get_size(0), get_size(0)
    elif platform.system() == "Linux":
        try:
            gpu_info = subprocess.check_output("lspci | grep -i 'vga\\|3d\\|2d'", shell=True).decode()
            return f"GPU: {gpu_info.strip()}"
        except Exception as e:
            return f"Error getting GPU info on Linux: {str(e)}"
    else:
        return "Unsupported operating system"

def get_system_info():
    # RAM Information
    total_ram, free_ram = get_ram_info()
    print(f"Total RAM: {total_ram}")
    print(f"Available RAM: {free_ram}")
    
    total_vram, free_vram = get_gpu_info()
    print(f"Total VRAM: {total_vram}")
    print(f"Free VRAM: {free_vram}")

if __name__ == "__main__":
    get_system_info()