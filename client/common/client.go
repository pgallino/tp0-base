package common

import (
	"bufio"
	"fmt"
	"net"
	"time"
	"os"
	"os/signal"
	"sync"
	"syscall"

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
	on     bool
}

// NewClient Initializes a new client receiving the configuration
// as a parameter
func NewClient(config ClientConfig) *Client {
	client := &Client{
		config: config,
		on:     true,
	}

	client.setupSignalHandler()

	return client
}

// setupSignalHandler Configura una rutina para manejar señales SIGTERM
func (c *Client) setupSignalHandler() {
	// Canal para recibir señales del sistema
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGTERM)

	// Goroutine para manejar señales de manera graceful
	go func() {
		sig := <-sigChan
		c.on = false // Cambiar `on` a false para indicar que el bucle debe terminar
	}()
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
	// There is an autoincremental msgID to identify every message sent
	// Messages if the message amount threshold has not been surpassed
	for msgID := 1; msgID <= c.config.LoopAmount; msgID++ {

	    if !c.on {
			log.Infof("action: exit | result: success | client_id: %v", c.config.ID)
			break // Salir del bucle si se recibió una señal
		}

		// Create the connection the server in every loop iteration. Send an
		err := c.createClientSocket()
		if err != nil {
			break
			// si no me pude conectar salgo -> estaría bueno un numero de intentos
		}

		// TODO: Modify the send to avoid short-write
		_, err := fmt.Fprintf(
			c.conn,
			"[CLIENT %v] Message N°%v\n",
			c.config.ID,
			msgID,
		)

        if err != nil {
            log.Errorf("action: send_message | result: fail | client_id: %v | error: %v", c.config.ID, err)
            return
        }

		msg, err := bufio.NewReader(c.conn).ReadString('\n')

		if err != nil {
			log.Errorf("action: receive_message | result: fail | client_id: %v | error: %v",
				c.config.ID,
				err,
			)
			return
		}

		log.Infof("action: receive_message | result: success | client_id: %v | msg: %v",
			c.config.ID,
			msg,
		)

    	// Cerrar la conexión después de cada iteración
		c.conn.Close()

		// Wait a time between sending one message and the next one
		time.Sleep(c.config.LoopPeriod)

	}
	log.Infof("action: loop_finished | result: success | client_id: %v", c.config.ID)
}
