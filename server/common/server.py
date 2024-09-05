import socket
import logging
import signal
import time
from common.socket_handler import recv_msg, send_msg
from common.logic import procesar_mensaje
from common.messages import (
    decode_message,
    encode_confirmation_message,
    encode_winners_message
)
from common.utils import load_bets, has_won, Bet, store_bets

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
        self.notificaciones = 0
        self.ganadores_por_agencia = {}
        self.sorteo_realizado = False
        self.conexiones_por_agencia = {}

        signal.signal(signal.SIGTERM, self._graceful_shutdown)

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """

        # Iniciar el temporizador
        start_time = time.time()

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
        elapsed_time = time.time() - start_time
        logging.info(f"TIEMPO FINAL {elapsed_time:.2f} segundos")
        

    def __handle_client_connection(self, client_sock):
        """
        Manage communication with an existing client, keeping the connection open.
        """
        try:
            data = recv_msg(client_sock)
            # addr = client_sock.getpeername()

            # Procesar el mensaje recibido
            response = self._procesar_mensaje(data, client_sock )

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
        for client_sock in self.conexiones_por_agencia.values():
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
    
    def _realizar_sorteo(self):
        """
        Realiza el sorteo cuando todas las agencias han notificado.
        """

        # Cargar todas las apuestas
        todas_las_apuestas = load_bets()

        # Para cada apuesta, verificar si gano y almacenarla por agencia
        for bet in todas_las_apuestas:
            if has_won(bet):
                if bet.agency not in self.ganadores_por_agencia:
                    self.ganadores_por_agencia[bet.agency] = []
                self.ganadores_por_agencia[bet.agency].append(bet.document)
        
        self.sorteo_realizado = True
        logging.info("action: sorteo | result: success")

    def _comunicar_resultados(self):
        """
        Comunica los resultados del sorteo a las agencias que han participado.
        """

        logging.info(f"GANADORES POR AGENCIA: {self.ganadores_por_agencia}")
        for agency_id, conn in self.conexiones_por_agencia.items():
            ganadores = self.ganadores_por_agencia.get(agency_id, [])
            response = encode_winners_message(ganadores)
            
            # Enviar los resultados a la agencia
            send_msg(conn, response)
            logging.info(f"action: comunicar_ganadores | result: success | agency_id: {agency_id} | cant_ganadores: {len(ganadores)}")
        self._on = False

    def _procesar_mensaje(self, data, conn):
        """
        Procesa el mensaje recibido, maneja la lógica de negocio y retorna respuesta.
        """

        try:
            decoded_message = decode_message(data)

            if isinstance(decoded_message, list) and all(isinstance(bet, Bet) for bet in decoded_message):
                # Manejo de mensaje de tipo apuesta
                store_bets(decoded_message)  # Almacena las apuestas recibidas
                response = encode_confirmation_message(success=True)
                logging.info(f"action: batch_almacenado | result: success")
                return response

            elif decoded_message.get("tipo") == "finalizacion":
                # Manejo de mensaje de tipo finalización
                agency_id = decoded_message["agency_id"]
                self.conexiones_por_agencia[agency_id] = conn  # Guardar la conexión de la agencia
                self._client_sockets.remove(conn)
                self.notificaciones += 1
                logging.info(f"action: procesar_finalizacion | result: success | agency_id: {agency_id}")

                # Verificar si todas las agencias han notificado para realizar el sorteo
                if self.notificaciones == MAX_CLIENTS and not self.sorteo_realizado:
                    self._realizar_sorteo()
                    self._comunicar_resultados()

                return

            elif decoded_message.get("tipo") == "consulta":
                # Manejo de mensaje de tipo consulta de ganadores
                agency_id = decoded_message["agency_id"]
                logging.info(f"action: procesar_consulta | result: success | agency_id: {agency_id}")

                # Solo responder si el sorteo ya ha sido realizado
                if not self.sorteo_realizado:
                    return
                else:
                    ganadores = self.ganadores_por_agencia.get(agency_id, [])
                    response = encode_winners_message(ganadores)
            
                    # Enviar los resultados a la agencia
                    return response
            
            else:
                # Tipo de mensaje desconocido
                logging.error("action: procesar_mensaje | result: fail | error: Tipo de mensaje desconocido")
                response = encode_confirmation_message(success=False)
                return response

        except Exception as e:
            logging.error(f"action: procesar_mensaje | result: fail | error: {e}")
            response = encode_confirmation_message(success=False)
            return response

