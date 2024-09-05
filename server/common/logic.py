# common/application/app_logic.py

import logging
import threading
import time
from common.utils import Bet, store_bets
from common.messages import (
    decode_message,
    encode_confirmation_message
)

from common.socket_handler import recv_msg, send_msg

class AgencyThread(threading.Thread):
    def __init__(self, agency_socket, store_lock, barrier, conexiones_por_agencia, conexiones_lock):
        super().__init__()
        self.agency_socket = agency_socket
        self.store_lock = store_lock
        self.barrier = barrier
        self.conexiones_por_agencia = conexiones_por_agencia
        self.conexiones_lock = conexiones_lock
        self.agency_id = None  # Para guardar el ID de la agencia cuando llegue el mensaje de finalización

    def run(self):
        """
        Lógica del hilo de agencia.
        Recibe mensajes, procesa, y espera en la barrera cuando recibe el mensaje de finalización.
        """
        try:
            while True:
                data = recv_msg(self.agency_socket)  # Recibir mensaje
                if not data:
                    logging.error("NO LLEGO NADA EN EL HILO PRINCIPAL")
                    break
                
                # Procesar el mensaje
                decoded_message = decode_message(data)

                if isinstance(decoded_message, list) and all(isinstance(bet, Bet) for bet in decoded_message):
                    # Almacenar las apuestas recibidas
                    with self.store_lock:
                        store_bets(decoded_message)
                    response = encode_confirmation_message(success=True)
                    logging.info("Apuestas almacenadas exitosamente.")
                    send_msg(self.agency_socket, response)

                elif decoded_message.get("tipo") == "finalizacion":
                    self.agency_id = decoded_message["agency_id"]
                    with self.conexiones_lock:
                        self.conexiones_por_agencia[self.agency_id] = self.agency_socket
                    logging.info(f"Agencia {self.agency_id} ha enviado notificación de finalización.")

                    time.sleep(5)
                    # Esperar en la barrera
                    self.barrier.wait()  # El hilo de la agencia espera hasta que todos lleguen
                    break  # Salir del ciclo tras la notificación y espera

                else:
                    # Tipo de mensaje desconocido
                    logging.error("action: procesar_mensaje | result: fail | error: Tipo de mensaje desconocido")

        except Exception as e:
            logging.error(f"Error en la conexión con la agencia: {e}")
