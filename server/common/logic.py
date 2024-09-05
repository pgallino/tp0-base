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

def _recv_all(pipe_conn, length):
    """Función para recibir exactamente `length` bytes del pipe."""
    data = b''  # Usar bytes, no strings
    while len(data) < length:
        logging.info(f"Esperando recibir {length - len(data)} bytes más...")  # Log de bytes restantes
        chunk = pipe_conn.recv_bytes(min(4096, length - len(data)))  # Leer en bloques de bytes
        if not chunk:
            raise RuntimeError("Conexión cerrada antes de recibir todos los datos")
        data += chunk
        logging.info(f"Recibidos {len(chunk)} bytes, total recibido: {len(data)} bytes")  # Log de bytes recibidos
    return data


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

                # Recibir primero el tamaño del mensaje (10 bytes)
                data_length_str = _recv_all(pipe_conn, 10).decode('utf-8')  # Recibir los primeros 10 bytes
                logging.info(f"LARGO RECIBIDO para la agencia {agency_id}: {data_length_str}")
                
                # Verificar si el tamaño es razonable
                try:
                    data_length = int(data_length_str)
                except ValueError:
                    logging.error(f"Tamaño de datos inválido recibido: {data_length_str}")
                    break

                logging.info(f"Tamaño de datos convertido: {data_length} bytes para la agencia {agency_id}")

                # Leer los datos del pipe -> evito short read
                serialized_data = _recv_all(pipe_conn, data_length).decode('utf-8')  # Recibir todos los datos
                logging.info(f"Recibidos los ganadores serializados para la agencia {agency_id}: {serialized_data}")

                # Convertir la cadena recibida en la estructura de datos original
                ganadores_agencia = parse_to_dict(serialized_data)  # Convertir de nuevo a dic
                logging.info(f"Recibidos los ganadores para la agencia {agency_id}: {ganadores_agencia}")

                # Filtrar los ganadores de la agencia correspondiente
                ganadores_agencia = ganadores_agencia.get(agency_id, [])

                logging.info(f"GANADORES {agency_id}: {ganadores_agencia}")

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

def parse_to_dict(serialized_data):
    result = {}
    
    # Eliminar los corchetes iniciales y finales
    serialized_data = serialized_data.strip('{}')

    # Separar las entradas por comas, pero asegurarte de que no estén dentro de una lista
    entries = serialized_data.split('],')

    for entry in entries:
        # Separar la clave del valor
        key, value = entry.split(': [')

        # Quitar cualquier espacio extra y convertir la clave a entero
        key = int(key.strip())

        # Convertir el valor en una lista de strings
        value = value.replace("'", "").replace("]", "").split(', ')

        # Guardar en el diccionario
        result[key] = value

    return result