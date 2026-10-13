import os

MARCA     = "CRIPTA_LOG v1"
SEPARADOR = "----------"


class ErrorVersionIncompatible(Exception):
    pass


class BitacoraPartida:

    def __init__(self, ruta, cripta_id, version_cripta, version_catalogo, semilla):
        self.ruta             = ruta
        self.cripta_id        = cripta_id
        self.version_cripta   = version_cripta
        self.version_catalogo = version_catalogo
        self.semilla          = semilla
        self._archivo         = None

    @classmethod
    def partida_nueva(cls, ruta, cripta_id, version_cripta, version_catalogo, semilla):
        """Crea el archivo y escribe los datos de la partida al inicio."""
        carpeta = os.path.dirname(ruta)
        if carpeta:
            os.makedirs(carpeta, exist_ok=True)

        with open(ruta, "w", encoding="utf-8") as f:
            f.write(f"{MARCA}\n")
            f.write(f"cripta_id: {cripta_id}\n")
            f.write(f"version_cripta: {version_cripta}\n")
            f.write(f"version_catalogo: {version_catalogo}\n")
            f.write(f"semilla: {semilla}\n")
            f.write(f"{SEPARADOR}\n")

        return cls(ruta, cripta_id, version_cripta, version_catalogo, semilla)

    @classmethod
    def abrir(cls, ruta):
        if not os.path.exists(ruta):
            raise FileNotFoundError(f"Archivo {ruta} no existe")

        with open(ruta, "r", encoding="utf-8") as f:
            primera = f.readline().strip()
            if primera != MARCA:
                raise ValueError(f"El archivo no es una bitácora de CRIPTA.")

            campos = {}
            for linea in f:
                if linea.strip() == SEPARADOR:
                    break
                if ":" in linea:
                    clave, _, valor = linea.partition(":")
                    campos[clave.strip()] = valor.strip()

        return cls(
            ruta             = ruta,
            cripta_id        = campos["cripta_id"],
            version_cripta   = campos["version_cripta"],
            version_catalogo = campos["version_catalogo"],
            semilla          = int(campos["semilla"]),
        )

    def registrar(self, tiempo: int, accion: str):
        if self._archivo is None:
            self._archivo = open(self.ruta, "a", encoding="utf-8")
        self._archivo.write(f"t={tiempo} {accion}\n")
        self._archivo.flush()

    def cerrar(self):
        if self._archivo is not None:
            self._archivo.close()
            self._archivo = None

    def leer_acciones(self):
        """Lee todas las acciones registradas, devuelve lista de (tiempo, accion)."""
        acciones = []
        with open(self.ruta, "r", encoding="utf-8") as f:
            primera = f.readline().strip()
            if primera != MARCA:
                raise ValueError("El archivo no es una bitácora de CRIPTA.")

            for linea in f:
                if linea.strip() == SEPARADOR:
                    break

            for linea in f:
                linea = linea.rstrip("\n")
                if not linea:
                    continue
                prefijo, _, accion = linea.partition(" ")
                tiempo = int(prefijo[len("t="):])
                acciones.append((tiempo, accion))

        return acciones

    def verificar_compatibilidad(self, version_cripta, version_catalogo):
        problemas = []
        if self.version_cripta != version_cripta:
            problemas.append(f"cripta: log='{self.version_cripta}' actual='{version_cripta}'")
        if self.version_catalogo != version_catalogo:
            problemas.append(f"catalogo: log='{self.version_catalogo}' actual='{version_catalogo}'")
        if problemas:
            raise ErrorVersionIncompatible(
                "No se puede garantizar reproducción fiel: " + ", ".join(problemas)
            )

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.cerrar()

