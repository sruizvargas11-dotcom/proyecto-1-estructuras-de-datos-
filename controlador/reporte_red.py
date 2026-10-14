import os
from datetime import datetime

from estructuras.pila import Pila
from estructuras.vector_dinamico import Vector

RUTA_POR_DEFECTO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "partidas", "reportes_red.txt")
CAPACIDAD_HISTORIAL = 50
MARCA = "CRIPTA_REPORTES_RED v1"
INICIO_BLOQUE = "=== Reporte de red #"
FIN_BLOQUE = " ==="


def motivo_partida(estado):
    if estado == "victoria":
        return "victoria: el jugador llegó a la sala de salida"
    if estado == "derrota":
        return "derrota: la vida del jugador llegó a 0"
    return "salida controlada: el jugador terminó la sesión (Q)"


def motivo_error(error):
    texto = str(error)
    if "Presupuesto de solicitudes agotado" in texto:
        return f"presupuesto de solicitudes agotado: {texto}"
    return f"error: {type(error).__name__}: {texto}"


def _si_no(valor):
    return "sí" if valor else "no"


def _valor(pares, clave, defecto=0):
    for nombre, valor in pares:
        if nombre == clave:
            return valor
    return defecto


def _entero(valor):
    return valor if type(valor) is int else None


def _modo_fuente(fuente):
    modo = getattr(fuente, "modo", None)
    modo = modo() if callable(modo) else None
    return modo if isinstance(modo, str) else "http"


def construir_reporte(fuente, sesion, modo, motivo, ahora=None, bitacora=None):
    """Líneas del reporte (sin encabezado ni número). sesion puede ser None si
    la partida no llegó a crearse (por ejemplo, presupuesto agotado al cargar)."""
    ahora = ahora or datetime.now()
    lineas = Vector()
    agregar = lineas.agregarValor
    fuente_modo = _modo_fuente(fuente)
    agregar(f"fecha: {ahora.strftime('%Y-%m-%d %H:%M:%S')}")
    agregar(f"modo: {modo}")
    agregar(f"fuente: {fuente_modo}")

    partida = sesion.partida if sesion is not None else None
    if partida is not None:
        agregar(f"cripta: {partida.cripta_id}")
        agregar(f"version_cripta: {partida.version_cripta}")
        agregar(f"version_catalogo: {partida.version_catalogo}")
        agregar(f"semilla: {partida.semilla}")
    if bitacora:
        agregar(f"bitacora: {bitacora}")
    agregar("motivo_fin: " + " | ".join(parte.strip() for parte in str(motivo).split("\n")))
    if partida is not None:
        agregar(f"estado_final: {partida.estado}")
        agregar(f"tiempo_final: {partida.tiempo}")
        agregar(f"acciones_jugador: {partida.acciones_jugador}")
        agregar(f"enemigos_derrotados: {partida.enemigos_derrotados}")

    # El presupuesto sale de los datos generales de la cripta, nunca de una constante.
    agregar("-- Solicitudes de red --")
    realizadas = _entero(getattr(fuente, "requests_realizados", 0)) or 0
    if partida is not None:
        presupuesto = partida.cripta.presupuesto_solicitudes
    else:
        presupuesto = _entero(getattr(fuente, "presupuesto", None)) or None
    nota = " (offline: las lecturas locales no cuentan)" if fuente_modo == "offline" else ""
    agregar(f"solicitudes_realizadas: {realizadas}{nota}")
    if presupuesto is None:
        agregar("presupuesto_solicitudes: desconocido (no se llegó a leer la cripta)")
    else:
        agregar(f"presupuesto_solicitudes: {presupuesto}")
        agregar(f"restantes: {presupuesto - realizadas}")
        agregar(f"dentro_del_presupuesto: {_si_no(realizadas <= presupuesto)}")

    if sesion is None:
        return lineas

    red = sesion.red
    contadores = red.contadores()
    contenido = _valor(contadores, "solicitudes_contenido")
    catalogo = _valor(contadores, "solicitudes_catalogo")
    if fuente_modo == "offline":
        agregar(f"lotes_leidos_localmente: contenido {contenido}, catálogo {catalogo}")
    else:
        otras = realizadas - contenido - catalogo
        agregar(f"por_tipo: contenido {contenido}, catálogo {catalogo}, otras {otras} "
                "(lista de criptas, datos generales, páginas, versiones y reintentos 429)")

    agregar("-- Caché --")
    cache = red.estadisticas_cache()
    if sesion.esqueleto_desde_cache is not None:
        agregar("esqueleto: " + ("desde caché en disco" if sesion.esqueleto_desde_cache
                                 else "descargado de la fuente"))
    agregar(f"salas_incorporadas: {_valor(cache, 'salas_incorporadas')} "
            f"({_valor(contadores, 'salas_desde_disco')} desde disco, "
            f"{_valor(contadores, 'salas_desde_red')} desde la fuente)")
    agregar(f"fichas_lru_aciertos: {_valor(cache, 'aciertos')}")
    agregar(f"fichas_lru_fallos: {_valor(cache, 'fallos')}")
    agregar(f"fichas_fallos_resueltos: {_valor(contadores, 'fichas_desde_disco')} desde disco, "
            f"{_valor(contadores, 'fichas_desde_red')} desde la fuente")
    agregar(f"fichas_lru: {_valor(cache, 'en_memoria')} en memoria de "
            f"{_valor(cache, 'capacidad')}, {_valor(cache, 'desalojos')} desalojos")

    agregar("-- Precarga --")
    agregar(f"esperas_bloqueantes: {_valor(contadores, 'esperas_bloqueantes')}")
    agregar(f"precargas_fallidas: {_valor(contadores, 'precargas_fallidas')}")
    return lineas


