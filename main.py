import sys


def crear_fuente(argumentos):
    if "--offline" in argumentos:
        from adaptadores.datos_offline import DatosOffline

        return DatosOffline()

    from adaptadores.datos_http import DatosHTTP

    return DatosHTTP()


def main():
    argumentos = sys.argv[1:]
    fuente = crear_fuente(argumentos)

    respuesta = fuente.listar_criptas()

    print("Criptas disponibles:")

    for cripta in respuesta["criptas"]:
        print(f"- {cripta['id']}: {cripta['nombre']}")


if __name__ == "__main__":
    main()