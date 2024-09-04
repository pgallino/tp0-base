# communication/socket_handler.py

import logging
import socket
import struct
from common.messages import (
    encode_bet_message,
    encode_confirmation_message,
)
from common.utils import Bet

def recv_msg(sock):
    """
    Lee un mensaje completo del socket y lo devuelve.
    """
    header = _recv_all(sock, 2)
    if not header:
        raise ValueError("No se pudo leer el encabezado del mensaje.")
    
    total_length = struct.unpack('>H', header)[0]
    data = _recv_all(sock, total_length - 2)
    
    if not data:
        raise ValueError("No se pudo leer los datos del mensaje.")
    
    return header + data

def _recv_all(sock, length):
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

def send_msg(sock, message):
    """
    Envía un mensaje completo al socket.
    """
    try:
        sock.sendall(message)
    except socket.error as e:
        logging.error(f"Error al enviar el mensaje: {e}")
        raise
