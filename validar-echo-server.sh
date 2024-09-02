#!/bin/bash

# Configuración
SERVER_CONTAINER_NAME="server"
CONFIG_FILE_PATH="./server/config.ini"
MESSAGE="validar echo server"
SERVER_PORT="12345"

# Ejecuta netcat desde un contenedor temporal en la misma red
RESPONSE=$(docker run --rm --network tp0_testing_net busybox sh -c "echo -n '$MESSAGE' | nc $SERVER_CONTAINER_NAME $SERVER_PORT")

# Verifica si el mensaje recibido es igual al mensaje enviado
if [ "$RESPONSE" = "$MESSAGE" ]; then
    echo "action: test_echo_server | result: success"
else
    echo "action: test_echo_server | result: fail"
fi
