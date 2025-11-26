import sqlite3
from datetime import datetime, timezone
from threading import Lock

# Lock global único para toda la aplicación
DB_LOCK = Lock()

def init_db(db_path):
    """
    Inicializa la BD y retorna una conexión global.
    """
    conn = sqlite3.connect(
        db_path,
        check_same_thread=False,
        timeout=30
    )

    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass

    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            message TEXT,
            lamport INTEGER,
            server_id TEXT,
            timestamp TEXT,
            UNIQUE(lamport, server_id)
        )
    """)
    conn.commit()
    cur.close()
    return conn


def insert_message(conn, user, message, lamport, server_id, ts=None):
    """Inserta un mensaje si no existe ya."""
    if ts is None:
        ts = datetime.now(timezone.utc).isoformat()

    with DB_LOCK:
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT OR IGNORE INTO messages (user, message, lamport, server_id, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (user, message, lamport, server_id, ts))
            conn.commit()
            # Retorna True si insertó, False si era duplicado
            return cur.rowcount > 0
        except Exception as e:
            print("[DB ERROR insert_message]:", e)
            return False
        finally:
            try:
                cur.close()
            except:
                pass


def get_full_history(conn):
    """Obtiene todos los mensajes ordenados globalmente."""
    with DB_LOCK:
        cur = conn.cursor()
        cur.execute("""
            SELECT user, message, lamport, server_id, timestamp
            FROM messages
            ORDER BY lamport ASC, server_id ASC
        """)
        rows = cur.fetchall()
        cur.close()
        return rows


def get_max_lamport(conn):
    """Retorna lamport máximo existente en la BD."""
    with DB_LOCK:
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(MAX(lamport), 0) FROM messages")
        val = cur.fetchone()[0]
        cur.close()
        return val


def get_last_message_position(conn):
    """
    Retorna (lamport, server_id) del último mensaje en la BD.
    Útil para saber desde dónde sincronizar.
    """
    with DB_LOCK:
        cur = conn.cursor()
        cur.execute("""
            SELECT lamport, server_id
            FROM messages
            ORDER BY lamport DESC, server_id DESC
            LIMIT 1
        """)
        row = cur.fetchone()
        cur.close()
        if row:
            return (row[0], row[1])
        return (0, "")


def get_messages_after(conn, lamport_value, server_id_value):
    """
    Obtiene mensajes posteriores a una posición (lamport, server_id).
    """
    with DB_LOCK:
        cur = conn.cursor()
        cur.execute("""
            SELECT user, message, lamport, server_id, timestamp
            FROM messages
            WHERE lamport > ?
               OR (lamport = ? AND server_id > ?)
            ORDER BY lamport ASC, server_id ASC
        """, (lamport_value, lamport_value, server_id_value))
        rows = cur.fetchall()
        cur.close()
        return rows