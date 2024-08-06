import os
import platform
import psutil
import subprocess

def get_ram_info():
    total_ram = psutil.virtual_memory().total
    available_ram = psutil.virtual_memory().available
    return total_ram, available_ram

def get_vram_info():
    if platform.system() == "Windows":
        try:
            import wmi
            c = wmi.WMI()
            gpu_info = c.Win32_VideoController()[0]
            return int(gpu_info.AdapterRAM)
        except ImportError:
            print("WMI module not found. Install it using 'pip install wmi'")
            return None
        except Exception as e:
            print(f"Error retrieving VRAM information: {e}")
            return None
    elif platform.system() == "Linux":
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader,nounits'], 
                                    capture_output=True, text=True, check=True)
            return int(result.stdout.split('\n')[0]) * 1024 * 1024
        except FileNotFoundError:
            pass
        except subprocess.CalledProcessError as e:
            print(f"Error retrieving NVIDIA VRAM information: {e}")

        try:
            result = subprocess.run(['rocm-smi', '--showmeminfo', 'vram'], 
                                    capture_output=True, text=True, check=True)
            for line in result.stdout.split('\n'):
                if "VRAM Total" in line:
                    return int(line.split()[-2]) * 1024 * 1024
        except FileNotFoundError:
            pass
        except subprocess.CalledProcessError as e:
            print(f"Error retrieving AMD VRAM information: {e}")

        print("Unable to retrieve VRAM information.")
        return None
    else:
        print(f"VRAM information retrieval not supported on {platform.system()}")
        return None

def main():
    total_ram, available_ram = get_ram_info()
    vram = get_vram_info()

    print(f"Total RAM: {total_ram / (1024**3):.2f} GB")
    print(f"Available RAM: {available_ram / (1024**3):.2f} GB")
    
    if vram is not None:
        print(f"Total VRAM: {vram / (1024**3):.2f} GB")
    else:
        print("VRAM information not available")

if __name__ == "__main__":
    main()