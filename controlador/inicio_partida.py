"""Arranque de una partida nueva: red/disco + semilla + bitácora + Partida.

Orden (presupuesto de red mínimo):
  1. Datos generales (una solicitud): versión, presupuesto y estadísticas del jugador.
  2. Esqueleto: desde caché si la versión sigue vigente; si no, páginas + versión.
  3. Primer lote: sala inicial + precarga de vecinas (y vecinas de vecinas) en UNA
     solicitud de contenido; el catálogo de todo el lote se resuelve en lotes de 10.
  4. Semilla: generada aquí (partida nueva) o recibida (replay / carga).
  5. Partida.inicializar(): rastro t=0, jugador en t=0, enemigos de la sala inicial.
  6. Bitácora: encabezado con cripta, versiones y semilla (si se pide ruta).

La partida queda lista para que el controlador del juego (ROL 4) llame
reloj.avanzar_hasta_turno(jugador) y pida la primera decisión.
"""
import os

from bitacora_partida import BitacoraPartida
from controlador.controlador_red import ControladorRed, cargar_cripta, _generales
from controlador.semilla import generar_semilla, validar_semilla
from modelo.entidades.jugador import Jugador
from modelo.entidades.objetos.fabrica_objetos import FabricaObjetos
from modelo.partida import Partida


class SesionPartida:
    """Lo que el controlador del juego necesita después del arranque."""

    def __init__(self, partida, red, fuente, bitacora=None):
        self.partida = partida
        self.red = red
        self.fuente = fuente
        self.bitacora = bitacora


def ruta_bitacora_por_defecto(cripta_id, semilla, carpeta=None):
    if carpeta is None:
        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        carpeta = os.path.join(raiz, "partidas", "bitacoras")
    return os.path.join(carpeta, f"{cripta_id}_{semilla}.log")


class _FuenteConGenerales:
    """Entrega a cargar_cripta los datos generales ya pedidos, sin repetir la
    solicitud; todo lo demás va a la fuente real."""

    def __init__(self, fuente, generales):
        self._fuente = fuente
        self._generales = generales

    def datos_cripta(self, cripta_id):
        return self._generales

    def __getattr__(self, nombre):
        return getattr(self._fuente, nombre)


def _version_catalogo(red):
    """Texto de la versión del catálogo; la fuente la entrega como {"version": ...}.

    Reutiliza la que ControladorRed ya obtuvo al resolver el catálogo del lote.
    (Cuando se trabaje controlador_red.py conviene exponerlo como método público.)
    """
    version = red._persistencia_catalogo().version
    if isinstance(version, dict):
        version = version.get("version")
    return version


def _resolvedor_fichas(red):
    """resolver_ficha para la Partida: memoria (LRU) -> disco -> red."""
    def resolver(tipo_id):
        ficha = red.ficha(tipo_id)
        if ficha is None:
            red.resolver_catalogo([tipo_id])
            ficha = red.ficha(tipo_id)
        return ficha
    return resolver


def _validar_jugador(generales):
    datos = generales.get("jugador")
    if not isinstance(datos, dict):
        raise ValueError("Datos de cripta inválidos: faltan las estadísticas del jugador.")
    for campo in ("vida_max", "ataque", "defensa", "velocidad"):
        if type(datos.get(campo)) is not int:
            raise ValueError(f"Datos de cripta inválidos: jugador.{campo} debe ser entero.")


def nueva_partida(fuente, cripta_id, carpeta_cache=None, semilla=None,
                  ruta_bitacora=None, cache_size=25):
    """Crea e inicializa una partida. Devuelve SesionPartida.

    semilla=None  -> partida nueva: se genera automáticamente (nunca la elige el jugador).
    semilla=int   -> replay o carga: se reutiliza la guardada.
    ruta_bitacora -> si se da, se crea la bitácora append-only con la semilla en el
                     encabezado. Use ruta_bitacora_por_defecto(...) para la ubicación
                     estándar.
    """
    semilla = generar_semilla() if semilla is None else validar_semilla(semilla)

    generales = _generales(fuente, cripta_id)        # 1 solicitud
    _validar_jugador(generales)
    cripta, _ = cargar_cripta(_FuenteConGenerales(fuente, generales), cripta_id, carpeta_cache)

    fabrica = FabricaObjetos()                        # una sola por partida
    red = ControladorRed(fuente, cripta, carpeta_cache, fabrica=fabrica,
                         cache_size=cache_size)
    sala_inicial = cripta.sala_por_id(cripta.sala_inicial_id)
    # Encolar vecinas ANTES: garantizar_contenido completa el lote con ellas y todo
    # viaja en una sola solicitud de contenido.
    red.planificar_precarga(sala_inicial)
    red.garantizar_contenido(sala_inicial.id)
    # Para la bitácora; normalmente ya se obtuvo al resolver el catálogo del lote.
    version_catalogo = _version_catalogo(red)

    jugador = Jugador.desde_generales(generales, sala_inicial)
    partida = Partida(cripta, jugador, semilla, version_catalogo,
                      fabrica=fabrica, resolver_ficha=_resolvedor_fichas(red))
    partida.al_morir_enemigo.agregarValor(red.notificar_muerte_enemigo)
    partida.inicializar()

    bitacora = None
    if ruta_bitacora is not None:
        bitacora = BitacoraPartida.partida_nueva(
            ruta_bitacora, cripta.id, cripta.version, version_catalogo, semilla)
    return SesionPartida(partida, red, fuente, bitacora)
