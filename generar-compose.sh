#!/bin/bash

if [ $# -ne 2 ]; then
    echo "Uso: $0 <nombre_del_archivo_de_salida> <cantidad_de_clientes>"
    exit 1
fi

echo "Nombre del archivo de salida: $1"
echo "Cantidad de clientes: $2"
python3 mi-generador.py $1 $2