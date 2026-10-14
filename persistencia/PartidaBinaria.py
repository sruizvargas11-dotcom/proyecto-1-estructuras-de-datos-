# persistencia/partida_binaria.py
import json, os

# "CRPT" en bytes — sirve para reconocer el archivo como nuestro
MAGIC           = 0x43525054
VERSION_FORMATO = 1


def _escribir(f, numero, n_bytes):
    # convierte el número a big-endian y lo escribe directo
    f.write(numero.to_bytes(n_bytes, byteorder="big"))

def _leer(f, n_bytes):
    # lee n_bytes y los interpreta como entero big-endian
    return int.from_bytes(f.read(n_bytes), byteorder="big")


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

    def guardar(self, estado_global: dict, estado_salas: dict):
        """Escribe todo el estado al archivo."""
        os.makedirs(os.path.dirname(self.ruta) or ".", exist_ok=True)

        sala_ids  = sorted(estado_salas.keys())   # ordenados para búsqueda binaria
        num_salas = len(sala_ids)

        b_global = json.dumps(estado_global, ensure_ascii=False).encode()

        # calculamos dónde va a caer cada bloque de sala en el archivo
        # encabezado(12) + índice(n×8) + longitud_global(4) + datos_global
        inicio_datos = 12 + num_salas * 8 + 4 + len(b_global)

        offsets = []
        cursor  = inicio_datos
        for sid in sala_ids:
            offsets.append(cursor)
            b = json.dumps(estado_salas[sid], ensure_ascii=False).encode()
            cursor += 4 + 4 + len(b)   # sala_id + longitud + datos

        with open(self.ruta, "wb") as f:

            # encabezado
            _escribir(f, MAGIC,           4)   # marca "CRPT"
            _escribir(f, VERSION_FORMATO, 2)   # versión del formato
            _escribir(f, num_salas,       2)   # cuántas salas hay
            _escribir(f, inicio_datos,    4)   # offset donde empiezan los bloques

            # índice: permite saltar directo a cualquier sala sin leer todo
            for sid, off in zip(sala_ids, offsets):
                _escribir(f, sid, 4)
                _escribir(f, off, 4)

            # estado global (reloj, jugador, inventario, semilla…)
            _escribir(f, len(b_global), 4)
            f.write(b_global)

            # un bloque por cada sala
            for sid in sala_ids:
                b = json.dumps(estado_salas[sid], ensure_ascii=False).encode()
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
        Carga una sala específica usando búsqueda binaria sobre el índice
        y un único seek. No lee el archivo completo.
        """
        with open(self.ruta, "rb") as f:
            num_salas, _ = self._leer_encabezado(f)

            # cargamos el índice en memoria (es pequeño, n × 8 bytes)
            indice = [(_leer(f, 4), _leer(f, 4)) for _ in range(num_salas)]

        # búsqueda binaria O(log n) sobre el índice
        izq, der = 0, num_salas - 1
        while izq <= der:
            medio    = (izq + der) // 2
            sid, off = indice[medio]

            if sid == sala_id:
                # encontrada — saltamos directo a su bloque
                with open(self.ruta, "rb") as f:
                    f.seek(off + 4)              # +4 para saltarnos el sala_id
                    longitud = _leer(f, 4)
                    return json.loads(f.read(longitud))

            elif sid < sala_id:
                izq = medio + 1
            else:
                der = medio - 1

        return None   # la sala no estaba guardada

    def cargar_todo(self) -> tuple:
        """Carga estado global + todas las salas. Útil para pruebas."""
        with open(self.ruta, "rb") as f:
            num_salas, _ = self._leer_encabezado(f)
            for _ in range(num_salas):
                f.read(8)   # saltamos el índice

            longitud      = _leer(f, 4)
            estado_global = json.loads(f.read(longitud))

            estado_salas = {}
            for _ in range(num_salas):
                sid               = _leer(f, 4)
                longitud          = _leer(f, 4)
                estado_salas[sid] = json.loads(f.read(longitud))

        return estado_global, estado_salas