import socket
import threading
import json
from datetime import datetime
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config.json")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

HOST = config["host"]
PORT = config["port"]
MESSAGE_FILE = os.path.join(os.path.dirname(__file__), f"../{config['message_file']}")

clients = {}
lock = threading.Lock()

def save_message(user, message):
    data = {
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "user": user,
        "message": message
    }
    with lock:
        with open(MESSAGE_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(data) + "\n")

def broadcast(message, sender_socket=None):
    """Envía el mensaje a todos los clientes conectados."""
    with lock:
        for client, nickname in clients.items():
            if client != sender_socket:
                try:
                    client.sendall(message.encode('utf-8'))
                except:
                    client.close()
                    del clients[client]

def handle_client(conn, addr):
    """Maneja la comunicación con cada cliente."""
    print(f"[Nueva conexión] {addr}")

    try:
        conn.sendall("Ingresa tu nickname: ".encode('utf-8'))
        nickname = conn.recv(1024).decode('utf-8').strip()

        with lock:
            clients[conn] = nickname
        print(f"[{nickname}] se ha conectado.")
        broadcast(f"{nickname} se ha unido al chat.\n")

        while True:
            msg = conn.recv(1024)
            if not msg:
                break
            message = msg.decode('utf-8').strip()
            if message.lower() == "/users":
                conn.sendall(f"Usuarios conectados: {', '.join(clients.values())}\n".encode('utf-8'))
            else:
                print(f"[{nickname}] {message}")
                save_message(nickname, message)
                broadcast(f"[{nickname}] {message}\n", conn)

    except ConnectionResetError:
        print(f"[Cliente {addr} cerró la conexión inesperadamente]")
    except Exception as e:
        print(f"[Error con {addr}] {e}")

    finally:
        with lock:
            if conn in clients:
                left_nick = clients.pop(conn)
                broadcast(f"{left_nick} salió del chat.\n")
                print(f"[{left_nick}] desconectado.")
        conn.close()

def start_server():
    """Inicia el servidor TCP."""
    print(f"[Iniciando servidor en {HOST}:{PORT}]")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()

    print("[Servidor esperando conexiones...]")
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()

if __name__ == "__main__":
    start_server()
