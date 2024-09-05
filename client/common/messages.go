// messages.go
package common

import (
	"bytes"
	"encoding/binary"
	"fmt"
)

// # Estructura de los paquetes -> pensado para ej 5 y 6
// # =========================================
// # 1. Paquete de Apuesta (MSG_TYPE_APUESTA = 0x01)
// # -----------------------------------------
// # Byte 1-2  : Longitud total del mensaje (2 bytes, uint16, big-endian)
// # Byte 3    : Tipo de mensaje (1 byte, valor fijo: 0x01)
// # Byte 4    : Cantidad de apuestas en el batch (1 byte, uint8)
// # Byte 5-N  : Apuestas (estructura repetida para cada apuesta):
// #     - Byte 1  : Agencia (1 byte, uint8)
// #     - Byte 2  : Longitud del nombre (1 byte, uint8)
// #     - Byte 3-N: Nombre (N bytes, longitud variable)
// #     - Byte M  : Longitud del apellido (1 byte, uint8)
// #     - Byte M+1-N+M: Apellido (N bytes, longitud variable)
// #     - Byte N+1-N+4: DNI (4 bytes, uint32, big-endian)
// #     - Byte N+5-N+14: Fecha de nacimiento (10 bytes, string en formato YYYY-MM-DD)
// #     - Byte N+15-N+16: Número apostado (2 bytes, uint16, big-endian)
// # -----------------------------------------

// # 2. Paquete de Confirmación (MSG_TYPE_CONFIRMACION = 0x02)
// # -----------------------------------------
// # Byte 1-2  : Longitud total del mensaje (2 bytes, uint16, big-endian)
// # Byte 3    : Tipo de mensaje (1 byte, valor fijo: 0x02)
// # Byte 4    : Código de estado (1 byte, uint8; 0x00 para éxito, 0x01 para error)

// # 3. Paquete de Finalización (MSG_TYPE_FINALIZACION = 0x03)
// # -----------------------------------------
// # Byte 1-2  : Longitud total del mensaje (2 bytes, uint16, big-endian)
// # Byte 3    : Tipo de mensaje (1 byte, valor fijo: 0x03)
// # Byte 4    : ID de la agencia (1 byte, uint8)
// # -----------------------------------------

// # 4. Paquete de Consulta de Ganadores (MSG_TYPE_CONSULTA = 0x04)
// # -----------------------------------------
// # Byte 1-2  : Longitud total del mensaje (2 bytes, uint16, big-endian)
// # Byte 3    : Tipo de mensaje (1 byte, valor fijo: 0x04)
// # Byte 4    : ID de la agencia (1 byte, uint8)
// # -----------------------------------------

// # 5. Paquete de Lista de Ganadores (MSG_TYPE_WINNERS = 0x05)
// # -----------------------------------------
// # Byte 1-2  : Longitud total del mensaje (2 bytes, uint16, big-endian)
// # Byte 3    : Tipo de mensaje (1 byte, valor fijo: 0x05)
// # Byte 4    : Cantidad de ganadores (1 byte, uint8)
// # Byte 5-N  : Lista de ganadores (cada ganador es un DNI representado como 4 bytes, uint32, big-endian)
// # -----------------------------------------

// Constantes para tipos de mensajes
const (
	MSG_TYPE_APUESTA      = 0x01
	MSG_TYPE_CONFIRMACION = 0x02
	MSG_TYPE_FINALIZACION = 0x03
	MSG_TYPE_CONSULTA     = 0x04
	MSG_TYPE_WINNERS      = 0x05
)

func EncodeBetMessage(bets []Bet) ([]byte, error) {
	buffer := new(bytes.Buffer)

	// Calcular longitud total del mensaje
	totalLength := 4
	for _, bet := range bets {
		totalLength += 1 + 1 + len(bet.FirstName) + 1 + len(bet.LastName) + 4 + 10 + 2
	}

	// Escribir longitud total del mensaje
	if err := binary.Write(buffer, binary.BigEndian, uint16(totalLength)); err != nil {
		log.Errorf(
			"action: write_total_length | result: fail | error: %v",
			err,
		)
		return nil, err
	}

	// Escribir tipo de mensaje (MSG_TYPE_APUESTA)
	if err := buffer.WriteByte(MSG_TYPE_APUESTA); err != nil {
		log.Errorf(
			"action: write_message_type | result: fail | error: %v",
			err,
		)
		return nil, err
	}

	// Escribir cantidad de apuestas en el batch
	if err := buffer.WriteByte(uint8(len(bets))); err != nil {
		log.Errorf(
			"action: write_bet_count | result: fail | error: %v",
			err,
		)
		return nil, err
	}

	// Codificar cada apuesta usando encodeBet
	for _, bet := range bets {
		betBytes, err := encodeBet(bet)
		if err != nil {
			return nil, err
		}
		buffer.Write(betBytes) // Escribir los bytes de la apuesta al buffer
	}

	return buffer.Bytes(), nil
}

