package common

import (
	"bufio"
	"fmt"
	"net"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/op/go-logging"
)

var log = logging.MustGetLogger("log")

// ClientConfig Configuration used by the client
type ClientConfig struct {
	ID            string
	ServerAddress string
	LoopAmount    int
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

// CreateClientSocket Initializes client socket. In case of
// failure, error is printed in stdout/stderr and exit 1
// is returned
func (c *Client) createClientSocket() error {
	conn, err := net.Dial("tcp", c.config.ServerAddress)
	if err != nil {
		log.Criticalf(
			"action: connect | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
		return err
	}
	c.conn = conn
	return nil
}

// StartClientLoop Send messages to the client until some time threshold is met
func (c *Client) StartClientLoop() {

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGTERM)

	// There is an autoincremental msgID to identify every message sent
	// Messages if the message amount threshold has not been surpassed
	for msgID := 1; msgID <= c.config.LoopAmount; msgID++ {
		select {
		case <-sigChan:
			if c.conn != nil {
				c.conn.Close()
			}
			log.Infof("action: exit | result: success | client_id: %v", c.config.ID)
			return
		default:
			// Create the connection the server in every loop iteration. Send an
			err := c.createClientSocket()
			if err != nil {
				log.Errorf("action: connect | result: fail | client_id: %v | error: %v", c.config.ID, err)
				return
			}

			// Verificar que c.conn no sea nil antes de usarla
			if c.conn == nil {
				log.Errorf("action: send_message | result: fail | client_id: %v | error: connection is nil", c.config.ID)
				return // terminar
			}

			// Enviar mensaje al servidor
			_, err = fmt.Fprintf(
				c.conn,
				"[CLIENT %v] Message N°%v\n",
				c.config.ID,
				msgID,
			)

			if err != nil {
				log.Errorf("action: send_message | result: fail | client_id: %v | error: %v", c.config.ID, err)
				return // terminar
			}

			// Leer respuesta del servidor
			msg, err := bufio.NewReader(c.conn).ReadString('\n')

			if err != nil {
				log.Errorf("action: receive_message | result: fail | client_id: %v | error: %v",
					c.config.ID,
					err,
				)
				return // terminar
			}

        	// Cerrar la conexión después de cada iteración
			c.conn.Close()

			log.Infof("action: receive_message | result: success | client_id: %v | msg: %v",
				c.config.ID,
				msg,
			)

			// Wait a time between sending one message and the next one
			time.Sleep(c.config.LoopPeriod)
		}
	}
	log.Infof("action: loop_finished | result: success | client_id: %v", c.config.ID)
}
