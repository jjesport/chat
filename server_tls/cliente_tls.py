"""
Archivo: chat_client_basic.py

Descripción:
------------
Este archivo implementa un cliente de chat básico que se conecta al servidor
mediante sockets TCP convencionales (sin cifrado). Es una versión simple del
cliente principal que permite enviar y recibir mensajes en tiempo real.

Este cliente fue diseñado principalmente para:
 - Probar la comunicación base con el servidor.
 - Comprobar el correcto funcionamiento del manejo de hilos (threads).
 - Verificar la estabilidad del flujo de mensajes antes de agregar SSL/TLS.

Flujo de ejecución:
-------------------
1. Conecta al servidor definido por HOST y PORT.
2. Crea un hilo que recibe mensajes de manera constante.
3. Permite al usuario enviar mensajes manualmente desde la consola.
4. Finaliza la conexión cuando el usuario ingresa el comando `/salir`.
"""
import socket
import ssl
import threading

# Configuración del cliente
HOST = '127.0.0.1'            # Dirección IP del servidor (localhost)
PORT = 9000                   # Puerto de conexión del servidor

# Función: receive_messages
def receive_messages(sock):
     """
    - Recibe mensajes en un bucle constante hasta que la conexión se cierre.
    - Si se detecta un error o el servidor se desconecta, se muestra un aviso.
    """
    while True:
        try:
            msg = sock.recv(1024).decode('utf-8')
            if not msg:
                break
            print(msg)
        except:
            print("Conexión perdida con el servidor.")
            break
            
# Función principal: main
def main():
    """
    Inicia el cliente del chat y gestiona el envío y recepción de mensajes.

    Flujo:
    -------
    1. Crea un socket TCP.
    2. Se conecta al servidor en el host y puerto especificados.
    3. Inicia un hilo independiente para escuchar mensajes del servidor.
    4. Permite al usuario escribir mensajes desde la consola.
    5. Finaliza al escribir `/salir`, cerrando la conexión.
    """
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE  # desactiva verificación estricta (modo local)

    raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn = context.wrap_socket(raw_sock, server_hostname=HOST)
    conn.connect((HOST, PORT))

    # Inicia el hilo para recibir mensajes
    recv_thread = threading.Thread(target=receive_messages, args=(conn,))
    recv_thread.start()

    # Bucle principal para enviar mensajes
    while True:
        msg = input()
        if msg.lower() == "/salir":
            conn.close()
            break
        conn.sendall(msg.encode('utf-8'))

# Punto de inicio del programa
if __name__ == "__main__":
    main()
