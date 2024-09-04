// messages.go
package common

import (
	"bytes"
	"encoding/binary"
	"fmt"
)

// # Estructura de los paquetes
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

// EncodeBetMessage codifica una apuesta en un formato binario para enviar al servidor
func EncodeBetMessage(bets []Bet) ([]byte, error) {
	buffer := new(bytes.Buffer)

	// Calcular longitud total del mensaje
	// 4 bytes para el encabezado (longitud, tipo de mensaje, cantidad de apuestas)
	totalLength := 4
	for _, bet := range bets {
		totalLength += 1 + 1 + len(bet.FirstName) + 1 + len(bet.LastName) + 4 + 10 + 2
	}

	// Escribir longitud total del mensaje
	if err := binary.Write(buffer, binary.BigEndian, uint16(totalLength)); err != nil {
		return nil, fmt.Errorf("error al escribir la longitud del mensaje: %v", err)
	}

	// Escribir tipo de mensaje (MSG_TYPE_APUESTA)
	if err := buffer.WriteByte(MSG_TYPE_APUESTA); err != nil {
		return nil, fmt.Errorf("error al escribir el tipo de mensaje: %v", err)
	}

	// Escribir cantidad de apuestas en el batch
	if err := buffer.WriteByte(uint8(len(bets))); err != nil {
		return nil, fmt.Errorf("error al escribir la cantidad de apuestas: %v", err)
	}

	// Codificar cada apuesta
	for _, bet := range bets {
		// Escribir agencia
		if err := buffer.WriteByte(bet.Agency); err != nil {
			return nil, fmt.Errorf("error al escribir la agencia: %v", err)
		}

		// Escribir longitud y nombre
		if err := buffer.WriteByte(uint8(len(bet.FirstName))); err != nil {
			return nil, fmt.Errorf("error al escribir la longitud del nombre: %v", err)
		}
		if _, err := buffer.WriteString(bet.FirstName); err != nil {
			return nil, fmt.Errorf("error al escribir el nombre: %v", err)
		}

		// Escribir longitud y apellido
		if err := buffer.WriteByte(uint8(len(bet.LastName))); err != nil {
			return nil, fmt.Errorf("error al escribir la longitud del apellido: %v", err)
		}
		if _, err := buffer.WriteString(bet.LastName); err != nil {
			return nil, fmt.Errorf("error al escribir el apellido: %v", err)
		}

		// Escribir DNI
		if err := binary.Write(buffer, binary.BigEndian, bet.Document); err != nil {
			return nil, fmt.Errorf("error al escribir el DNI: %v", err)
		}

		// Escribir fecha de nacimiento
		if _, err := buffer.WriteString(bet.Birthdate); err != nil {
			return nil, fmt.Errorf("error al escribir la fecha de nacimiento: %v", err)
		}

		// Escribir número apostado
		if err := binary.Write(buffer, binary.BigEndian, bet.Number); err != nil {
			return nil, fmt.Errorf("error al escribir el número apostado: %v", err)
		}
	}

	return buffer.Bytes(), nil
}

// DecodeConfirmationMessage decodifica un mensaje de confirmación recibido desde el servidor
func DecodeConfirmationMessage(data []byte) (bool, error) {
	// Verificar que el mensaje tenga exactamente 2 bytes (tipo de mensaje + código de estado)
	if len(data) != 2 {
		return false, fmt.Errorf("mensaje de confirmación demasiado corto, longitud recibida: %d", len(data))
	}

	// Verificar que el tipo de mensaje sea el esperado (MSG_TYPE_CONFIRMACION)
	if data[0] != MSG_TYPE_CONFIRMACION {
		return false, fmt.Errorf("tipo de mensaje inesperado: %x", data[0])
	}

	// El segundo byte es el código de estado: 0x00 para éxito, 0x01 para error
	success := data[1] == 0x00
	return success, nil
}

