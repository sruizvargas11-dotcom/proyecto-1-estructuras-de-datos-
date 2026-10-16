import os

from estructuras.vector_dinamico import Vector

MARCA     = "CRIPTA_LOG v1"
SEPARADOR = "----------"
CIERRE    = "fin"   # t=<tiempo> fin <estado>, seguida de las líneas del estado final
ESTADO    = "= "    # prefijo de cada línea del estado final
CAMPOS    = ("cripta_id", "version_cripta", "version_catalogo", "semilla")


class ErrorVersionIncompatible(ValueError):
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

            # Tupla alineada con CAMPOS: cuatro claves fijas, sin diccionario.
            valores = [None, None, None, None]
            for linea in f:
                if linea.strip() == SEPARADOR:
                    break
                if ":" in linea:
                    clave, _, valor = linea.partition(":")
                    for i in range(len(CAMPOS)):
                        if CAMPOS[i] == clave.strip():
                            valores[i] = valor.strip()

        for i in range(len(CAMPOS)):
            if valores[i] is None:
                raise ValueError(f"La bitácora no tiene el campo '{CAMPOS[i]}' en el encabezado.")
        return cls(
            ruta             = ruta,
            cripta_id        = valores[0],
            version_cripta   = valores[1],
            version_catalogo = valores[2],
            semilla          = int(valores[3]),
        )

    def registrar(self, tiempo: int, accion: str):
        if self._archivo is None:
            self._archivo = open(self.ruta, "a", encoding="utf-8")
        self._archivo.write(f"t={tiempo} {accion}\n")
        self._archivo.flush()

    def registrar_cierre(self, tiempo: int, estado: str, lineas_estado):
        """Línea 'fin' y debajo el estado final completo; el replay lo compara."""
        self.registrar(tiempo, f"{CIERRE} {estado}")
        for linea in lineas_estado:
            self._archivo.write(f"{ESTADO}{linea}\n")
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
                if not linea or linea.startswith(ESTADO):
                    continue
                tiempo, accion = self._partir(linea)
                if accion.split(" ")[0] != CIERRE:
                    acciones.append((tiempo, accion))

        return acciones

    @staticmethod
    def _partir(linea):
        prefijo, _, accion = linea.partition(" ")
        if not prefijo.startswith("t=") or not prefijo[2:].isdigit() or not accion:
            raise ValueError(f"Línea de bitácora inválida: '{linea}'")
        return int(prefijo[2:]), accion

    def leer_cierre(self):
        """(tiempo, estado, lineas_estado) del cierre, o None si la partida no se
        cerró de forma controlada (por ejemplo, el programa se cayó)."""
        cierre = None
        with open(self.ruta, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.rstrip("\n")
                if cierre is not None and linea.startswith(ESTADO):
                    cierre[2].agregarValor(linea[len(ESTADO):])
                    continue
                if not linea.startswith("t="):
                    continue
                tiempo, accion = self._partir(linea)
                partes = accion.split(" ")
                if partes[0] == CIERRE and len(partes) >= 2:
                    cierre = (tiempo, partes[1], Vector())
        return cierre

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

