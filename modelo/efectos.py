"""Efectos temporales programados en el reloj de la partida.

Los cambios se registran mediante los deltas del historial compartido.
El objeto o la entidad que aplica un efecto aporta sus parámetros, como
el daño del veneno o la duración de una antorcha.

El veneno reinicia sus pulsos al aplicarse de nuevo. Con intervalo 80 y
duración 400 se ejecutan cinco pulsos, incluido el del instante 400.
Un antídoto cancela las entradas pendientes antes del siguiente pulso.
Estas reglas están documentadas en docs/decisiones/4.06.txt.
"""
from modelo.deltas import DeltaAtributos
from modelo.reloj import entero
from modelo.ejecutor_evento import EjecutorEvento

INTERVALO_VENENO = 80
DURACION_VENENO = 400
PULSOS_VENENO = DURACION_VENENO // INTERVALO_VENENO  # 5


class EstadoVeneno:
    """Daño y pulsos restantes del veneno activo. No es la agenda del reloj."""

    def __init__(self, dano_por_pulso, pulsos_restantes):
        self.dano_por_pulso = dano_por_pulso
        self.pulsos_restantes = pulsos_restantes


def _entrada_pendiente(entrada):
    return entrada is not None and entrada.valido and entrada._en_heap


def aplicar_veneno(reloj, actor, dano_por_pulso, pulsos=PULSOS_VENENO,
                    intervalo=INTERVALO_VENENO):
    """Envenena a actor; si ya estaba envenenado, reinicia el conteo (política
    de reaplicación fijada arriba). dano_por_pulso lo decide quien llama.
    """
    entero(dano_por_pulso, 'daño del veneno', 1)
    entero(pulsos, 'pulsos de veneno', 1)
    entero(intervalo, 'intervalo de veneno', 1)
    if not actor.vivo:
        return False
    reloj.vincular_actor(actor)
    if _entrada_pendiente(actor.evento_veneno):
        reloj.cancelar(actor.evento_veneno)
    reloj.registrar(DeltaAtributos(actor, 'estado_veneno'))
    actor.estado_veneno = EstadoVeneno(dano_por_pulso, pulsos)
    _programar_pulso_veneno(reloj, actor, intervalo)
    return True


def _programar_pulso_veneno(reloj, actor, intervalo):
    tiempo = reloj.tiempo_actual + intervalo

    pulso = EjecutorEvento('veneno', actor, intervalo)

    reloj.programar_en(tiempo, pulso, tipo='veneno', dueno=actor,
                        campo='evento_veneno', efecto=True)


def cancelar_veneno(reloj, actor):
    """Antídoto u otro efecto que cure el veneno antes del próximo pulso."""
    if not _entrada_pendiente(actor.evento_veneno):
        return False
    reloj.cancelar(actor.evento_veneno)
    reloj.registrar(DeltaAtributos(actor, 'estado_veneno'))
    actor.estado_veneno = None
    return True

# --------------------------------------------------------------------------- 
# Cambio temporal de velocidad
# ---------------------------------------------------------------------------

def aplicar_modificador_velocidad(reloj, actor, modificador, duracion):
    """Aplica un cambio temporal de velocidad.

    Tanto al comenzar como al terminar, reprograma la próxima acción
    para conservar el progreso del turno.
    """
    entero(duracion, 'duración del modificador', 1)
    if not actor.vivo:
        return False
    if _entrada_pendiente(actor.evento_mod_velocidad):
        raise ValueError(
            'Ya hay un modificador de velocidad activo; cancélalo antes de aplicar otro.'
        )
    velocidad_original = actor.velocidad
    nueva = velocidad_original + modificador
    if nueva < 1:
        raise ValueError('El modificador deja la velocidad en cero o negativa.')

    reloj.reprogramar_por_velocidad(actor, nueva)

    tiempo = reloj.tiempo_actual + duracion

    fin = EjecutorEvento('velocidad', actor, velocidad_original)

    reloj.programar_en(tiempo, fin, tipo='fin_modificador_velocidad', dueno=actor,
                        campo='evento_mod_velocidad', efecto=True)
    return True

# --------------------------------------------------------------------------- 
# Antorcha
# ---------------------------------------------------------------------------

def apagar_antorcha(reloj, antorcha):
    """Apagado voluntario reversible; la unidad sigue venciendo a la misma hora."""
    if not antorcha.encendida:
        return False
    reloj.registrar(DeltaAtributos(antorcha, 'encendida'))
    antorcha.encendida = False
    return True


def encender_antorcha(reloj, antorcha):
    """Enciende la antorcha y programa su propio apagado tras `duracion`."""
    if antorcha.encendida:
        return False
    pendiente = _entrada_pendiente(antorcha.evento_apagado)
    if pendiente:
        # Se reanuda la misma unidad de uso, hasta el vencimiento original.
        reloj.registrar(DeltaAtributos(antorcha, 'encendida'))
        antorcha.encendida = True
        return True
    if getattr(antorcha, 'usos_restantes', 1) <= 0:
        return False
    if not hasattr(antorcha, 'usos_restantes'):
        antorcha.usos_restantes = 1
    reloj.registrar(DeltaAtributos(antorcha, 'encendida', 'usos_restantes'))
    antorcha.encendida = True
    antorcha.usos_restantes -= 1

    tiempo = reloj.tiempo_actual + antorcha.duracion

    apagar = EjecutorEvento('antorcha', antorcha)

    reloj.programar_en(tiempo, apagar, tipo='apagado_antorcha', dueno=antorcha,
                        campo='evento_apagado', efecto=False)
    return True


# --------------------------------------------------------------------------- 
# Regeneración
# ---------------------------------------------------------------------------

INTERVALO_REGENERACION = 200


def iniciar_regeneracion(reloj, enemigo):
    """Activa la regeneración periódica de un enemigo con ficha.regeneracion
    > 0. Se llama explícitamente al activar al enemigo (Partida), no al
    crearlo: antes de eso no hay reloj corriendo donde programar el pulso.
    """
    if enemigo.regeneracion <= 0 or not enemigo.vivo:
        return False
    if _entrada_pendiente(enemigo.evento_regeneracion):
        return False
    _programar_pulso_regeneracion(reloj, enemigo)
    return True


def _programar_pulso_regeneracion(reloj, enemigo):
    tiempo = reloj.tiempo_actual + INTERVALO_REGENERACION

    pulso = EjecutorEvento('regeneracion', enemigo)

    reloj.programar_en(tiempo, pulso, tipo='regeneracion', dueno=enemigo,
                        campo='evento_regeneracion', efecto=True)


# --------------------------------------------------------------------------- 
# Conector con Partida.aplicar_efecto (f(partida, objeto) -> bool)
# ---------------------------------------------------------------------------

def aplicar_efecto_objeto(partida, objeto):
    """Aplica el efecto del objeto que Partida.usar_objeto acaba de validar.

    Resuelve pociones de velocidad, antídotos y antorchas; Partida se encarga
    de decidir cuándo usar el objeto y de consumirlo si corresponde.
    """
    reloj, jugador = partida.reloj, partida.jugador
    if objeto.clase == 'pocion':
        return aplicar_modificador_velocidad(
            reloj, jugador, objeto.modificador_velocidad, objeto.duracion)
    if objeto.clase == 'antidoto':
        return cancelar_veneno(reloj, jugador)
    if objeto.clase == 'antorcha':
        return encender_antorcha(reloj, objeto)
    return False