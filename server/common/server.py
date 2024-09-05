import socket
import logging
import signal
import time
import multiprocessing
from common.client_process import AgencyProcess
from common.utils import load_bets, has_won

MAX_CLIENTS = 5

class Server:
    def __init__(self, port, listen_backlog):
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self._on = True
        self.agencias = 0 # conteo de agencias registradas
        self._client_processes = []  # Lista para almacenar los procesos de las agencias
        self.store_lock = multiprocessing.Lock()  # Lock para almacenar apuestas
        self.pipes = []  # Lista para almacenar los extremos de las pipes (canales)
        self.notif_queue = multiprocessing.Queue() # cola para 
        self.conexiones_por_agencia = {}

        # Catcheo de signal
        signal.signal(signal.SIGTERM, self._graceful_shutdown)

    def run(self):
        start_time = time.time()
        logging.info("Servidor corriendo...")
        try:
            while self._on:
                client_sock = self.__accept_new_connection()

                # Crear y lanzar un AgencyProcess por cada conexión de cliente
                if client_sock:

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

                # Si llego a la cantidad máxima de clientes, espero las notificaciones de finalización y hago el sorteo
                if self.agencias >= MAX_CLIENTS:

                    self._receive_from_queue()  # Recibir las notificaciones de los procesos

                    ganadores = self._realizar_sorteo() # Una vez recibidos las notificaciones realizo el sorteo
                    
                    self._registrar_ganadores(ganadores) # Comunico a los procesos agency los ganadores

        finally:
            self._shutdown()
            elapsed_time = time.time() - start_time
            logging.info(f"TIEMPO FINAL: {elapsed_time:.2f} segundos")


    def __accept_new_connection(self):
        """Acepta conexiones entrantes"""

        client_sock, addr = self._server_socket.accept()
        logging.info(f"Conexión aceptada desde {addr[0]}:{addr[1]}")
        return client_sock

    def _receive_from_queue(self):
        """Recibe la notificación de las agencias por la cola bloqueante"""

        logging.info(f"action: waiting notif | result: success | msg: esperando notificaciones")
        notificaciones = 0
        while notificaciones < MAX_CLIENTS:
            agency_id = self.notif_queue.get()  # Esperar a recibir notificacion
            logging.info(f"action: notified | result: success | msg: {agency_id} me notificó que terminó.")
            notificaciones += 1

    def _realizar_sorteo(self):
        """
        Realiza el sorteo y guarda los ganadores por agencia.
        """

        logging.info("action: sorteo | result: in_progress...")

        ganadores_por_agencia = {}

        # no uso mutex porque solo ingresa este proceso luego de que ya haya sido usado por todos (podria usar el mismo lock por seguridad)
        apuestas_totales = load_bets()
        for bet in apuestas_totales:
            if has_won(bet):
                if bet.agency not in ganadores_por_agencia:
                    ganadores_por_agencia[bet.agency] = []
                ganadores_por_agencia[bet.agency].append(bet.document)

        logging.info(f"action: sorteo | result: succes | ganadores: {ganadores_por_agencia}")

        return ganadores_por_agencia

    def _registrar_ganadores(self, ganadores):
        """
        envia vía pipes los resultados a todos los procesos agency.
        """

        for pipe in self.pipes:
            # Convertir los ganadores a una cadena
            serialized_data = str(ganadores)
            
            #TODO modificar para que no tengan que ser 10 digitos -> mucho espacio
            data_length = f"{len(serialized_data):010d}"  # Convertir el tamaño a una cadena de 10 dígitos

            # Enviar tamaño del mensaje
            pipe.send_bytes(data_length.encode("utf-8"))  # Enviar el tamaño como una cadena de longitud fija

            # Enviar los datos
            pipe.send_bytes(serialized_data.encode("utf-8"))  # Asegurarse de que todos los datos sean enviados
        
        self._on = False # cierro server

    def _graceful_shutdown(self, signum, frame):
        logging.info("action: shutdown | result: success")
        self._on = False

    def _shutdown(self):
        for process in self._client_processes:
            process.join()

        for pipe in self.pipes:
            pipe.close()
        
        self._server_socket.close()
        logging.info("action: exit | result: success")