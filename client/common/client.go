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
	agency uint8
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

    // Abrir una conexión con el servidor una vez
    conn, err := CreateClientSocket(c.config.ServerAddress)
    if err != nil {
        log.Errorf("action: connect | result: fail | client_id: %v | error: %v", c.config.ID, err)
        return
    }
    defer conn.Close() // Cerrar la conexión al final de todo

	err = c.readAndSendBets(conn)
	if err != nil {
		log.Errorf("action: send_bets | result: fail | client_id: %v | error: %v", c.config.ID, err)
		return
	}

    // Notificar finalización de apuestas
    err = c.notifyFinalization(conn)
    if err != nil {
        log.Errorf("action: notify_end | result: fail | client_id: %v | error: %v", c.config.ID, err)
        return
    }

    // Consultar lista de ganadores
    err = c.consultWinners(conn)
    if err != nil {
        log.Errorf("action: consult_winners | result: fail | client_id: %v | error: %v", c.config.ID, err)
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
func (c *Client) readAndSendBets(conn net.Conn) error {


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
	
	// Restar los primeros 4 bytes del encabezado
	bytesRestantes := limitBytes - 4

	agency, err := strconv.ParseUint(agencyIDStr, 10, 8)
	if err != nil {
		return fmt.Errorf("error al parsear AGENCIA: %v", err)
	}
	c.agency = uint8(agency)

	for {
		// Leer una fila del CSV
		row, err := reader.Read()
		if err == io.EOF {
			break
		} else if err != nil {
			return fmt.Errorf("error al leer el archivo CSV: %v", err)
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

		// Si agregar esta apuesta supera el límite de tamaño en bytes, envio el batch actual
		if batchBuffer.Len()+len(betBytes) > bytesRestantes {

			log.Infof("El batch actual alcanzó el límite. Tamaño: %d bytes | Número de apuestas: %d", batchBuffer.Len(), bets_number)
			// envio el batch actual
			err := c.sendBatch(conn, batchBuffer.Bytes(), bets_number)
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
		err := c.sendBatch(conn, batchBuffer.Bytes(), bets_number)
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
		log.Infof("action: batch_apuesta_confirmada | result: success")
	} else {
		log.Infof("action: batch_apuesta_confirmada | result: fail")
	}
}

// sendBatch abre una nueva conexión, envía el batch, espera la confirmación, y cierra la conexión
func (c *Client) sendBatch(conn net.Conn, batchBuffer []byte, numBets int) error {

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

// Enviar notificación de fin de apuestas
func (c *Client) notifyFinalization(conn net.Conn) error {
	message, err := EncodeFinalizationMessage(c.agency)
	if err != nil {
		return fmt.Errorf("error al codificar la notificacion: %v", err)
	}
    err = SendMessage(conn, message)
    if err != nil {
        return fmt.Errorf("error al enviar notificación de fin de apuestas: %v", err)
    }
    log.Infof("action: end_of_bets_notification | result: success | client_id: %v", c.config.ID)
    return nil
}

// Consultar lista de ganadores
func (c *Client) consultWinners(conn net.Conn) error {
	message, err := EncodeWinnerQueryMessage(c.agency)
	if err != nil {
		return fmt.Errorf("error al codificar la query: %v", err)
	}

    err = SendMessage(conn, message)
    if err != nil {
        return fmt.Errorf("error al solicitar lista de ganadores: %v", err)
    }

    // Recibir respuesta
    response, err := ReceiveMessage(conn)
    if err != nil {
        return fmt.Errorf("error al recibir lista de ganadores: %v", err)
    }

    // Decodificar lista de ganadores
    winners, err := DecodeWinnersMessage(response)
    if err != nil {
        return fmt.Errorf("error al decodificar la lista de ganadores: %v", err)
    }

    // Imprimir la cantidad de ganadores por log
    log.Infof("action: consulta_ganadores | result: success | cant_ganadores: %d", len(winners))
	// Imprimir la lista completa de ganadores
	log.Infof("Lista de ganadores: %v", winners)

    return nil
}