#!/usr/bin/env python3
"""
server_tls.py - Servidor TLS con sincronización distribuida
"""
import socket
import ssl
import threading
import json
from datetime import datetime, timezone
import os
import time
import argparse
import requests
import traceback
import sys

from db import (
    init_db, insert_message, get_max_lamport, 
    get_last_message_position, DB_LOCK
)

# --- Configuración ---
def load_config():
    parser = argparse.ArgumentParser(description="Servidor TLS distribuido")
    parser.add_argument("--config", type=str, required=True,
                        help="Ruta al archivo de configuración JSON")
    args = parser.parse_args()

    config_path = args.config
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"El archivo de configuración '{config_path}' no existe")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    return config

config = load_config()
BASE_DIR = os.path.dirname(__file__)
db_path = os.path.join(BASE_DIR, config.get("db_file", "messages.db"))
db_conn = init_db(db_path)

HOST = config.get("host", "0.0.0.0")
PORT = int(config.get("port", 9000))
SERVER_ID = config.get("server_id", "S")
TLS_CERT = config.get("tls_cert", "server.crt")
TLS_KEY = config.get("tls_key", "server.key")
HEARTBEAT_INTERVAL = float(config.get("heartbeat_interval", 2))
SYNC_INTERVAL = float(config.get("sync_interval", 3))

# Control de logs (configurable)
DEBUG = config.get("debug", False)  # False = logs mínimos
VERBOSE_SYNC = config.get("verbose_sync", False)
VERBOSE_PUSH = config.get("verbose_push", False)
VERBOSE_HB = config.get("verbose_heartbeat", False)

# --- Estado ---
clients = {}
clients_lock = threading.Lock()
lamport_lock = threading.Lock()
peer_alive_lock = threading.Lock()
peer_alive = True

# ✅ Inicializar lamport con el máximo de la BD
lamport = get_max_lamport(db_conn)
# No imprimir aquí, se imprimirá en start_server()

# --- Lamport Clock ---
def increment_lamport():
    global lamport
    with lamport_lock:
        lamport += 1
        return lamport

def update_lamport_on_receive(received_lamport):
    global lamport
    with lamport_lock:
        lamport = max(lamport, int(received_lamport)) + 1
        return lamport

# --- Broadcast ---
def broadcast(payload_dict, sender_socket=None):
    """
    Envía payload a todos los clientes excepto sender_socket.
    """
    data = json.dumps(payload_dict) + "\n"
    encoded = data.encode("utf-8")
    to_remove = []
    
    with clients_lock:
        num_clients = len(clients)
        if DEBUG:
            print(f"[BROADCAST] Enviando a {num_clients} clientes (excluye sender={sender_socket is not None})")
        
        for client in list(clients.keys()):
            if client == sender_socket:
                continue
            try:
                client.sendall(encoded)
                if DEBUG:
                    print(f"[BROADCAST] ✓ Enviado a {clients.get(client, 'unknown')}")
            except Exception as e:
                if DEBUG:
                    print(f"[BROADCAST] ✗ Error enviando a {clients.get(client, 'unknown')}: {e}")
                try:
                    client.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                try:
                    client.close()
                except Exception:
                    pass
                to_remove.append(client)
        for r in to_remove:
            clients.pop(r, None)

