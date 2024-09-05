# common/application/app_logic.py

import logging
from common.utils import Bet, store_bets
from common.messages import (
    decode_message,
    encode_confirmation_message,
    encode_winners_message
)

from common.socket_handler import recv_msg, send_msg

LENGTH_PIPE_MSG = 10

def AgencyProcess(agency_socket, store_lock, notif_queue, pipe_conn):
    agency_id = None  # Para guardar el ID de la agencia cuando llegue el mensaje de finalización
    ganadores_encodeados = None

    try:
        while True:
            data = recv_msg(agency_socket)  # Recibir mensaje
            if not data:
                logging.error("action: recv_data | result: error | no se recibio data")
                break
            
            # Procesar el mensaje
            decoded_message = decode_message(data)

            # ============== Mensaje de batch de apuestas ============== #

            if decoded_message.get("tipo") == "apuesta":
                apuestas = decoded_message["apuestas"]

                # Almacenar las apuestas recibidas -> utilizo lock
                with store_lock:
                    store_bets(apuestas)
                response = encode_confirmation_message(success=True)

                logging.info(f"action: almacenar batch | result: success | cantidad de apuestas: {len(apuestas)}")
                # logging.debug(f"apuestas almacenadas: {apuestas}")
                send_msg(agency_socket, response)

                logging.info("action: confirmation | result: success")

            # ============== Mensaje de finalización ============== #

            elif decoded_message.get("tipo") == "finalizacion":
                agency_id = decoded_message["agency_id"]
                notif_queue.put(agency_id)

                logging.info(f"action: notificado | result: success | Agencia {agency_id} ha enviado notificación de finalización.")

                # Recibir primero el tamaño del mensaje (10 bytes)
                data_length_str = pipe_conn.recv_bytes(LENGTH_PIPE_MSG).decode('utf-8')  # Recibir los primeros 10 bytes que contienen el tamaño
                data_length = int(data_length_str)

                # Recibir los datos completos
                serialized_data = pipe_conn.recv_bytes(data_length).decode('utf-8')  # Recibir todos los datos

                # Convertir la cadena recibida en la estructura de datos original
                ganadores_agencia = eval(serialized_data)  # Convertir de nuevo a dic

                # Filtrar los ganadores de la agencia correspondiente
                ganadores_agencia = ganadores_agencia.get(agency_id, [])

                #TODO guardar los ganadores y enviarlos luego de recibir el mensaje de solicitud
                response = encode_winners_message(ganadores_agencia)
                ganadores_encodeados = response


                logging.info(f"action: load_winners | result: success | Agency: {agency_id}")
            
            elif decoded_message.get("tipo") == "consulta":
                if ganadores_encodeados:
                    send_msg(agency_socket, response)
                    logging.info(f"action: send_results | result: success | Agency: {agency_id}")
                    break # Salir del ciclo
            else:
                # Tipo de mensaje desconocido
                logging.error("action: procesar_mensaje | result: fail | error: Tipo de mensaje desconocido")

    except Exception as e:
        logging.error(f"Error en la conexión con la agencia: {e}")
    finally:
        # Cerrar el socket cuando el proceso termina
        agency_socket.close()  # Cerrar socket
        pipe_conn.close()  # Cerrar el pipe
        logging.info(f"action: closing | result: success | msg: cerró el proceso de agency: {agency_id}")

# # TODO utilizar esta funcion si no está permitida eval
# def parse_to_dict(serialized_data):
#     result = {}
    
#     # Eliminar los corchetes iniciales y finales
#     serialized_data = serialized_data.strip('{}')

#     # Separar las entradas por comas, pero asegurarte de que no estén dentro de una lista
#     entries = serialized_data.split('],')

#     for entry in entries:
#         # Separar la clave del valor
#         key, value = entry.split(': [')

#         # Quitar cualquier espacio extra y convertir la clave a entero
#         key = int(key.strip())

#         # Convertir el valor en una lista de strings
#         value = value.replace("'", "").replace("]", "").split(', ')

#         # Guardar en el diccionario
#         result[key] = value

#     return result