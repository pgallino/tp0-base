#!/bin/bash

# Configuración
SERVER_CONTAINER_NAME="server"
CONFIG_FILE_PATH="./server/config.ini"
MESSAGE="validar"

# Como el puerto puede variar lo leo directamente del config
SERVER_PORT=$(grep "SERVER_PORT" $CONFIG_FILE_PATH | awk -F '=' '{print $2}' | xargs)

# Ejecuta netcat desde un contenedor temporal en la misma red
RESPONSE=$(docker run --rm --network tp0_testing_net busybox:latest sh -c "echo -n '$MESSAGE' | nc $SERVER_CONTAINER_NAME $SERVER_PORT")

# Verifica si el mensaje recibido es igual al mensaje enviado
if [ "$RESPONSE" = "$MESSAGE" ]; then
    echo "action: test_echo_server | result: success"
else
    echo "action: test_echo_server | result: fail"
fi
