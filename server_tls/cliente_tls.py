import socket
import ssl
import threading

HOST = '127.0.0.1'
PORT = 9000

def receive_messages(sock):
    while True:
        try:
            msg = sock.recv(1024).decode('utf-8')
            if not msg:
                break
            print(msg)
        except:
            print("Conexión perdida con el servidor.")
            break

def main():
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE  # desactiva verificación estricta (modo local)

    raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn = context.wrap_socket(raw_sock, server_hostname=HOST)
    conn.connect((HOST, PORT))

    recv_thread = threading.Thread(target=receive_messages, args=(conn,))
    recv_thread.start()

    while True:
        msg = input()
        if msg.lower() == "/salir":
            conn.close()
            break
        conn.sendall(msg.encode('utf-8'))

if __name__ == "__main__":
    main()
