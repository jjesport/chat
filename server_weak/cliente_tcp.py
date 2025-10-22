import socket
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
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((HOST, PORT))

    recv_thread = threading.Thread(target=receive_messages, args=(client,))
    recv_thread.start()

    while True:
        msg = input()
        if msg.lower() == "/salir":
            client.close()
            break
        client.sendall(msg.encode('utf-8'))

if __name__ == "__main__":
    main()
