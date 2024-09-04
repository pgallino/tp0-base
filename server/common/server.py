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

        signal.signal(signal.SIGTERM, self._graceful_shutdown)

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """

        while self._on:
            try:
                client_sock = self.__accept_new_connection()
                self.__handle_client_connection(client_sock)
            except OSError as e:
                if not self._on:
                    break
                else:
                    logging.error(f"action: main loop | result: fail | error: {e}")
                    break
        if self._server_socket.fileno() != -1:
            self._server_socket.close()
        logging.info('action: exit | result: success')

    def __handle_client_connection(self, client_sock):
        """
        Lee un mensaje de un socket de cliente específico y cierra el socket.

        Si surge un problema en la comunicación con el cliente, el socket del cliente
        también se cerrará.
        """
        try:
            # Recibir mensaje
            data = recv_msg(client_sock)
            addr = client_sock.getpeername()
            logging.info(f'action: receive_message | result: success | ip: {addr[0]}')

            # Procesar el mensaje recibido
            response = procesar_mensaje(data)

            # Enviar una respuesta (confirmación)
            if response: send_msg(client_sock, response)

        except Exception as e:
            logging.error(f"action: handle_client_connection | result: fail | error: {e}")
        finally:
            if client_sock.fileno() != -1:
                client_sock.close()
            # Le pongo el tope para que cierre después de atender a los 5 clientes
            # TODO hacer configurable la cantidad de clientes
            if self.agencias == MAX_CLIENTS:
                self._on = False
            logging.info(f'action: close_connection | result: success | ip: {addr[0]}')

    def __accept_new_connection(self):
        """
        Accept new connections

        Function blocks until a connection to a client is made.
        Then connection created is printed and returned
        """

        # Connection arrived
        logging.info('action: accept_connections | result: in_progress')
        c, addr = self._server_socket.accept()
        logging.info(f'action: accept_connections | result: success | ip: {addr[0]}')
        self.agencias += 1
        return c

    # agrego el handler de la signal
    def _graceful_shutdown(self, signum, frame):

        self._on = False