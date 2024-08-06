import platform

def get_os():
    os_name = platform.system()
    if os_name == "Windows":
        print("You are on Windows")
    elif os_name == "Linux":
        print("You are on Linux")
    else:
        print(f"Unknown operating system: {os_name}")

get_os()