# --- Cliente TLS ---
def handle_client(conn, addr):
    buffer = ""
    try:
        conn.sendall(b"Ingresa tu nickname:\n")
        nickname = conn.recv(1024).decode('utf-8').strip() or "anon"

        with clients_lock:
            clients[conn] = nickname

        print(f"[{nickname}] conectado desde {addr}")

        join_payload = {
            "type": "system",
            "text": f"{nickname} se ha unido al chat.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "server_id": SERVER_ID
        }
        broadcast(join_payload)

        while True:
            data = conn.recv(4096)
            if not data:
                break
            buffer += data.decode('utf-8', errors='replace')
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                message = line.strip()
                if not message:
                    continue

                # Comando /users
                if message.lower() == "/users":
                    with clients_lock:
                        users_list = ", ".join(clients.values())
                    try:
                        conn.sendall(f"Usuarios conectados: {users_list}\n".encode('utf-8'))
                    except Exception:
                        pass
                    continue

                # Mensaje normal
                my_l = increment_lamport()
                ts = datetime.now(timezone.utc).isoformat()
                
                try:
                    insert_message(db_conn, nickname, message, my_l, SERVER_ID, ts)
                except Exception:
                    print("[DB ERROR]:", traceback.format_exc())

                payload = {
                    "type": "message",
                    "user": nickname,
                    "message": message,
                    "lamport": my_l,
                    "server_id": SERVER_ID,
                    "timestamp": ts
                }
                
                # Broadcast a clientes locales
                broadcast(payload, sender_socket=conn)
                
                # Push al peer
                push_to_peer(payload)
                
                if DEBUG:
                    print(f"[{nickname}] ({my_l},{SERVER_ID}) {message}")
                else:
                    print(f"[{nickname}]: {message}")

    except ConnectionResetError:
        print(f"[Cliente {addr} cerró la conexión]")
    except Exception:
        print("[CLIENT ERROR]:", traceback.format_exc())
    finally:
        with clients_lock:
            left_nick = clients.pop(conn, None)
        if left_nick:
            leave_payload = {
                "type": "system",
                "text": f"{left_nick} salió del chat.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "server_id": SERVER_ID
            }
            broadcast(leave_payload)
            print(f"[{left_nick}] desconectado.")
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

# --- Push to peer ---
def push_to_peer(payload):
    global peer_alive
    peer_url = config.get("peer_url")
    if not peer_url:
        print("[PUSH] No hay peer_url configurado.")
        return

    with peer_alive_lock:
        alive = peer_alive

    if not alive:
        print("[PUSH] Peer marcado como no-alive, saltando push.")
        return

    try:
        url = f"{peer_url}/push"
        print(f"[PUSH] POST -> {url} lamport={payload.get('lamport')} server_id={payload.get('server_id')}")
        resp = requests.post(url, json=payload, timeout=2)
        print(f"[PUSH] Respuesta: status={resp.status_code} body={resp.json()}")
        
        if resp.status_code != 200:
            with peer_alive_lock:
                peer_alive = False
            print(f"[PUSH] ⚠️  Peer respondió {resp.status_code}, marcado como no-alive")
    except Exception as e:
        with peer_alive_lock:
            peer_alive = False
        print("[PUSH] ❌ Error:", repr(e))

# --- Heartbeat ---
def heartbeat_monitor():
    global peer_alive
    peer_url = config.get("peer_url")
    if not peer_url:
        return

    print(f"[HB] Monitor iniciado. Chequeando: {peer_url}/heartbeat")
    
    # Esperar 3 segundos antes del primer check
    print("[HB] Esperando 3s para que el peer arranque...")
    time.sleep(3)
    print("[HB] Comenzando monitoreo del peer")
    
    while True:
        try:
            url = f"{peer_url}/heartbeat"
            print(f"[HB] → GET {url}") if DEBUG else None
            r = requests.get(url, timeout=2)
            print(f"[HB] ← Status: {r.status_code}") if DEBUG else None
            
            with peer_alive_lock:
                was_dead = not peer_alive
                if r.status_code == 200:
                    peer_alive = True
                    if was_dead:
                        print("[HB] ✓ Peer recuperado")
                else:
                    peer_alive = False
                    if not was_dead or DEBUG:
                        print(f"[HB] ⚠️  Peer caído (status {r.status_code})")
        except requests.exceptions.ConnectionError as e:
            with peer_alive_lock:
                was_alive = peer_alive
                peer_alive = False
                if was_alive or DEBUG:
                    print(f"[HB] ⚠️  Peer caído (ConnectionError: {repr(e)[:80]})")
        except requests.exceptions.Timeout:
            with peer_alive_lock:
                was_alive = peer_alive
                peer_alive = False
                if was_alive or DEBUG:
                    print("[HB] ⚠️  Peer caído (Timeout)")
        except Exception as e:
            with peer_alive_lock:
                was_alive = peer_alive
                peer_alive = False
                if was_alive or DEBUG:
                    print(f"[HB] ⚠️  Peer caído (Error: {repr(e)[:80]})")
        
        time.sleep(HEARTBEAT_INTERVAL)

