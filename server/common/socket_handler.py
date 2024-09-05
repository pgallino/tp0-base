import logging
import socket
import struct

BYTES_HEADER = 2

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

def recv_msg(sock):
    """
    Lee un mensaje completo del socket y lo devuelve.
    """
    header = _recv_all(sock, BYTES_HEADER)
    if not header:
        raise ValueError("Conexion cerrada o No se pudo leer el encabezado del mensaje.")
    
    total_length = struct.unpack('>H', header)[0]
    data = _recv_all(sock, total_length - BYTES_HEADER)
    
    if not data:
        raise ValueError("No se pudo leer los datos del mensaje.")
    
    return header + data

def send_msg(sock, message):
    """
    Envía un mensaje completo al socket.
    """
    try:
        sock.sendall(message)
    except socket.error as e:
        logging.error(f"Error al enviar el mensaje: {e}")
        raise
