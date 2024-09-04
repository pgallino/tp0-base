# common/application/app_logic.py

import logging
from common.utils import Bet, store_bets
from common.messages import (
    decode_message,
    encode_confirmation_message
)

def procesar_mensaje(data):
    """
    Procesa el mensaje recibido, maneja la lógica de negocio y retorna respuesta
    """
    try:
        decoded_message = decode_message(data)

        if isinstance(decoded_message, list) and all(isinstance(bet, Bet) for bet in decoded_message):
            # Manejo de mensaje de tipo apuesta
            bet = decoded_message[0]
            store_bets(decoded_message)  # Almacena las apuestas recibidas
            for bet in decoded_message:
                logging.info(f"action: apuesta_almacenada | result: success | dni: {bet.document} | numero: {bet.number}")
            response = encode_confirmation_message(success=True)
            return response

        elif decoded_message.get("tipo") == "confirmacion":
            pass
            return None

        elif decoded_message.get("tipo") == "finalizacion":
            pass
            return None

        elif decoded_message.get("tipo") == "consulta":
            pass
            return None

        else:
            # Tipo de mensaje desconocido
            logging.error("action: procesar_mensaje | result: fail | error: Tipo de mensaje desconocido")
            response = encode_confirmation_message(success=False)
            return response

    except Exception as e:
        logging.error(f"action: procesar_mensaje | result: fail | error: {e}")
        response = encode_confirmation_message(success=False)
        return response