# --- Sync ---
def sync_with_peer():
    global peer_alive
    peer_url = config.get("peer_url")
    if not peer_url:
        return

    if VERBOSE_SYNC or DEBUG:
        print(f"[SYNC] Thread iniciado. peer_url={peer_url}")
    
    # Esperar 5 segundos antes del primer sync
    print("[SYNC] Esperando 5s antes del primer sync...")
    time.sleep(5)
    print("[SYNC] Comenzando sincronización periódica")
    
    while True:
        try:
            with peer_alive_lock:
                alive = peer_alive
            
            if not alive:
                time.sleep(SYNC_INTERVAL)
                continue

            # Obtener última posición
            last_lamport, last_server = get_last_message_position(db_conn)
            
            url = f"{peer_url}/sync?since_lamport={last_lamport}&since_server={last_server}"
            if VERBOSE_SYNC:
                print(f"[SYNC] Consultando desde ({last_lamport}, '{last_server}')")
            
            r = requests.get(url, timeout=3)

            if r.status_code != 200:
                with peer_alive_lock:
                    peer_alive = False
                print(f"[SYNC] ⚠️  Error {r.status_code}")
                time.sleep(SYNC_INTERVAL)
                continue

            data = r.json()
            msgs = data.get("messages", [])
            
            if msgs:
                print(f"[SYNC] ← Recibidos {len(msgs)} mensajes")

            for m in msgs:
                if isinstance(m, dict):
                    user = m.get("user")
                    text = m.get("message")
                    remote_l = m.get("lamport")
                    remote_server = m.get("server_id")
                    ts = m.get("timestamp")
                else:
                    continue

                if VERBOSE_SYNC:
                    print(f"[SYNC] Procesando ({remote_l}, '{remote_server}'): {text[:40]}")
                
                update_lamport_on_receive(remote_l)
                was_inserted = insert_message(db_conn, user, text, remote_l, remote_server, ts)
                
                if was_inserted:
                    broadcast({
                        "type": "message",
                        "user": user,
                        "message": text,
                        "lamport": remote_l,
                        "server_id": remote_server,
                        "timestamp": ts
                    })
                    print(f"[SYNC] ✓ [{user}] ({remote_l},{remote_server}): {text}")
                elif VERBOSE_SYNC:
                    print(f"[SYNC] ⊘ Duplicado ({remote_l},{remote_server})")

        except Exception as e:
            if DEBUG:
                print("[SYNC] Error:", repr(e))
                traceback.print_exc()
            with peer_alive_lock:
                peer_alive = False

        time.sleep(SYNC_INTERVAL)

# --- Start server ---
def start_server():
    print(f"[TLS] ========================================")
    print(f"[TLS] Iniciando servidor TLS")
    print(f"[TLS] Server ID: {SERVER_ID}")
    print(f"[TLS] Base de datos: {db_path}")
    print(f"[TLS] Lamport inicial: {lamport}")
    print(f"[TLS] Escuchando en {HOST}:{PORT}")
    print(f"[TLS] Peer URL: {config.get('peer_url', 'No configurado')}")
    print(f"[TLS] Debug: {DEBUG}")
    print(f"[TLS] ========================================")
    
    # Threads de background
    print("[TLS] Iniciando threads de sincronización...")
    t_hb = threading.Thread(target=heartbeat_monitor, daemon=True)
    t_hb.start()
    print("[TLS] ✓ Heartbeat monitor iniciado")
    
    t_sync = threading.Thread(target=sync_with_peer, daemon=True)
    t_sync.start()
    print("[TLS] ✓ Sync monitor iniciado")

    # TLS
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=TLS_CERT, keyfile=TLS_KEY)

    bind_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    bind_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    bind_socket.bind((HOST, PORT))
    bind_socket.listen(5)

    print(f"[TLS] ✓ Listo para aceptar conexiones TLS\n")

    try:
        while True:
            try:
                raw_conn, addr = bind_socket.accept()
                try:
                    tls_conn = context.wrap_socket(raw_conn, server_side=True)
                except Exception:
                    try:
                        raw_conn.close()
                    except:
                        pass
                    continue

                t = threading.Thread(target=handle_client, args=(tls_conn, addr), daemon=True)
                t.start()

            except KeyboardInterrupt:
                print("\n[SERVER] Cerrando...")
                with clients_lock:
                    for c in list(clients.keys()):
                        try:
                            c.close()
                        except:
                            pass
                    clients.clear()
                bind_socket.close()
                sys.exit(0)
            except Exception:
                print("[ACCEPT ERROR]:", traceback.format_exc())
    except KeyboardInterrupt:
        bind_socket.close()
        sys.exit(0)

if __name__ == "__main__":
    start_server()