func encodeBet(bet Bet) ([]byte, error) {
	buffer := new(bytes.Buffer)

	// Escribir agencia
	if err := buffer.WriteByte(bet.Agency); err != nil {
		log.Errorf(
			"action: write_agency | result: fail | error: %v",
			err,
		)
		return nil, err
	}

	// Escribir longitud y nombre
	if err := buffer.WriteByte(uint8(len(bet.FirstName))); err != nil {
		log.Errorf(
			"action: write_first_name_length | result: fail | error: %v",
			err,
		)
		return nil, err
	}
	if _, err := buffer.WriteString(bet.FirstName); err != nil {
		log.Errorf(
			"action: write_first_name | result: fail | error: %v",
			err,
		)
		return nil, err
	}

	// Escribir longitud y apellido
	if err := buffer.WriteByte(uint8(len(bet.LastName))); err != nil {
		log.Errorf(
			"action: write_last_name_length | result: fail | error: %v",
			err,
		)
		return nil, err
	}
	if _, err := buffer.WriteString(bet.LastName); err != nil {
		log.Errorf(
			"action: write_last_name | result: fail | error: %v",
			err,
		)
		return nil, err
	}

	// Escribir DNI
	if err := binary.Write(buffer, binary.BigEndian, bet.Document); err != nil {
		log.Errorf(
			"action: write_dni | result: fail | error: %v",
			err,
		)
		return nil, err
	}

	// Escribir fecha de nacimiento
	if _, err := buffer.WriteString(bet.Birthdate); err != nil {
		log.Errorf(
			"action: write_birthdate | result: fail | error: %v",
			err,
		)
		return nil, err
	}

	// Escribir número apostado
	if err := binary.Write(buffer, binary.BigEndian, bet.Number); err != nil {
		log.Errorf(
			"action: write_bet_number | result: fail | error: %v",
			err,
		)
		return nil, err
	}

	return buffer.Bytes(), nil
}

func encodeBatchMessage(batchBuffer []byte, numBets int) ([]byte, error) {
	// Crear un nuevo buffer para construir el mensaje final
	buffer := new(bytes.Buffer)

	// Calcular longitud total del mensaje (4 bytes fijos + longitud del contenido de batchBuffer)
	totalLength := 4 + len(batchBuffer) // 2 bytes para la longitud total + 1 byte para el tipo de mensaje + 1 byte para el número de apuestas

	// Escribir longitud total del mensaje
	if err := binary.Write(buffer, binary.BigEndian, uint16(totalLength)); err != nil {
		log.Errorf(
			"action: write_total_length | result: fail | error: %v",
			err,
		)
		return nil, err
	}

	// Escribir tipo de mensaje (MSG_TYPE_APUESTA)
	if err := buffer.WriteByte(MSG_TYPE_APUESTA); err != nil {
		log.Errorf(
			"action: write_message_type | result: fail | error: %v",
			err,
		)
		return nil, err
	}

	// Escribir cantidad de apuestas en el batch
	if err := buffer.WriteByte(uint8(numBets)); err != nil {
		log.Errorf(
			"action: write_bet_count | result: fail | error: %v",
			err,
		)
		return nil, err
	}

	// Escribir el contenido ya codificado en batchBuffer después de los encabezados
	if _, err := buffer.Write(batchBuffer); err != nil {
		log.Errorf(
			"action: write_batch_buffer | result: fail | error: %v",
			err,
		)
		return nil, err
	}

	// Devolver los bytes del mensaje completo
	return buffer.Bytes(), nil
}

// EncodeFinalizationMessage crea un mensaje de finalización (tipo 0x03)
func EncodeFinalizationMessage(agencyID uint8) ([]byte, error) {
	buffer := new(bytes.Buffer)

	// Longitud total del mensaje (4 bytes fijos)
	totalLength := uint16(4)

	// Escribir longitud total del mensaje (2 bytes, big-endian)
	if err := binary.Write(buffer, binary.BigEndian, totalLength); err != nil {
		return nil, fmt.Errorf("error al escribir la longitud total del mensaje de finalización: %v", err)
	}

	// Escribir tipo de mensaje (1 byte, valor fijo: 0x03)
	if err := buffer.WriteByte(MSG_TYPE_FINALIZACION); err != nil {
		return nil, fmt.Errorf("error al escribir el tipo de mensaje: %v", err)
	}

	// Escribir ID de la agencia (1 byte)
	if err := buffer.WriteByte(agencyID); err != nil {
		return nil, fmt.Errorf("error al escribir el ID de la agencia: %v", err)
	}

	return buffer.Bytes(), nil
}

