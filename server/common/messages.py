import struct
import logging
from .utils import Bet

# Definición de los tipos de mensajes
MSG_TYPE_APUESTA = 0x01
MSG_TYPE_CONFIRMACION = 0x02
MSG_TYPE_FINALIZACION = 0x03
MSG_TYPE_CONSULTA = 0x04

# Estructura de los paquetes
# =========================================
# 1. Paquete de Apuesta (MSG_TYPE_APUESTA = 0x01)
# -----------------------------------------
# Byte 1-2  : Longitud total del mensaje (2 bytes, uint16, big-endian)
# Byte 3    : Tipo de mensaje (1 byte, valor fijo: 0x01)
# Byte 4    : Cantidad de apuestas en el batch (1 byte, uint8)
# Byte 5-N  : Apuestas (estructura repetida para cada apuesta):
#     - Byte 1  : Agencia (1 byte, uint8)
#     - Byte 2  : Longitud del nombre (1 byte, uint8)
#     - Byte 3-N: Nombre (N bytes, longitud variable)
#     - Byte M  : Longitud del apellido (1 byte, uint8)
#     - Byte M+1-N+M: Apellido (N bytes, longitud variable)
#     - Byte N+1-N+4: DNI (4 bytes, uint32, big-endian)
#     - Byte N+5-N+14: Fecha de nacimiento (10 bytes, string en formato YYYY-MM-DD)
#     - Byte N+15-N+16: Número apostado (2 bytes, uint16, big-endian)
# -----------------------------------------

# 2. Paquete de Confirmación (MSG_TYPE_CONFIRMACION = 0x02)
# -----------------------------------------
# Byte 1-2  : Longitud total del mensaje (2 bytes, uint16, big-endian)
# Byte 3    : Tipo de mensaje (1 byte, valor fijo: 0x02)
# Byte 4    : Código de estado (1 byte, uint8; 0x00 para éxito, 0x01 para error)
# -----------------------------------------

# 3. Paquete de Finalización (MSG_TYPE_FINALIZACION = 0x03)
# -----------------------------------------
# Byte 1-2  : Longitud total del mensaje (2 bytes, uint16, big-endian)
# Byte 3    : Tipo de mensaje (1 byte, valor fijo: 0x03)
# Byte 4    : ID de la agencia (1 byte, uint8)
# -----------------------------------------

# 4. Paquete de Consulta de Ganadores (MSG_TYPE_CONSULTA = 0x04)
# -----------------------------------------
# Byte 1-2  : Longitud total del mensaje (2 bytes, uint16, big-endian)
# Byte 3    : Tipo de mensaje (1 byte, valor fijo: 0x04)
# Byte 4    : ID de la agencia (1 byte, uint8)
# -----------------------------------------

# Todos los mensajes comienzan con un campo de longitud total para
# indicar el tamaño del mensaje, seguido por un tipo de mensaje que
# define qué tipo de operación se está solicitando o confirmando.

# Codificadores
# =========================================

def encode_bet_message(bets):
    """
    Codifica un batch de apuestas en un mensaje binario.
    """
    buffer = bytearray()
    total_length = 4  # 2 bytes para la longitud, 1 para el tipo, 1 para la cantidad de apuestas

    for bet in bets:
        nombre_bytes = bet.first_name.encode('utf-8')
        apellido_bytes = bet.last_name.encode('utf-8')
        nombre_len = len(nombre_bytes)
        apellido_len = len(apellido_bytes)

        # Sumar al total_length los bytes de cada campo de cada apuesta
        total_length += 1 + nombre_len + 1 + apellido_len + 4 + 10 + 2

        buffer.append(bet.agency)
        buffer.append(nombre_len)
        buffer.extend(nombre_bytes)
        buffer.append(apellido_len)
        buffer.extend(apellido_bytes)
        buffer.extend(struct.pack('>I', int(bet.document)))
        buffer.extend(bet.birthdate.isoformat().encode('utf-8'))
        buffer.extend(struct.pack('>H', bet.number))

    # Crear el mensaje completo
    message = struct.pack('>HBB', total_length, MSG_TYPE_APUESTA, len(bets))
    message += buffer

    return message

def encode_confirmation_message(success=True):
    """
    Codifica un mensaje de confirmación en un formato binario.
    """
    response_code = 0x00 if success else 0x01
    total_length = 4  # 2 bytes para la longitud, 1 para el tipo, 1 para el código de estado

    return struct.pack('>HBB', total_length, MSG_TYPE_CONFIRMACION, response_code)

def encode_finalization_message(agency_id):
    """
    Codifica un mensaje de finalización en un formato binario.
    """
    total_length = 4  # 2 bytes para la longitud, 1 para el tipo, 1 para el ID de la agencia

    return struct.pack('>HBB', total_length, MSG_TYPE_FINALIZACION, agency_id)

def encode_query_message(agency_id):
    """
    Codifica un mensaje de consulta de ganadores en un formato binario.
    """
    total_length = 4  # 2 bytes para la longitud, 1 para el tipo, 1 para el ID de la agencia

    return struct.pack('>HBB', total_length, MSG_TYPE_CONSULTA, agency_id)

# Decodificadores
# =========================================

def decode_message(data):
    """
    Decodifica un mensaje recibido en su estructura de datos correspondiente.
    """

    # El tipo de mensaje está en el tercer byte
    tipo_mensaje = data[2]

    if tipo_mensaje == MSG_TYPE_APUESTA:
        return decode_bet_message(data[3:])
    elif tipo_mensaje == MSG_TYPE_CONFIRMACION:
        return decode_confirmation_message(data[3:])
    elif tipo_mensaje == MSG_TYPE_FINALIZACION:
        return decode_finalization_message(data[3:])
    elif tipo_mensaje == MSG_TYPE_CONSULTA:
        return decode_query_message(data[3:])
    else:
        raise ValueError("Tipo de mensaje desconocido")

def decode_bet_message(data):
    """
    Decodifica un mensaje de tipo apuesta en una lista de objetos Bet.
    """
    cantidad_apuestas = data[0]
    offset = 1
    apuestas = []

    for _ in range(cantidad_apuestas):
        agency = data[offset]
        offset += 1

        nombre_len = data[offset]
        offset += 1
        nombre = data[offset:offset + nombre_len].decode('utf-8')
        offset += nombre_len

        apellido_len = data[offset]
        offset += 1
        apellido = data[offset:offset + apellido_len].decode('utf-8')
        offset += apellido_len

        dni = struct.unpack('>I', data[offset:offset + 4])[0]
        offset += 4

        nacimiento = data[offset:offset + 10].decode('utf-8')
        offset += 10

        numero = struct.unpack('>H', data[offset:offset + 2])[0]
        offset += 2

        bet = Bet(agency=str(agency), first_name=nombre, last_name=apellido,
                  document=str(dni), birthdate=nacimiento, number=str(numero))
        apuestas.append(bet)

    return apuestas

def decode_confirmation_message(data):
    """
    Decodifica un mensaje de confirmación y devuelve el estado.
    """
    response_code = data[0]
    success = (response_code == 0x00)
    return {"tipo": "confirmacion", "success": success}

def decode_finalization_message(data):
    """
    Decodifica un mensaje de finalización y devuelve el ID de la agencia.
    """
    agency_id = data[0]
    return {"tipo": "finalizacion", "agency_id": agency_id}

def decode_query_message(data):
    """
    Decodifica un mensaje de consulta de ganadores y devuelve el ID de la agencia.
    """
    agency_id = data[0]
    return {"tipo": "consulta", "agency_id": agency_id}