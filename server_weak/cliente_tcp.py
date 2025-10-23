# ===============================================================
#  CLIENTE TCP SIMPLE PARA CHAT DISTRIBUIDO
#  ---------------------------------------------------------------
#  Autor: [Tu nombre]
#  Descripción:
#      Este cliente se conecta a un servidor de chat basado en TCP,
#      permitiendo enviar y recibir mensajes en tiempo real.
# ===============================================================
import socket
import threading

# Configuración de conexión
HOST = '127.0.0.1'            # Dirección IP del servidor (localhost)
PORT = 9000                   # Puerto de escucha del servidor

# ===============================================================
#  FUNCIÓN: receive_messages
# ===============================================================
# Descripción:
#   Escucha continuamente los mensajes enviados por el servidor
#   y los muestra por consola. Se ejecuta en un hilo independiente
#   para permitir recibir mientras se escribe.
#
# Parámetros:
#   sock : socket del cliente conectado al servidor.
# ===============================================================
def receive_messages(sock):
    while True:
        try:
            # Recibe datos desde el servidor (máximo 1024 bytes)
            msg = sock.recv(1024).decode('utf-8')
            # Si el servidor cierra la conexión, se rompe el bucle
            if not msg:
                break
            # Muestra el mensaje recibido
            print(msg)
        except:
            # Error de conexión (el servidor se desconectó o hubo fallo)
            print("Conexión perdida con el servidor.")
            break
# ===============================================================
#  FUNCIÓN PRINCIPAL: main
# ===============================================================
# Descripción:
#   Crea un socket cliente, se conecta al servidor TCP,
#   lanza un hilo para escuchar mensajes y permite enviar
#   texto en tiempo real desde la consola.
# ===============================================================
def main():
    # 1️ Crear el socket del cliente
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 2️ Establecer la conexión con el servidor
    client.connect((HOST, PORT))

    # 3️ Iniciar hilo para escuchar mensajes del servidor
    recv_thread = threading.Thread(target=receive_messages, args=(client,))
    recv_thread.start()

    # 4️ Bucle principal de envío de mensajes
    while True:
        msg = input()                    # Espera entrada del usuario
        # Comando especial para cerrar la conexión
        if msg.lower() == "/salir":
            client.close()
            break
        # Envía el mensaje al servidor codificado en UTF-8
        client.sendall(msg.encode('utf-8'))
#  PUNTO DE ENTRADA DEL SCRIPT
if __name__ == "__main__":
    main()
