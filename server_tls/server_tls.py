"""
Archivo: chat_server_basic.py

Descripción:
------------
Servidor de chat básico implementado con sockets TCP y soporte multicliente
usando hilos (threads). Esta versión no utiliza cifrado (sin SSL/TLS) y se
empleó principalmente como base de prueba del sistema de comunicación.

El servidor gestiona múltiples usuarios simultáneamente, registra los mensajes
en un archivo JSON y permite comandos especiales como `/users` para consultar
los participantes activos.

Flujo de ejecución:
-------------------
1. Carga la configuración desde 'config.json' (host, puerto y archivo de mensajes).
2. Inicia el socket del servidor y queda a la espera de conexiones.
3. Cada cliente conectado es gestionado en un hilo independiente.
4. Los mensajes se guardan con marca temporal y se retransmiten a los demás usuarios.
5. Cuando un usuario se desconecta, el servidor actualiza la lista y notifica al resto.
"""
import socket
import ssl
import threading
import json
from datetime import datetime
import os

# Carga de configuración
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config.json")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

HOST = config["host"]                # Dirección IP del servidor
PORT = config["port"]                # Puerto de escucha
MESSAGE_FILE = os.path.join(os.path.dirname(__file__), f"../{config['message_file']}")

# Variables globales
clients = {}                         # Diccionario {socket: nickname}
lock = threading.Lock()              # Asegura acceso concurrente seguro

# Función: save_message
def save_message(user, message):
    """
    Guarda cada mensaje en el archivo JSON con su usuario y timestamp.
    """
    data = {
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "user": user,
        "message": message
    }
    with lock:
        with open(MESSAGE_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(data) + "\n")

# Función: broadcast
def broadcast(message, sender_socket=None):
    """
    Envía un mensaje a todos los clientes conectados, excepto al remitente.

    Parámetros:
    -----------
    message : str
        Texto que se transmitirá a los usuarios conectados.
    sender_socket : socket
        Conexión del cliente que envía el mensaje (opcional).
    """
    with lock:
        for client in list(clients.keys()):
            if client != sender_socket:
                try:
                    client.sendall(message.encode('utf-8'))
                except:
                    client.close()
                    del clients[client]

# Función: handle_client
def handle_client(conn, addr):
     """
    Gestiona la interacción con un cliente conectado.

    Parámetros:
    -----------
    conn : socket
        Objeto de conexión del cliente.
    addr : tuple
        Dirección IP y puerto del cliente.
    """
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

# Función: start_server
def start_server():
    """
    Inicia el servidor TCP y espera conexiones de múltiples clientes.

    Flujo:
    -------
    1. Crea un socket TCP.
    2. Lo vincula al host y puerto definidos en config.json.
    3. Escucha nuevas conexiones y crea un hilo por cliente.
    """
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

# Punto de inicio
if __name__ == "__main__":
    start_server()
