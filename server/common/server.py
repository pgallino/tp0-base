import socket
import logging
import signal
from common.socket_handler import recv_msg, send_msg
from common.logic import procesar_mensaje

MAX_CLIENTS = 5

class Server:
    def __init__(self, port, listen_backlog):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self._on = True
        self.agencias = 0
        self._client_sockets = [] # almaceno conexiones

        signal.signal(signal.SIGTERM, self._graceful_shutdown)

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """

        while self._on:
            # Aceptar nuevas conexiones si hay menos de MAX_CLIENTS
            if self.agencias < MAX_CLIENTS:
                client_sock = self.__accept_new_connection()

                if client_sock:
                    # Agregar la nueva conexión a la lista de conexiones activas
                    self._client_sockets.append(client_sock)
                    self.agencias += 1

            # Manejar los clientes ya conectados
            for client_sock in list(self._client_sockets):  # Usamos list para modificar la lista mientras iteramos
                self.__handle_client_connection(client_sock)

        # Al salir del bucle principal, cerrar todas las conexiones activas y el socket del servidor
        self._cleanup()

    def __handle_client_connection(self, client_sock):
        """
        Manage communication with an existing client, keeping the connection open.
        """
        try:
            data = recv_msg(client_sock)
            addr = client_sock.getpeername()

            # Procesar el mensaje recibido
            response = procesar_mensaje(data)

            # Enviar una respuesta
            if response:
                send_msg(client_sock, response)
        except Exception as e:
            # En caso de error, cerrar la conexión con el cliente
            logging.error(f"Error en la conexión con el cliente {client_sock.getpeername()[0]}: {e}")
            self._client_sockets.remove(client_sock)
            client_sock.close()
            if len(self._client_sockets) <= 0:
                self._on = False

    def _graceful_shutdown(self, signum, frame):
        """
        Apagar el servidor de manera controlada.
        """
        self._on = False

    def _cleanup(self):
        """
        Limpiar: cerrar todas las conexiones de clientes y el socket del servidor.
        """
        logging.info("Cerrando todas las conexiones...")
        for client_sock in self._client_sockets:
            client_sock.close()
        self._server_socket.close()

    def __accept_new_connection(self):
        """
        Accept new client connections and return the client socket.

        no bloqueo hasta encontrar una nueva
        """
        client_sock, addr = self._server_socket.accept()

        logging.info(f'Conexión aceptada de {addr[0]}:{addr[1]}')
        return client_sock