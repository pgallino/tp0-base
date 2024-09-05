import sys

def generar_docker_compose(nombre_archivo, cantidad_clientes):

    with open(nombre_archivo, 'w') as archivo:

        archivo.write("version: '3'\n")  # Versión del docker-compose
        archivo.write("services:\n")

        # Configuración del servidor
        archivo.write("  server:\n")
        archivo.write("    container_name: server\n")
        archivo.write("    image: server:latest\n")
        archivo.write("    entrypoint: python3 /main.py\n")
        archivo.write("    environment:\n")
        archivo.write("      - PYTHONUNBUFFERED=1\n")
        archivo.write("    volumes:\n")
        archivo.write("      - ./server/config.ini:/config.ini\n")
        archivo.write("    networks:\n")
        archivo.write("      - testing_net\n")
        archivo.write("\n")

        # Configuración de los clientes
        for i in range(1, cantidad_clientes + 1):
            archivo.write(f"  client{i}:\n")
            archivo.write(f"    container_name: client{i}\n")
            archivo.write("    image: client:latest\n")
            archivo.write("    entrypoint: /client\n")
            archivo.write("    environment:\n")
            archivo.write(f"      - CLI_ID={i}\n")
            archivo.write(f"      - AGENCIA={i}\n")  # AGENCIA variable
            archivo.write("    volumes:\n")
            archivo.write(f"      - ./dataset:/data\n")  # Montar el directorio con los archivos CSV
            archivo.write("      - ./client/config.yaml:/config.yaml\n")
            archivo.write("    networks:\n")
            archivo.write("      - testing_net\n")
            archivo.write("    depends_on:\n")
            archivo.write("      - server\n")
            archivo.write("\n")

        # Configuración de la red
        archivo.write("networks:\n")
        archivo.write("  testing_net:\n")
        archivo.write("    ipam:\n")
        archivo.write("      driver: default\n")
        archivo.write("      config:\n")
        archivo.write("        - subnet: 172.25.125.0/24\n")

if __name__ == "__main__":

    nombre_archivo = sys.argv[1]
    cantidad_clientes = int(sys.argv[2])

    generar_docker_compose(nombre_archivo, cantidad_clientes)
