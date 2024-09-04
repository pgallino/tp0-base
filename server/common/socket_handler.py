# communication/socket_handler.py

import logging
import socket
import struct
from common.messages import (
    encode_bet_message,
    encode_confirmation_message,
    encode_finalization_message,
    encode_query_message,
    decode_message
)
from common.utils import Bet

def recibir_mensaje(sock):
    """
    Lee un mensaje completo del socket y lo devuelve.
    """
    header = receive_exactly(sock, 2)
    if not header:
        raise ValueError("No se pudo leer el encabezado del mensaje.")
    
    total_length = struct.unpack('>H', header)[0]
    logging.debug(f"Encabezado recibido: {header.hex()} (longitud total del mensaje: {total_length} bytes)")
    data = receive_exactly(sock, total_length - 2)
    
    if not data:
        raise ValueError("No se pudo leer los datos del mensaje.")
    
    logging.debug(f"Datos recibidos: {data.hex()}")
    
    return header + data

def receive_exactly(sock, length):
    """
    Asegura la recepción de exactamente 'length' bytes desde el socket.
    """
    data = bytearray()
    while len(data) < length:
        packet = sock.recv(length - len(data))
        if not packet:
            return None  # Conexión cerrada o no se pudieron leer más datos
        data.extend(packet)
    return data

def enviar_mensaje(sock, message):
    """
    Envía un mensaje completo al socket.
    """
    try:
        sock.sendall(message)
    except socket.error as e:
        logging.error(f"Error al enviar el mensaje: {e}")
        raise
    
    logging.debug(f"Envio mensaje al cliente: {message}")
def enviar_apuestas(sock, bets):
    """
    Codifica y envía un mensaje de apuestas.
    """
    message = encode_bet_message(bets)
    enviar_mensaje(sock, message)

def enviar_confirmacion(sock, success):
    """
    Codifica y envía un mensaje de confirmación.
    """
    message = encode_confirmation_message(success)
    enviar_mensaje(sock, message)

def enviar_finalizacion(sock, agency_id):
    """
    Codifica y envía un mensaje de finalización.
    """
    message = encode_finalization_message(agency_id)
    enviar_mensaje(sock, message)

def enviar_consulta(sock, agency_id):
    """
    Codifica y envía un mensaje de consulta de ganadores.
    """
    message = encode_query_message(agency_id)
    enviar_mensaje(sock, message)