def formatear(numero, lineas):
    """Una sola función da el texto del reporte para la pantalla y el archivo."""
    texto = f"{INICIO_BLOQUE}{numero}{FIN_BLOQUE}"
    for linea in lineas:
        texto += "\n" + linea
    return texto


class ReporteGuardado:
    def __init__(self, numero, texto):
        self.numero = numero
        self.texto = texto


class HistorialReportesRed:
    """Archivo de texto con los últimos reportes, el más reciente primero."""

    def __init__(self, ruta=None, capacidad=CAPACIDAD_HISTORIAL):
        self.ruta = ruta or RUTA_POR_DEFECTO
        self.capacidad = capacidad

    def _leer_bloques(self):
        """Vector de ReporteGuardado en el orden del archivo (más reciente primero)."""
        bloques = Vector()
        if not os.path.exists(self.ruta):
            return bloques
        with open(self.ruta, encoding="utf-8") as f:
            primera = f.readline().rstrip("\n")
            if not primera.startswith(MARCA):
                raise ValueError(f"'{self.ruta}' no es un historial de reportes de red.")
            numero, texto = None, ""
            for linea in f:
                linea = linea.rstrip("\n")
                if linea.startswith(INICIO_BLOQUE) and linea.endswith(FIN_BLOQUE):
                    if numero is not None:
                        bloques.agregarValor(ReporteGuardado(numero, texto.rstrip("\n")))
                    numero = int(linea[len(INICIO_BLOQUE):-len(FIN_BLOQUE)])
                    texto = linea
                elif numero is not None:
                    texto += "\n" + linea
            if numero is not None:
                bloques.agregarValor(ReporteGuardado(numero, texto.rstrip("\n")))
        return bloques

    def cargar(self):
        """Pila con el historial; el tope es el reporte más reciente."""
        pila = Pila(self.capacidad)
        bloques = self._leer_bloques()
        for i in range(len(bloques) - 1, -1, -1):     # del más viejo al más nuevo
            pila.apilar_elemento(bloques.obtenerValor(i))
        return pila

    def agregar(self, lineas):
        """Apila un reporte nuevo y reescribe el archivo. Devuelve (numero, texto)."""
        pila = self.cargar()
        tope = pila.ver_tope()
        numero = 1 if tope is None else tope.numero + 1
        texto = formatear(numero, lineas)
        pila.apilar_elemento(ReporteGuardado(numero, texto))
        self._guardar(pila)
        return numero, texto

    def _guardar(self, pila):
        carpeta = os.path.dirname(self.ruta)
        if carpeta:
            os.makedirs(carpeta, exist_ok=True)
        temporal = self.ruta + ".tmp"
        with open(temporal, "w", encoding="utf-8") as f:
            f.write(f"{MARCA} (más reciente primero; se guardan los últimos {self.capacidad})\n")
            reporte = pila.desapilar_elemento()
            while reporte is not None:
                f.write("\n" + reporte.texto + "\n")
                reporte = pila.desapilar_elemento()
        os.replace(temporal, self.ruta)

    def leer(self):
        """Reportes del más reciente al más antiguo."""
        return self._leer_bloques()


def registrar_reporte(fuente, sesion, modo, motivo, ruta=None, bitacora=None, ahora=None):
    """Arma el reporte, lo apila en el historial y devuelve el texto a mostrar.
    Si el archivo no se puede escribir, el reporte igual se devuelve para pantalla."""
    lineas = construir_reporte(fuente, sesion, modo, motivo, ahora=ahora, bitacora=bitacora)
    historial = HistorialReportesRed(ruta)
    try:
        numero, texto = historial.agregar(lineas)
    except (OSError, ValueError) as error:
        return formatear("?", lineas) + f"\n(no se pudo guardar en {historial.ruta}: {error})"
    return texto + f"\n(guardado en {historial.ruta})"
