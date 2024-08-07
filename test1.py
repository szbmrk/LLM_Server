import pynvml

# Initialize NVML
pynvml.nvmlInit()

# Get the number of GPUs
device_count = pynvml.nvmlDeviceGetCount()

for i in range(device_count):
    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
    name = pynvml.nvmlDeviceGetName(handle)
    memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)

    print(f"GPU {i}: {name.decode('utf-8')}")
    print(f"Total Memory: {memory_info.total / 1024**2} MB")
    print(f"Free Memory: {memory_info.free / 1024**2} MB")
    print(f"Used Memory: {memory_info.used / 1024**2} MB")
    print()

# Shutdown NVML
pynvml.nvmlShutdown()