import asyncio
import json

clients = {}
clients_lock = asyncio.Lock()
server_running = True

async def handle_client(reader, writer):
    try:
        client_info_json = await reader.read(1024)
        client_info = json.loads(client_info_json.decode('utf-8'))
        print(f"Connection established with info: {client_info}")

        async with clients_lock:
            clients[(client_info['model'], client_info['RAM'])] = writer

        while server_running:
            try:
                data = await asyncio.wait_for(reader.read(1024), timeout=1.0)
                if not data:
                    break
                print(f"Received from {client_info}: {data.decode('utf-8')}")
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Error receiving from {client_info}: {e}")
                break

    except json.JSONDecodeError as e:
        print(f"Failed to decode client info: {e}")

    finally:
        writer.close()
        await writer.wait_closed()

        async with clients_lock:
            clients.pop((client_info['model'], client_info['RAM']), None)

        print(f"Connection with {client_info} closed.")

async def start_server(host, port):
    server = await asyncio.start_server(handle_client, host, port)
    addr = server.sockets[0].getsockname()
    print(f'Serving on {addr}')

    async with server:
        await server.serve_forever()

async def send_message_to_client(model, ram, message):
    async with clients_lock:
        writer = clients.get((model, ram))
        if writer:
            try:
                writer.write(message.encode('utf-8'))
                await writer.drain()
                print(f"Sent message to {model}, {ram}: {message}")

                try:
                    response = await asyncio.wait_for(writer.read(1024), timeout=5.0)
                    print(f"Received response from {model}, {ram}: {response.decode('utf-8')}")
                    return True
                except asyncio.TimeoutError:
                    print(f"Timeout waiting for response from {model}, {ram}")
                    return False

            except Exception as e:
                print(f"Error communicating with {model}, {ram}: {e}")
                return False
        else:
            print(f"Client with info '{model}, {ram}' not found.")
            return False

async def handle_commands():
    global server_running
    while server_running:
        command = await asyncio.to_thread(input, "Enter command: ").strip()
        if command == "show clients":
            async with clients_lock:
                if clients:
                    print("Connected clients:")
                    for (model, ram), _ in clients.items():
                        print(f"Model: {model}, RAM: {ram}")
                else:
                    print("No clients connected.")
        elif command == "close server":
            server_running = False
            print("Server is shutting down...")
        elif command == "help":
            print("Available commands:")
            print("show clients")
            print("send message <model> <ram> <message>")
            print("close server")
            print("help")
        elif command.startswith("send message"):
            parts = command.split()
            if len(parts) < 5:
                print("Usage: send message <model> <ram> <message>")
            else:
                model = parts[2]
                ram = parts[3]
                message = " ".join(parts[4:])
                if await send_message_to_client(model, ram, message):
                    print("Message sent successfully and response received.")
                else:
                    print("Failed to send message or receive response.")
        else:
            print("Unknown command. Type 'help' for a list of available commands.")

async def main():
    host = '142.93.207.109'
    port = 9999
    
    server_task = asyncio.create_task(start_server(host, port))
    command_task = asyncio.create_task(handle_commands())
    
    await asyncio.gather(server_task, command_task)

if __name__ == "__main__":
    asyncio.run(main())
    print("Server has been shut down.")