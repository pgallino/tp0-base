import socket
import logging
import signal
import multiprocessing
import time
from common.logic import AgencyProcess
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
        self._client_processes = []  # Lista para almacenar los hilos de las agencias
        self.store_lock = multiprocessing.Lock()  # Lock para almacenar apuestas
        self.pipes = []  # Lista para almacenar los extremos de las pipes (canales)
        self.notif_queue = multiprocessing.Queue()
        self.conexiones_por_agencia = {}

        signal.signal(signal.SIGTERM, self._graceful_shutdown)

    def run(self):
        logging.info("Servidor corriendo...")
        try:
            while self._on:
                client_sock = self.__accept_new_connection()
                if client_sock:
                    # Crear y lanzar un AgencyProcess por cada conexión de cliente

                    # Crear una pipe para la comunicación
                    parent_conn, child_conn = multiprocessing.Pipe()

                    client_process = multiprocessing.Process(
                    target=AgencyProcess,
                    args=(client_sock, self.store_lock, self.notif_queue, child_conn)
                    )

                    client_process.start()
                    self._client_processes.append(client_process)
                    self.pipes.append(parent_conn)
                    self.agencias += 1

                # Si llegamos a la cantidad máxima de clientes, espero las notif y hago el sorteo
                if self.agencias == MAX_CLIENTS:
                    logging.info(f"Esperando a que los {MAX_CLIENTS} clientes notifiquen...")

                    self._receive_from_queue()  # Recibir los IDs de los procesos
                    self._realizar_sorteo_y_enviar_resultados()

        except KeyboardInterrupt:
            logging.info("Apagando servidor...")
            self._cleanup()
        finally:
            self._shutdown()

    def _receive_from_queue(self):
        """Recibe los IDs enviados por los procesos a través de la cola."""
        notificaciones = 0
        while notificaciones < MAX_CLIENTS:
            agency_id = self.notif_queue.get()  # Esperar a recibir el ID
            logging.info(f"Agencia {agency_id} registrada con éxito.")
            notificaciones += 1


    def _send_all(self, pipe, data):
        """Función que asegura que todos los datos se escriben en el pipe."""
        data_length = len(data)
        
        logging.info(f"Intentando enviar {data_length} bytes de datos...\n\n")
        
        # Continuar enviando los datos hasta que todo haya sido enviado
        try:
            pipe.send_bytes(data)  # Intentar enviar los datos restantes
        except Exception as e:
            logging.error(f"Error al enviar datos por el pipe: {e}")
        
        logging.info(f"Envío completado. \n\n")

    def _realizar_sorteo_y_enviar_resultados(self):
        """
        Realiza el sorteo y luego envía los resultados a todos los clientes.
        """
        ganadores = self._realizar_sorteo()
        for pipe in self.pipes:
            # Convertir los ganadores a una cadena
            serialized_data = str(ganadores)
            logging.info(f"data serializada de ganadores: {serialized_data}\n\n")
            
            data_length = f"{len(serialized_data):010d}"  # Convertir el tamaño a una cadena de 10 dígitos

            # Enviar primero el tamaño del mensaje
            logging.info(f"Enviando longitud de datos: {data_length}\n\n")
            self._send_all(pipe, data_length.encode('utf-8'))  # Enviar el tamaño como una cadena de longitud fija

            # Luego, enviar los datos
            logging.info(f"Enviando datos por el pipe...\n\n")
            self._send_all(pipe, serialized_data.encode('utf-8'))  # Asegurarse de que todos los datos sean enviados

            logging.info(f"Envio de datos completado: {data_length}\n\n")

        self._on = False

    def _realizar_sorteo(self):
        """
        Realiza el sorteo y guarda los ganadores por agencia.
        """

        ganadores_por_agencia = {}
        todas_las_apuestas = load_bets()
        for bet in todas_las_apuestas:
            if has_won(bet):
                if bet.agency not in ganadores_por_agencia:
                    ganadores_por_agencia[bet.agency] = []
                ganadores_por_agencia[bet.agency].append(bet.document)
        logging.info("Sorteo realizado exitosamente.")

        logging.info(f"Ganadores: {ganadores_por_agencia}\n\n")
        return ganadores_por_agencia

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

    def _shutdown(self):
        logging.info("Apagando el servidor...")
        for process in self._client_processes:
            process.join()
        self._server_socket.close()