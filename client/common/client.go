package common

import (
	"fmt"
	"net"
	"os"
	"os/signal"
	"syscall"
	"time"
	"strconv"

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

	// Crear y establecer la conexión con el servidor
	conn, err := CreateClientSocket(c.config.ServerAddress)
	if err != nil {
		log.Errorf("action: connect | result: fail | client_id: %v | error: %v", c.config.ID, err)
		return
	}
	defer conn.Close()

	// Leer apuesta desde las variables de entorno
	bet, err := c.readBetFromEnv()
	if err != nil {
		log.Errorf("action: read_bet | result: fail | client_id: %v | error: %v", c.config.ID, err)
		return
	}

	// Codificar la apuesta en un mensaje de bytes
	message, err := EncodeBetMessage([]Bet{bet})
	if err != nil {
		log.Errorf("action: encode_message | result: fail | error: %v", err)
		return
	}

	// Enviar la apuesta al servidor
	err = SendMessage(conn, message)

	if err != nil {
		log.Errorf("action: send_message | result: fail | client_id: %v | error: %v", c.config.ID, err)
		return
	}

	log.Infof("action: send_message | result: success | client_id: %v", c.config.ID)

	// Recibir datos crudos de respuesta desde el servidor
	response, err := ReceiveMessage(conn)
	if err != nil {
		log.Errorf("action: receive_message | result: fail | client_id: %v | error: %v", c.config.ID, err)
		return
	}

	log.Infof("action: recv_message | result: success | client_id: %v", c.config.ID)

	// Decodificar la respuesta de confirmación
	success, err := DecodeConfirmationMessage(response)
	if err != nil {
		log.Errorf("action: decode_confirmation | result: fail | client_id: %v | error: %v", c.config.ID, err)
	} else if success {
		log.Infof("action: apuesta_enviada | result: success | dni: %d | numero: %d", bet.Document, bet.Number)
	} else {
		log.Infof("action: apuesta_enviada | result: fail | dni: %d | numero: %d", bet.Document, bet.Number)
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

// readBetFromEnv lee las variables de entorno para crear una estructura de apuesta
func (c *Client) readBetFromEnv() (Bet, error) {
	agencyStr := os.Getenv("AGENCIA")
	firstName := os.Getenv("NOMBRE")
	lastName := os.Getenv("APELLIDO")
	documentStr := os.Getenv("DOCUMENTO")
	birthdate := os.Getenv("NACIMIENTO")
	numberStr := os.Getenv("NUMERO")

	if agencyStr == "" || firstName == "" || lastName == "" || documentStr == "" || birthdate == "" || numberStr == "" {
		return Bet{}, fmt.Errorf("faltan una o más variables de entorno necesarias")
	}

	agency, err := strconv.ParseUint(agencyStr, 10, 8)
	if err != nil {
		return Bet{}, fmt.Errorf("error al parsear el ID de la agencia: %v", err)
	}

	document, err := strconv.ParseUint(documentStr, 10, 32)
	if err != nil {
		return Bet{}, fmt.Errorf("error al parsear el documento: %v", err)
	}

	number, err := strconv.ParseUint(numberStr, 10, 16)
	if err != nil {
		return Bet{}, fmt.Errorf("error al parsear el número apostado: %v", err)
	}

	return Bet{
		Agency:    uint8(agency),
		FirstName: firstName,
		LastName:  lastName,
		Document:  uint32(document),
		Birthdate: birthdate,
		Number:    uint16(number),
	}, nil
}
