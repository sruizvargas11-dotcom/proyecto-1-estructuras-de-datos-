# persistencia/partida_binaria.py
import json, os

from estructuras.vector_dinamico import Vector
from estructuras.ordenamientos import ordenar

# "CRPT" en bytes — sirve para reconocer el archivo como nuestro
MAGIC           = 0x43525054
VERSION_FORMATO = 1


def _escribir(f, numero, n_bytes):
    # convierte el número a big-endian y lo escribe directo
    f.write(numero.to_bytes(n_bytes, byteorder="big"))

def _leer(f, n_bytes):
    # lee n_bytes y los interpreta como entero big-endian
    return int.from_bytes(f.read(n_bytes), byteorder="big")

def _comparar_pares(a, b):
    """Compara pares (sala_id, datos) por sala_id, para ordenar() propio."""
    return (a[0] > b[0]) - (a[0] < b[0])


class ErrorFormatoBinario(Exception):
    pass


class PartidaBinaria:
    """
    Guarda y carga la partida en un archivo binario propio.

    Estructura del archivo:
        [encabezado]  12 bytes  — magic, versión, num_salas, dónde empiezan los datos
        [índice]      n × 8 bytes — sala_id + offset para cada sala (ordenado)
        [global]      4 + n bytes — longitud + JSON del estado global
        [salas]       un bloque por sala: sala_id(4) + longitud(4) + JSON
    """

    def __init__(self, ruta: str):
        self.ruta = ruta

    # ── guardar ──────────────────────────────────────────────────────────

    def guardar(self, estado_global: dict, salas):
        """Escribe todo el estado al archivo.

        salas: secuencia de pares (sala_id:int, datos), en cualquier orden
        (lista o Vector propio). Un sala_id repetido es un error del
        llamador, no un estado válido para guardar.
        """
        os.makedirs(os.path.dirname(self.ruta) or ".", exist_ok=True)

        pares = Vector()
        for sala_id, datos in salas:
            pares.agregarValor((sala_id, datos))

        ordenar(pares, _comparar_pares)   # ordenados para búsqueda binaria

        for i in range(1, len(pares)):
            anterior = pares.obtenerValor(i - 1)
            actual   = pares.obtenerValor(i)
            if anterior[0] == actual[0]:
                raise ValueError(f"sala_id repetido al guardar: {actual[0]}")

        num_salas = len(pares)

        b_global = json.dumps(estado_global, ensure_ascii=False).encode()

        # calculamos dónde va a caer cada bloque de sala en el archivo
        # encabezado(12) + índice(n×8) + longitud_global(4) + datos_global
        inicio_datos = 12 + num_salas * 8 + 4 + len(b_global)

        bloques = Vector()   # bytes JSON de cada sala, en el mismo orden que 'pares'
        offsets = Vector()
        cursor  = inicio_datos
        for i in range(num_salas):
            sid, datos = pares.obtenerValor(i)
            b = json.dumps(datos, ensure_ascii=False).encode()
            bloques.agregarValor(b)
            offsets.agregarValor(cursor)
            cursor += 4 + 4 + len(b)   # sala_id + longitud + datos

        with open(self.ruta, "wb") as f:

            # encabezado
            _escribir(f, MAGIC,           4)   # marca "CRPT"
            _escribir(f, VERSION_FORMATO, 2)   # versión del formato
            _escribir(f, num_salas,       2)   # cuántas salas hay
            _escribir(f, inicio_datos,    4)   # offset donde empiezan los bloques

            # índice: permite saltar directo a cualquier sala sin leer todo
            for i in range(num_salas):
                sid, _ = pares.obtenerValor(i)
                _escribir(f, sid, 4)
                _escribir(f, offsets.obtenerValor(i), 4)

            # estado global (reloj, jugador, inventario, semilla…)
            _escribir(f, len(b_global), 4)
            f.write(b_global)

            # un bloque por cada sala
            for i in range(num_salas):
                sid, _ = pares.obtenerValor(i)
                b = bloques.obtenerValor(i)
                _escribir(f, sid,    4)
                _escribir(f, len(b), 4)
                f.write(b)

    # ── lectura ───────────────────────────────────────────────────────────

    def _leer_encabezado(self, f):
        """Valida magic y versión; devuelve (num_salas, inicio_datos)."""
        magic = _leer(f, 4)
        if magic != MAGIC:
            raise ErrorFormatoBinario(
                "El archivo no es una partida de CRIPTA o está dañado."
            )
        version = _leer(f, 2)
        if version != VERSION_FORMATO:
            raise ErrorFormatoBinario(
                f"Versión del archivo ({version}) no compatible "
                f"con esta versión del programa ({VERSION_FORMATO})."
            )
        return _leer(f, 2), _leer(f, 4)   # num_salas, inicio_datos

    def cargar_global(self) -> dict:
        """Lee solo el estado global; no toca los bloques de sala."""
        with open(self.ruta, "rb") as f:
            num_salas, _ = self._leer_encabezado(f)
            f.seek(12 + num_salas * 8)   # saltamos el índice entero
            longitud = _leer(f, 4)
            return json.loads(f.read(longitud))

    def cargar_sala_binaria(self, sala_id: int) -> dict | None:
        """
        Carga una sala específica con búsqueda binaria DIRECTAMENTE sobre el
        índice en disco: cada paso es un seek + la lectura de una sola
        entrada (8 bytes), nunca el índice completo. O(log n) lecturas,
        más un último seek al bloque de la sala.
        """
        with open(self.ruta, "rb") as f:
            num_salas, _ = self._leer_encabezado(f)
            off = self._buscar_offset_en_indice(f, num_salas, sala_id)
            if off is None:
                return None   # la sala no estaba guardada

            f.seek(off + 4)              # +4 para saltarnos el sala_id
            longitud = _leer(f, 4)
            return json.loads(f.read(longitud))

    def _buscar_offset_en_indice(self, f, num_salas, sala_id):
        """Búsqueda binaria sobre las entradas de 8 bytes del índice en
        disco (arranca justo después del encabezado de 12 bytes)."""
        inicio_indice = 12
        inicio, fin = 0, num_salas - 1

        while inicio <= fin:
            medio = (inicio + fin) // 2
            f.seek(inicio_indice + medio * 8)
            sid = _leer(f, 4)
            off = _leer(f, 4)

            if sid == sala_id:
                return off
            if sid < sala_id:
                inicio = medio + 1
            else:
                fin = medio - 1

        return None

    def cargar_todo(self) -> tuple:
        """Carga estado global + todas las salas. Útil para pruebas.

        Devuelve (estado_global, salas), donde 'salas' es la secuencia de
        pares (sala_id, datos) ordenados por sala_id (así quedaron
        escritos en el archivo).
        """
        with open(self.ruta, "rb") as f:
            num_salas, _ = self._leer_encabezado(f)
            for _ in range(num_salas):
                f.read(8)   # saltamos el índice

            longitud      = _leer(f, 4)
            estado_global = json.loads(f.read(longitud))

            salas = []
            for _ in range(num_salas):
                sid      = _leer(f, 4)
                longitud = _leer(f, 4)
                datos    = json.loads(f.read(longitud))
                salas.append((sid, datos))

        return estado_global, salas