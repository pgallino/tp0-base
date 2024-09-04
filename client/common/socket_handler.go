// socket_handler.go
package common

import (
	"bufio"
	"fmt"
	"net"
)

// CreateClientSocket initializes a client socket and connects to the server
func CreateClientSocket() (net.Conn, error) {
	conn, err := net.Dial("tcp", c.Config.ServerAddress)
	if err != nil {
		return nil, fmt.Errorf("error al conectar con el servidor: %v", err)
	}
	return conn, nil
}

// SendMessage sends raw data to the server through the connection
func SendMessage(conn net.Conn, data []byte) error {
	totalSent := 0
	dataLen := len(data)
	for totalSent < dataLen {
		n, err := conn.Write(data[totalSent:])
		if err != nil {
			return fmt.Errorf("error al enviar datos al servidor: %v", err)
		}
		totalSent += n
	}
	return nil
}

// ReceiveMessage reads raw data from the server through the connection
func ReceiveMessage(conn net.Conn) ([]byte, error) {
	reader := bufio.NewReader(conn)

	// Leer el encabezado del mensaje para obtener la longitud total (2 bytes)
	header := make([]byte, 2)
	bytesRead := 0
	for bytesRead < len(header) {
		n, err := reader.Read(header[bytesRead:])
		if err != nil {
			return nil, fmt.Errorf("error al leer el encabezado del mensaje: %v", err)
		}
		bytesRead += n
	}

	// Decodificar la longitud total del mensaje (big-endian)
	messageLength := int(binary.BigEndian.Uint16(header))

	// Leer el resto del mensaje basado en la longitud especificada
	data := make([]byte, messageLength)
	bytesRead = 0
	for bytesRead < messageLength {
		n, err := reader.Read(data[bytesRead:])
		if err != nil {
			return nil, fmt.Errorf("error al leer el cuerpo del mensaje: %v", err)
		}
		bytesRead += n
	}

	return data, nil
}

