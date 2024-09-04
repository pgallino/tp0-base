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

// Constantes para tipos de mensajes
const (
	MSG_TYPE_APUESTA      = 0x01
	MSG_TYPE_CONFIRMACION = 0x02
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

	// Codificar cada apuesta
	for _, bet := range bets {
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
	}

	return buffer.Bytes(), nil
}

// DecodeConfirmationMessage decodifica un mensaje de confirmación recibido desde el servidor
func DecodeConfirmationMessage(data []byte) (bool, error) {
	// Verificar que el mensaje tenga exactamente 2 bytes (tipo de mensaje + código de estado)
	if len(data) != 2 {
		log.Errorf(
			"action: decode_confirmation | result: fail | reason: message too short | length_received: %d",
			len(data),
		)
		return false, fmt.Errorf("action: decode_confirmation | result: fail | reason: message too short | length_received: %d",
			len(data))
	}

	// Verificar que el tipo de mensaje sea el esperado (MSG_TYPE_CONFIRMACION)
	if data[0] != MSG_TYPE_CONFIRMACION {
		log.Errorf(
			"action: decode_confirmation | result: fail | reason: unexpected message type | message_type: %x",
			data[0],
		)
		return false, fmt.Errorf("action: decode_confirmation | result: fail | reason: unexpected message type | message_type: %x",
			data[0])
	}

	// El segundo byte es el código de estado: 0x00 para éxito, 0x01 para error
	success := data[1] == 0x00
	return success, nil
}
