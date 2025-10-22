import socket
import ssl
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
    with lock:
        for client in list(clients.keys()):
            if client != sender_socket:
                try:
                    client.sendall(message.encode('utf-8'))
                except:
                    client.close()
                    del clients[client]

def handle_client(conn, addr):
    try:
        conn.sendall("Ingresa tu nickname: ".encode('utf-8'))
        nickname = conn.recv(1024).decode('utf-8').strip()
        with lock:
            clients[conn] = nickname
        print(f"[{nickname}] conectado desde {addr}")
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
    finally:
        with lock:
            if conn in clients:
                left_nick = clients.pop(conn)
                broadcast(f"{left_nick} salió del chat.\n")
                print(f"[{left_nick}] desconectado.")
        conn.close()

def start_server():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    
    base_path = os.path.dirname(__file__)
    cert_path = os.path.join(base_path, "server.crt")
    key_path = os.path.join(base_path, "server.key")

    context.load_cert_chain(certfile=cert_path, keyfile=key_path)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)

    print(f"[TLS SERVER] Esperando conexiones seguras en {HOST}:{PORT}...")

    with context.wrap_socket(server_socket, server_side=True) as tls_server:
        while True:
            conn, addr = tls_server.accept()
            print(f"[Nueva conexión TLS] {addr}")
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()

if __name__ == "__main__":
    start_server()