// EncodeWinnerQueryMessage crea un mensaje de consulta de ganadores (tipo 0x04)
func EncodeWinnerQueryMessage(agencyID uint8) ([]byte, error) {
	buffer := new(bytes.Buffer)

	// Longitud total del mensaje (4 bytes fijos)
	totalLength := uint16(4)

	// Escribir longitud total del mensaje (2 bytes, big-endian)
	if err := binary.Write(buffer, binary.BigEndian, totalLength); err != nil {
		return nil, fmt.Errorf("error al escribir la longitud total del mensaje de consulta de ganadores: %v", err)
	}

	// Escribir tipo de mensaje (1 byte, valor fijo: 0x04)
	if err := buffer.WriteByte(MSG_TYPE_CONSULTA); err != nil {
		return nil, fmt.Errorf("error al escribir el tipo de mensaje: %v", err)
	}

	// Escribir ID de la agencia (1 byte)
	if err := buffer.WriteByte(agencyID); err != nil {
		return nil, fmt.Errorf("error al escribir el ID de la agencia: %v", err)
	}

	return buffer.Bytes(), nil
}

// =============================== decodificadores ================================= //

func decodeMessage(response []byte) (string, interface{}, error) {
    if len(response) < 2 {
        return "", nil, fmt.Errorf("mensaje demasiado corto para decodificar")
    }

    // Extraer el tipo de mensaje del primer byte
    msgType := response[0]

    switch msgType {

    case MSG_TYPE_CONFIRMACION:
        // Si es un mensaje de confirmación
        success, err := DecodeConfirmationMessage(response)
        if err != nil {
            return "", nil, fmt.Errorf("error al decodificar el mensaje de confirmación: %v", err)
        }
        return "confirmacion", success, nil


    case MSG_TYPE_WINNERS:
        // Si es un mensaje de ganadores
        winners, err := DecodeWinnersMessage(response)
        if err != nil {
            return "", nil, fmt.Errorf("error al decodificar el mensaje de ganadores: %v", err)
        }
        return "ganadores", winners, nil

    default:
        return "", nil, fmt.Errorf("tipo de mensaje desconocido: %x", msgType)
    }
}


// DecodeConfirmationMessage decodifica un mensaje de confirmación recibido desde el servidor
func DecodeConfirmationMessage(response []byte) (bool, error) {
	// Verificar que el mensaje tenga exactamente 2 bytes (tipo de mensaje + código de estado)
	if len(response) < 2 {
		log.Errorf(
			"action: decode_confirmation | result: fail | reason: message too short | length_received: %d",
			len(response),
		)
		return false, fmt.Errorf("action: decode_confirmation | result: fail | reason: message too short | length_received: %d",
			len(response))
	}

	// Verificar que el tipo de mensaje sea el esperado (MSG_TYPE_CONFIRMACION)
	if response[0] != MSG_TYPE_CONFIRMACION {
		log.Errorf(
			"action: decode_confirmation | result: fail | reason: unexpected message type | message_type: %x",
			response[0],
		)
		return false, fmt.Errorf("action: decode_confirmation | result: fail | reason: unexpected message type | message_type: %x",
			response[0])
	}

	// El segundo byte es el código de estado: 0x00 para éxito, 0x01 para error
	success := response[1] == 0x00
	return success, nil
}

func DecodeWinnersMessage(response []byte) ([]uint32, error) {
    if len(response) < 2 {  // Al menos debe tener 2 bytes: 1 para tipo y 1 para cantidad de ganadores
        return nil, fmt.Errorf("el mensaje de ganadores es demasiado corto")
    }

    // Verificar el tipo de mensaje (debería ser 0x05)
    if response[0] != MSG_TYPE_WINNERS {
        return nil, fmt.Errorf("tipo de mensaje inesperado: %x", response[0])
    }

    // Leer la cantidad de ganadores
    winnerCount := int(response[1])

    // Verificar que el tamaño del mensaje sea consistente con el número de ganadores
    expectedLength := 2 + winnerCount*4  // 2 bytes iniciales + 4 bytes por cada ganador
    if len(response) != expectedLength {
        return nil, fmt.Errorf("longitud de mensaje incorrecta: esperada %d, recibida %d", expectedLength, len(response))
    }

    // Leer los DNIs de los ganadores
    winners := make([]uint32, winnerCount)
    for i := 0; i < winnerCount; i++ {
        winners[i] = binary.BigEndian.Uint32(response[2+i*4:])
    }

    return winners, nil
}

