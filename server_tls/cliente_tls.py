import socket
import ssl
import threading
import sys
import os

HOST = "127.0.0.1"
PORT = 9000

def receive_messages(sock):
    """
    Hilo que escucha mensajes del servidor.
    Sale automáticamente cuando la conexión se cierra.
    """
    buffer = ""
    try:
        while True:
            data = sock.recv(4096)
            if not data:
                print("🔌 Servidor cerró la conexión.")
                break

            text = data.decode("utf-8", errors="replace")
            buffer += text

            # Procesado por líneas (server_tls.py envía JSON + \n)
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if line:
                    print(line)

    except Exception:
        print("⚠ Error recibiendo mensajes.")
    finally:
        try:
            sock.close()
        except:
            pass
        os._exit(0)  # termina todo el programa inmediatamente


def main():
    print("🔐 Cliente TLS conectado a", HOST, PORT)
    print("Escribe tu nickname y luego mensajes. Usa /salir para desconectar.\n")

    # Contexto TLS (modo desarrollo)
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE  # no validar cert local

    # Crear socket y envolverlo en TLS
    raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn = context.wrap_socket(raw_sock, server_hostname=HOST)

    try:
        conn.connect((HOST, PORT))
    except Exception as e:
        print("❌ No se pudo conectar al servidor TLS:", e)
        return

    # Hilo receptor
    recv_thread = threading.Thread(target=receive_messages, args=(conn,), daemon=True)
    recv_thread.start()

    # Loop principal de envío
    try:
        while True:
            msg = input()
            if msg.lower() == "/salir":
                print("Cerrando conexión...")
                try: conn.shutdown(socket.SHUT_RDWR)
                except: pass
                conn.close()
                break

            # Asegurar newline (server procesa por líneas)
            conn.sendall((msg + "\n").encode("utf-8"))

    except KeyboardInterrupt:
        print("\nInterrumpido por usuario.")
        try: conn.close()
        except: pass


if __name__ == "__main__":
    main()
