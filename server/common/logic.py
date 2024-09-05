# common/application/app_logic.py

import logging
import multiprocessing
import time
from common.utils import Bet, store_bets
from common.messages import (
    decode_message,
    encode_confirmation_message,
    encode_winners_message
)

from common.socket_handler import recv_msg, send_msg

def AgencyProcess(agency_socket, store_lock, notif_queue, pipe_conn):
    agency_id = None  # Para guardar el ID de la agencia cuando llegue el mensaje de finalización

    try:
        while True:
            data = recv_msg(agency_socket)  # Recibir mensaje
            if not data:
                logging.error("NO LLEGO NADA EN EL HILO PRINCIPAL")
                break
            
            # Procesar el mensaje
            decoded_message = decode_message(data)

            if isinstance(decoded_message, list) and all(isinstance(bet, Bet) for bet in decoded_message):
                # Almacenar las apuestas recibidas
                with store_lock:
                    store_bets(decoded_message)
                response = encode_confirmation_message(success=True)
                logging.info("Apuestas almacenadas exitosamente.")
                send_msg(agency_socket, response)

            elif decoded_message.get("tipo") == "finalizacion":
                agency_id = decoded_message["agency_id"]
                notif_queue.put(agency_id)
                logging.info(f"Agencia {agency_id} ha enviado notificación de finalización.")


                ganadores = pipe_conn.recv()
                logging.info(f"Recibidos los ganadores para la agencia {agency_id}: {ganadores}")

                # Filtrar los ganadores de la agencia correspondiente
                ganadores_agencia = ganadores.get(agency_id, [])

                response = encode_winners_message(ganadores_agencia)
                send_msg(agency_socket, response)
                logging.info(f"Resultados enviados a la agencia {agency_id}.")
                break  # Salir del ciclo tras la notificación y espera

            else:
                # Tipo de mensaje desconocido
                logging.error("action: procesar_mensaje | result: fail | error: Tipo de mensaje desconocido")

    except Exception as e:
        logging.error(f"Error en la conexión con la agencia: {e}")
    finally:
        # Cerrar el socket cuando el proceso termina
        logging.info("Cerrando el socket de la agencia")
        agency_socket.close()  # Cerramos el socket explícitamente

