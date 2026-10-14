
"""Efectos temporales y periódicos de los actores."""

INTERVALO_VENENO = 80
DURACION_VENENO = 400
INTERVALO_REGENERACION = 200


def _validar_entero(valor, nombre, minimo=0):
    """Valida valores enteros usados por los efectos."""
    if type(valor) is not int or valor < minimo:
        raise ValueError(f"{nombre} debe ser un entero >= {minimo}.")


def aplicar_veneno(actor, reloj, dano):
    """Inflige daño cada 80 unidades durante 400 unidades."""
    _validar_entero(dano, "El daño", 0)

    if not actor.vivo:
        return

    tiempo_final = reloj.tiempo_actual + DURACION_VENENO

    def ejecutar_veneno(reloj_actual):
        if not actor.vivo:
            return

        actor.recibir_dano(dano)

        siguiente = reloj_actual.tiempo_actual + INTERVALO_VENENO

        if siguiente <= tiempo_final and actor.vivo:
            reloj_actual.programar_en(
                siguiente,
                ejecutar_veneno,
                tipo="veneno",
                dueno=actor,
                efecto=True,
            )

    reloj.programar_en(
        reloj.tiempo_actual + INTERVALO_VENENO,
        ejecutar_veneno,
        tipo="veneno",
        dueno=actor,
        efecto=True,
    )


def cancelar_veneno(actor, reloj):
    """Cancela todos los eventos de veneno pendientes del actor."""
    nodo = actor.eventos_efectos.head()

    while nodo is not None:
        siguiente = nodo.siguiente
        entrada = nodo.valor

        if entrada.dato.tipo == "veneno":
            reloj.cancelar(entrada)

        nodo = siguiente


def aplicar_regeneracion(actor, reloj, cantidad, duracion):
    """Cura al actor cada 200 unidades hasta finalizar la duración."""
    _validar_entero(cantidad, "La cantidad de regeneración", 0)
    _validar_entero(duracion, "La duración", 1)

    if not actor.vivo:
        return

    tiempo_final = reloj.tiempo_actual + duracion

    def ejecutar_regeneracion(reloj_actual):
        if not actor.vivo:
            return

        actor.curar(cantidad)

        siguiente = reloj_actual.tiempo_actual + INTERVALO_REGENERACION

        if siguiente <= tiempo_final and actor.vivo:
            reloj_actual.programar_en(
                siguiente,
                ejecutar_regeneracion,
                tipo="regeneracion",
                dueno=actor,
                efecto=True,
            )

    reloj.programar_en(
        reloj.tiempo_actual + INTERVALO_REGENERACION,
        ejecutar_regeneracion,
        tipo="regeneracion",
        dueno=actor,
        efecto=True,
    )


def aplicar_velocidad(actor, reloj, modificador, duracion):
    """Modifica temporalmente la velocidad y luego la restaura."""
    if type(modificador) not in (int, float):
        raise ValueError("El modificador debe ser numérico.")

    _validar_entero(duracion, "La duración", 1)

    if not actor.vivo or modificador == 0:
        return

    velocidad_anterior = actor.velocidad
    nueva_velocidad = velocidad_anterior + modificador

    if nueva_velocidad <= 0:
        raise ValueError("La velocidad resultante debe ser positiva.")

    reloj.reprogramar_por_velocidad(actor, nueva_velocidad)

    def restaurar_velocidad(reloj_actual):
        if actor.vivo:
            reloj_actual.reprogramar_por_velocidad(
                actor,
                velocidad_anterior,
            )

    reloj.programar_en(
        reloj.tiempo_actual + duracion,
        restaurar_velocidad,
        tipo="restaurar_velocidad",
        dueno=actor,
        efecto=True,
    )


def usar_pocion(actor, pocion, reloj):
    """Aplica la curación y el modificador de una poción."""
    if not actor.vivo:
        return

    if pocion.cura > 0:
        actor.curar(pocion.cura)

    if pocion.modificador_velocidad != 0:
        aplicar_velocidad(
            actor,
            reloj,
            pocion.modificador_velocidad,
            pocion.duracion,
        )
