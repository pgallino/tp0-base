import socket
import logging
import signal
import threading
import time
from common.logic import AgencyThread
from common.messages import (
    encode_winners_message
)
from common.utils import load_bets, has_won

MAX_CLIENTS = 5

class Server:
    def __init__(self, port, listen_backlog):
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self._on = True
        self.agencias = 0
        self._client_threads = []  # Lista para almacenar los hilos de las agencias
        self.store_lock = threading.Lock()  # Lock para almacenar apuestas
        self.barrier = threading.Barrier(MAX_CLIENTS + 1)  # Barrera para sincronizar los hilos de agencias y el hilo principal
        self.sorteo_realizado = False
        self.ganadores_por_agencia = {}
        self.conexiones_por_agencia = {}
        self.conexiones_lock = threading.Lock()

        signal.signal(signal.SIGTERM, self._graceful_shutdown)

    def run(self):
        logging.info("Servidor corriendo...")
        try:
            while self._on:
                client_sock = self.__accept_new_connection()
                if client_sock:
                    # Crear y lanzar un AgencyThread por cada conexión de cliente
                    client_thread = AgencyThread(
                        agency_socket=client_sock,
                        store_lock=self.store_lock,
                        barrier=self.barrier,
                        conexiones_por_agencia=self.conexiones_por_agencia,
                        conexiones_lock=self.conexiones_lock
                    )
                    client_thread.start()
                    self._client_threads.append(client_thread)

                # Si llegamos a la cantidad máxima de clientes, el hilo principal espera en la barrera
                if len(self._client_threads) == MAX_CLIENTS:
                    logging.info(f"Esperando a que los {MAX_CLIENTS} clientes notifiquen...")
                    self.barrier.wait()  # Hilo principal espera hasta que todos los hilos lleguen aquí
                    logging.info(f"SALI DE LA BARRERA...")
                    time.sleep(5)
                    self._realizar_sorteo_y_enviar_resultados()

        except KeyboardInterrupt:
            logging.info("Apagando servidor...")
            self._cleanup()

    def _realizar_sorteo_y_enviar_resultados(self):
        """
        Realiza el sorteo y luego envía los resultados a todos los clientes.
        """
        self._realizar_sorteo()
        for agency_id, conn in self.conexiones_por_agencia.items():
            self._enviar_resultados(conn, agency_id)
        self._on = False

    def _realizar_sorteo(self):
        """
        Realiza el sorteo y guarda los ganadores por agencia.
        """
        todas_las_apuestas = load_bets()
        for bet in todas_las_apuestas:
            if has_won(bet):
                if bet.agency not in self.ganadores_por_agencia:
                    self.ganadores_por_agencia[bet.agency] = []
                self.ganadores_por_agencia[bet.agency].append(bet.document)
        logging.info("Sorteo realizado exitosamente.")
        self.sorteo_realizado = True

    def _enviar_resultados(self, client_sock, agency_id):
        """
        Envía los resultados del sorteo al cliente.
        """
        ganadores = self.ganadores_por_agencia.get(agency_id, [])
        response = encode_winners_message(ganadores)
        client_sock.send(response)
        logging.info(f"Resultados enviados a la agencia {agency_id}.")

    def _graceful_shutdown(self, signum, frame):
        logging.info("Apagando servidor de manera controlada...")
        self._on = False
        self._cleanup()

    def _cleanup(self):
        logging.info("Cerrando todas las conexiones...")
        for thread in self._client_threads:
            thread.join()  # Asegurarse de que todos los hilos de los clientes terminen
        self._server_socket.close()

    def __accept_new_connection(self):
        client_sock, addr = self._server_socket.accept()
        logging.info(f"Conexión aceptada desde {addr[0]}:{addr[1]}")
        return client_sock