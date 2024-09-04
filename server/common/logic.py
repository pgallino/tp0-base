# common/application/app_logic.py

import logging
from server.common.utils import Bet, store_bets, load_bets
from common.messages import (
    decode_message,
    encode_confirmation_message
)

def procesar_mensaje(data):
    """
    Procesa el mensaje recibido, maneja la lógica de negocio y envía una confirmación.

    Args:
        data: Los datos binarios recibidos del cliente.
        sock: El socket del cliente a través del cual se envió el mensaje.

    Returns:
        response: Una respuesta codificada para enviar de vuelta al cliente, si corresponde.
    """
    try:
        decoded_message = decode_message(data)

        if isinstance(decoded_message, list) and all(isinstance(bet, Bet) for bet in decoded_message):
            # Manejo de mensaje de tipo apuesta
            logging.info(f"action: procesar_apuesta | result: success | apuestas: {decoded_message}")
            store_bets(decoded_message)  # Almacena las apuestas recibidas
            response = encode_confirmation_message(success=True)
            return response

        elif decoded_message.get("tipo") == "confirmacion":
            # Manejo de mensaje de tipo confirmación
            logging.info(f"action: procesar_confirmacion | result: success | success: {decoded_message['success']}")
            # No se requiere respuesta
            return None

        elif decoded_message.get("tipo") == "finalizacion":
            # Manejo de mensaje de tipo finalización
            agency_id = decoded_message["agency_id"]
            logging.info(f"action: procesar_finalizacion | result: success | agency_id: {agency_id}")
            # Respuesta opcional, por ejemplo, una confirmación
            response = encode_confirmation_message(success=True)
            return response

        elif decoded_message.get("tipo") == "consulta":
            # Manejo de mensaje de tipo consulta de ganadores
            agency_id = decoded_message["agency_id"]
            logging.info(f"action: procesar_consulta | result: success | agency_id: {agency_id}")
            # Aquí podrías implementar lógica para enviar una lista de ganadores
            response = encode_confirmation_message(success=True)
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
