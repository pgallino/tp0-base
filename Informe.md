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

## 1.3 Paquete de Finalización (MSG_TYPE_FINALIZACION = 0x03)

Este mensaje es enviado por la agencia cuando ha completado el envío de todas sus apuestas:

- **Bytes 1-2**: Longitud del mensaje.
- **Byte 3**: Tipo de mensaje, `0x03`.
- **Byte 4**: ID de la agencia (1 byte, uint8).

Permite al servidor saber que la agencia ha completado su envío, lo cual es importante para sincronizar el sorteo de ganadores.

## 1.4 Paquete de Consulta de Ganadores (MSG_TYPE_CONSULTA = 0x04)

Este mensaje es enviado por la agencia cuando quiere consultar los resultados del sorteo:

- **Bytes 1-2**: Longitud del mensaje.
- **Byte 3**: Tipo de mensaje, `0x04`.
- **Byte 4**: ID de la agencia (1 byte, uint8).

## 1.5 Paquete de Lista de Ganadores (MSG_TYPE_WINNERS = 0x05)

Este mensaje es la respuesta del servidor a una consulta de ganadores:

- **Bytes 1-2**: Longitud total del mensaje.
- **Byte 3**: Tipo de mensaje, `0x05`.
- **Byte 4**: Cantidad de ganadores (1 byte, uint8).
- **Bytes 5-N**: Cada ganador es representado por su DNI (4 bytes, uint32, big-endian).

# 2. Métodos de Sincronización

## 2.1 Mutex/Locks para Sincronización de Acceso a Recursos Compartidos

Dado que múltiples procesos de agencias pueden intentar acceder al mismo recurso compartido (almacenar apuestas en un archivo), se utilizan **locks** para garantizar que solo un proceso a la vez pueda modificar estos recursos críticos. Esto es esencial para evitar condiciones de carrera donde múltiples procesos puedan corromper los datos o sobreescribir la información.

**Uso del Lock**: Antes de acceder al almacenamiento de apuestas, los procesos bloquean el recurso, garantizando que solo una agencia a la vez pueda escribir en el archivo. Una vez completada la operación, el recurso se desbloquea para que otros procesos puedan acceder a él.

## 2.2 Sincronización mediante Colas

Se utiliza una **cola de notificaciones** (usando `Queue`) para que las agencias puedan notificar al servidor cuando han terminado de enviar sus apuestas. Esta cola es una estructura bloqueante, lo que significa que el servidor puede esperar a que todas las agencias terminen antes de proceder con el sorteo.

**Funcionamiento**: Cuando una agencia envía un mensaje de finalización, su ID es encolada, y el servidor monitoriza la cola para saber cuándo todas las agencias han completado su envío de apuestas.

## 2.3 Pipes para Comunicación entre Procesos

Se utilizan **pipes** para la comunicación entre el servidor y los procesos de las agencias. Los pipes permiten el intercambio de información de manera eficiente entre los diferentes procesos involucrados en el sistema.

## 2.4 Multiprocessing

Se levanta un proceso por cada agencia, contando con un total de seis procesos teniendo en cuenta el proceso principal.

Los procesos reciben las apuestas y las cargan. Luego notifican al servidor (proceso principal) que sus agencias terminaron y comienza el sorteo.