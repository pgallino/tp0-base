// socket_handler.go
package common

import (
	"bufio"
	"net"
	"encoding/binary"
)

// CreateClientSocket initializes a client socket and connects to the server
func CreateClientSocket(ServerAddress string) (net.Conn, error) {
	conn, err := net.Dial("tcp", ServerAddress)
	if err != nil {
		log.Errorf("error al conectar con el servidor: %v", err)
		return nil, err
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
			log.Errorf("error al enviar datos al servidor: %v", err)
			return err
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
			log.Errorf("error al leer el encabezado del mensaje: %v", err)
			return nil, err
		}
		bytesRead += n
	}

	// Imprimir el encabezado en formato hexadecimal
	log.Infof("Encabezado recibido: %x", header)

	// Decodificar la longitud total del mensaje (big-endian)
	messageLength := int(binary.BigEndian.Uint16(header))

	// Imprimir la longitud total del mensaje
	log.Infof("Longitud total del mensaje: %d", messageLength)

	// Leer el resto del mensaje basado en la longitud especificada (messageLength - 2)
	data := make([]byte, messageLength - 2)  // Ya hemos leído los primeros 2 bytes de la longitud
	bytesRead = 0
	for bytesRead < len(data) {
		n, err := reader.Read(data[bytesRead:])
		if err != nil {
			log.Errorf("error al leer el cuerpo del mensaje: %v", err)
			return nil, err
		}
		bytesRead += n
	}

	// Imprimir el cuerpo del mensaje en formato hexadecimal
	log.Infof("Cuerpo del mensaje recibido: %x", data)

	return data, nil
}

