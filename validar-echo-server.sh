#!/bin/bash

# Configuración
MESSAGE="validar echo server"

# Ejecuta netcat desde un contenedor temporal en la misma red
RESPONSE=$(docker run --rm --network tp0_testing_net busybox sh -c "echo -n '$MESSAGE' | nc server 12345")

# Verifica si el mensaje recibido es igual al mensaje enviado
if [ "$RESPONSE" = "$MESSAGE" ]; then
    echo "action: test_echo_server | result: success"
else
    echo "action: test_echo_server | result: fail"
fi
