#!/usr/bin/env python3
"""
distributed_api.py - API REST para replicación distribuida (CORREGIDO)
"""

import json
import os
import sys
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
from threading import Lock
import traceback

# Importar DB_LOCK del módulo db (lock compartido)
from db import (
    init_db, insert_message, get_messages_after, 
    get_full_history, get_max_lamport, get_last_message_position,
    DB_LOCK  # ✅ Usar el mismo lock compartido
)

# ------------------------------------------------
# CARGA CONFIG
# ------------------------------------------------
def load_config():
    if len(sys.argv) < 2:
        print("USO: python distributed_api.py config.json")
        sys.exit(1)

    config_path = sys.argv[1]
    if not os.path.exists(config_path):
        print(f"No existe config: {config_path}")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

config = load_config()

BASE_DIR = os.path.dirname(__file__)
db_path = os.path.join(BASE_DIR, config.get("db_file", "messages.db"))
db_conn = init_db(db_path)

SERVER_ID = config.get("server_id", "A")
REST_HOST = config.get("rest_host", "0.0.0.0")
REST_PORT = int(config.get("rest_port", 5000))
DEBUG = config.get("debug", False)

# ------------------------------------------------
# ESTADO LOCAL
# ------------------------------------------------
app = FastAPI()

lamport_lock = Lock()

# ✅ Inicializar lamport con el máximo de la BD
lamport = get_max_lamport(db_conn)
if DEBUG:
    print(f"[REST] Lamport inicial: {lamport}")

# ------------------------------------------------
# FUNCIONES LAMPORT
# ------------------------------------------------
def update_lamport(received_lamport: int):
    """Ajusta lamport = max(local, remoto) + 1."""
    global lamport
    with lamport_lock:
        lamport = max(lamport, int(received_lamport)) + 1
        return lamport

def increment_lamport():
    """Incrementa y retorna lamport local."""
    global lamport
    with lamport_lock:
        lamport += 1
        return lamport

# ------------------------------------------------
# ENDPOINTS
# ------------------------------------------------

@app.on_event("startup")
async def startup_event():
    """Se ejecuta cuando el servidor arranca."""
    print(f"[REST] ✓ API lista. Esperando conexiones...")


@app.get("/heartbeat")
def heartbeat():
    """Health check."""
    return {"status": "alive", "server_id": SERVER_ID}


@app.get("/history")
def history():
    """Devuelve el historial completo."""
    # DB_LOCK ya está dentro de get_full_history
    msgs = get_full_history(db_conn)

    return {"messages": [
        {
            "user": m[0],
            "message": m[1],
            "lamport": m[2],
            "server_id": m[3],
            "timestamp": m[4]
        }
        for m in msgs
    ]}


@app.get("/sync")
def sync(since_lamport: int = 0, since_server: str = ""):
    """
    Devuelve mensajes posteriores a (since_lamport, since_server).
    Si no se proporciona since_server, asume string vacío.
    """
    try:
        # Si no especifican posición, retornar todo
        if since_lamport == 0 and not since_server:
            msgs = get_full_history(db_conn)
        else:
            msgs = get_messages_after(db_conn, since_lamport, since_server)

        return {
            "messages": [
                {
                    "user": m[0],
                    "message": m[1],
                    "lamport": m[2],
                    "server_id": m[3],
                    "timestamp": m[4]
                }
                for m in msgs
            ]
        }
    except Exception:
        traceback.print_exc()
        return JSONResponse({"error": "sync failed"}, status_code=500)


@app.post("/push")
async def push_message(request: Request):
    """
    Recibe un mensaje remoto y lo almacena.
    """
    try:
        payload = await request.json()

        remote_l = int(payload["lamport"])
        user = payload["user"]
        msg = payload["message"]
        remote_server = payload["server_id"]
        ts = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()

        # Actualizar Lamport local
        local_l = update_lamport(remote_l)

        # Insertar en DB
        was_inserted = insert_message(db_conn, user, msg, remote_l, remote_server, ts)

        if DEBUG:
            print(f"[REST /push] ({remote_l},{remote_server}) inserted={was_inserted}")

        return {
            "status": "stored" if was_inserted else "duplicate",
            "server_id": SERVER_ID,
            "lamport_local": local_l,
            "inserted": was_inserted
        }
    except Exception:
        if DEBUG:
            traceback.print_exc()
        return JSONResponse({"error": "push failed"}, status_code=500)

# ------------------------------------------------
# MAIN
# ------------------------------------------------

if __name__ == "__main__":
    print(f"[REST] ========================================")
    print(f"[REST] Iniciando distributed_api")
    print(f"[REST] Server ID: {SERVER_ID}")
    print(f"[REST] Base de datos: {db_path}")
    print(f"[REST] Escuchando en {REST_HOST}:{REST_PORT}")
    print(f"[REST] Debug: {DEBUG}")
    print(f"[REST] ========================================")
    
    # Configurar uvicorn con logs apropiados
    import logging
    
    log_level = "debug" if DEBUG else "info"
    
    uvicorn.run(
        app, 
        host=REST_HOST, 
        port=REST_PORT,
        log_level=log_level,
        access_log=DEBUG  # Solo mostrar access logs si está en debug
    )