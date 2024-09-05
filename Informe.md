# Informe de Instalación y Configuración del Sistema

## 1. Instalación y Estructura de los Datasets

Guardar los datasets en una carpeta llamada `dataset` dentro de la carpeta raíz del repositorio. 
Esta carpeta contiene los archivos de datos que cada agencia utilizará para enviar sus apuestas al servidor. La estructura de la carpeta es la siguiente:

/dataset 

├── agency-1.csv 

├── agency-2.csv 

├── agency-3.csv 

├── agency-4.csv 

├── agency-5.csv

## 2. Uso del Script `generate-compose.sh` para Añadir Volúmenes

Para permitir que los clientes accedan a los archivos de apuestas (`agency-*.csv`) desde los contenedores en Docker, creé un script llamado `generate-compose.sh`. Este script configura automáticamente el archivo `docker-compose.yml` para montar la carpeta `dataset` como un volumen en los contenedores de los clientes.

La linea a ejecutar debe ser:

`./generar-compose.sh docker-compose-dev.yaml 5`

## 3 Correr el programa `make docker-compose-up`

Finalmente debe correrse el comando make docker-compose-up.
Los otros comandos se encuentran en el readme original.

# 1. Protocolo de Comunicación

El protocolo diseñado para el intercambio de información entre el servidor y las agencias sigue una estructura clara basada en mensajes bien definidos que permiten la transmisión eficiente de información crítica para el proceso de apuestas y la consulta de ganadores. A continuación, se detallan los distintos tipos de mensajes utilizados en el protocolo:

## 1.1 Paquete de Apuesta (MSG_TYPE_APUESTA = 0x01)

Este paquete es utilizado por las agencias para enviar lotes de apuestas al servidor. La estructura incluye:

- **Bytes 1-2**: Longitud total del mensaje, codificada en 2 bytes (uint16, big-endian), lo que permite mensajes de hasta 65,535 bytes.
- **Byte 3**: Tipo de mensaje, que en este caso es `0x01`, indicando que el mensaje contiene apuestas.
- **Byte 4**: Cantidad de apuestas en el lote (uint8).
- **Byte 5-N**: Cada apuesta incluye los siguientes campos:
  - **Agencia**: 1 byte (uint8) que identifica la agencia que envía las apuestas.
  - **Nombre y Apellido**: El tamaño de cada uno se codifica en 1 byte seguido de los caracteres del nombre o apellido.
  - **DNI**: Documento del apostador, codificado en 4 bytes (uint32, big-endian).
  - **Fecha de Nacimiento**: Representada en 10 bytes como una cadena `YYYY-MM-DD`.
  - **Número apostado**: Codificado en 2 bytes (uint16, big-endian).

Este formato es eficiente porque agrupa múltiples apuestas en un solo paquete, optimizando las comunicaciones al evitar múltiples llamadas a la red por cada apuesta individual.

## 1.2 Paquete de Confirmación (MSG_TYPE_CONFIRMACION = 0x02)

Este mensaje es la respuesta del servidor a la recepción de un lote de apuestas:

- **Bytes 1-2**: Longitud del mensaje (2 bytes, uint16, big-endian).
- **Byte 3**: Tipo de mensaje, `0x02`, que indica una confirmación.
- **Byte 4**: Código de estado, `0x00` para éxito o `0x01` para error.

La simplicidad de este mensaje es clave para confirmar rápidamente si las apuestas fueron procesadas correctamente sin sobrecargar la red con información adicional innecesaria.
