package common

import (
	"fmt"
	"net"
	"os"
	"os/signal"
	"syscall"
	"time"
	"strconv"
	"encoding/csv"
	"bytes"
	"io"

	"github.com/op/go-logging"
)

var log = logging.MustGetLogger("log")

type Bet struct {
	Agency    uint8
	FirstName string
	LastName  string
	Document  uint32
	Birthdate string // Formato: YYYY-MM-DD
	Number    uint16
}

// ClientConfig Configuration used by the client
type ClientConfig struct {
	ID            string
	ServerAddress string
	LoopAmount    int // por ahora no las uso
	LoopPeriod    time.Duration
	MaxSizeKB     int    // Tamaño máximo del batch en KB
}

// Client Entity that encapsulates how
type Client struct {
	config ClientConfig
	conn   net.Conn
}

// NewClient Initializes a new client receiving the configuration
// as a parameter
func NewClient(config ClientConfig) *Client {
	client := &Client{
		config: config,
	}
	return client
}

// StartClient
func (c *Client) StartClient() {

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGTERM)

	err := c.readAndSendBets()
	if err != nil {
		log.Errorf("action: send_bets | result: fail | client_id: %v | error: %v", c.config.ID, err)
		return
	}

	select {
	case <-sigChan:
		// Si recibimos SIGTERM, interrumpimos inmediatamente
		log.Infof("action: exit by SIGTERM | result: success | client_id: %v", c.config.ID)
	default:
		// Si no hay SIGTERM, simplemente terminamos normalmente
		log.Infof("action: exit | result: success | client_id: %v", c.config.ID)
	}

}

// readAndSendBets reads the bets from a CSV file, encodes them, and groups them into batchs by size
func (c *Client) readAndSendBets() error {


	agencyIDStr := os.Getenv("AGENCIA")
	if agencyIDStr == "" {
		return fmt.Errorf("la variable de entorno AGENCIA no está configurada")
	}

	csvFilePath := fmt.Sprintf("/data/agency-%s.csv", agencyIDStr)

	file, err := os.Open(csvFilePath)

	
	if err != nil {
		return fmt.Errorf("error al abrir el archivo CSV: %v", err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	batchBuffer := new(bytes.Buffer)
	bets_number := 0
	limitBytes := c.config.MaxSizeKB * 1024 // Convertir el tamaño del batch de KB a bytes

	// Log para ver el tamaño máximo del batch en bytes
	log.Infof("Tamaño máximo del batch: %d bytes", limitBytes)
	
	// Restar los primeros 4 bytes del encabezado
	bytesRestantes := limitBytes - 4
	
	// Log para ver cuántos bytes quedan disponibles después de restar el encabezado
	log.Infof("Bytes disponibles después de restar el encabezado: %d bytes", bytesRestantes)

	for {
		// Leer una fila del CSV
		row, err := reader.Read()
		if err == io.EOF {
			break
		} else if err != nil {
			return fmt.Errorf("error al leer el archivo CSV: %v", err)
		}
	
		agency, err := strconv.ParseUint(agencyIDStr, 10, 8)
		if err != nil {
			return fmt.Errorf("error al parsear AGENCIA: %v", err)
		}

		document, err := strconv.ParseUint(row[2], 10, 32)
		if err != nil {
			return fmt.Errorf("error al parsear el documento: %v", err)
		}

		number, err := strconv.ParseUint(row[4], 10, 16)
		if err != nil {
			return fmt.Errorf("error al parsear el número apostado: %v", err)
		}

		bet := Bet{
			Agency:    uint8(agency),
			FirstName: row[0],
			LastName:  row[1],
			Document:  uint32(document),
			Birthdate: row[3],
			Number:    uint16(number),
		}

		// Codificar la apuesta para obtener su tamaño en bytes
		betBytes, err := encodeBet(bet)
		if err != nil {
			return fmt.Errorf("error al codificar la apuesta: %v", err)
		}

		// Log para ver el tamaño de la apuesta en bytes
		log.Infof("Apuesta codificada: %v | Tamaño en bytes: %d", bet, len(betBytes))

		// Si agregar esta apuesta supera el límite de tamaño en bytes, envio el batch actual
		if batchBuffer.Len()+len(betBytes) > bytesRestantes {

			log.Infof("El batch actual alcanzó el límite. Tamaño: %d bytes | Número de apuestas: %d", batchBuffer.Len(), bets_number)
			// envio el batch actual
			err := c.sendBatch(batchBuffer.Bytes(), bets_number)
			if err != nil {
				return err
			}

			// Limpiar el buffer y la lista de apuestas para el siguiente batch
			batchBuffer.Reset()
			bets_number = 0
		}

		// Agregar la apuesta al batch
		batchBuffer.Write(betBytes)
		bets_number += 1
	}

	// Enviar el último batch si hay apuestas pendientes
	if batchBuffer.Len() > 0 {
		err := c.sendBatch(batchBuffer.Bytes(), bets_number)
		if err != nil {
			return err
		}
	}

	return nil
}

// waitForConfirmation recibe un mensaje de confirmación desde el servidor, lo decodifica y maneja el resultado
func waitForConfirmation(conn net.Conn) {
	// Esperar la confirmación del servidor
	response, err := ReceiveMessage(conn)
	if err != nil {
		log.Errorf("error al recibir la confirmación del servidor: %v", err)
		return
	}

	// Decodificar la confirmación
	success, err := DecodeConfirmationMessage(response)
	if err != nil {
		log.Errorf("error al decodificar la confirmación: %v", err)
		return
	}

	if success {
		log.Infof("action: batch_apuesta_enviada | result: success")
	} else {
		log.Infof("action: batch_apuesta_enviada | result: fail")
	}
}

// sendBatch abre una nueva conexión, envía el batch, espera la confirmación, y cierra la conexión
func (c *Client) sendBatch(batchBuffer []byte, numBets int) error {
	// Abrir una nueva conexión con el servidor
	conn, err := CreateClientSocket(c.config.ServerAddress)
	if err != nil {
		return fmt.Errorf("action: connect | result: fail | client_id: %v | error: %v", c.config.ID, err)
	}
	defer conn.Close()

	// Codificar el batch de apuestas
	message, err := encodeBatchMessage(batchBuffer, numBets)
	if err != nil {
		return fmt.Errorf("error al codificar el mensaje del batch: %v", err)
	}

	// Enviar el batch
	err = SendMessage(conn, message)
	if err != nil {
		return fmt.Errorf("error al enviar el batch: %v", err)
	}

	log.Infof("action: send batch | result: succes | cantidad bets: %d", numBets)

	// Esperar la confirmación del servidor
	waitForConfirmation(conn)

	// Cerrar la conexión (la conexión se cerrará automáticamente con defer)
	time.Sleep(c.config.LoopPeriod)
	return nil
}