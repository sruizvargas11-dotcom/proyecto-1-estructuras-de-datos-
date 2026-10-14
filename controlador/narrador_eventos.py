def _nombre_enemigo(partida, actor):
    return partida.nombre_enemigo(actor)


def _en_sala_del_jugador(partida, actor):
    return getattr(actor, "sala_actual", None) is partida.jugador.sala_actual


def _salida_visible(partida, salida):
    """La puerta es de la sala del jugador o conduce a ella."""
    sala = partida.jugador.sala_actual
    if salida.sala_destino_id == sala.id:
        return True
    for propia in sala.salidas:
        if propia is salida:
            return True
    return False


def _trampa_visible(partida, trampa):
    for propia in partida.jugador.sala_actual.trampas:
        if propia is trampa:
            return True
    return False


def describir_evento(partida, evento, vida_antes=None):
    """Texto del evento ya ejecutado, o None si el jugador no lo percibe. """
    tipo, dueno = evento.tipo, evento.dueno
    jugador = partida.jugador

    if tipo == "veneno":
        perdida = 0 if vida_antes is None else vida_antes - dueno.vida
        if dueno is jugador:
            texto = f"El veneno te quema: -{perdida} de vida."
            if dueno.vivo and getattr(dueno, "estado_veneno", None) is None:
                texto += " El veneno se disipa."
            return texto
        if _en_sala_del_jugador(partida, dueno):
            return f"{_nombre_enemigo(partida, dueno)} sufre el veneno: -{perdida} de vida."
        return None

    if tipo == "regeneracion":
        if not _en_sala_del_jugador(partida, dueno):
            return None
        ganada = 0 if vida_antes is None else dueno.vida - vida_antes
        if ganada <= 0:
            return None
        return f"{_nombre_enemigo(partida, dueno)} se regenera: +{ganada} de vida."

    if tipo == "fin_modificador_velocidad":
        if dueno is jugador:
            return f"El efecto de la poción termina: velocidad {jugador.velocidad}."
        if _en_sala_del_jugador(partida, dueno):
            return f"{_nombre_enemigo(partida, dueno)} recupera su velocidad normal."
        return None

    if tipo == "apagado_antorcha":
        return f"Tu {dueno.nombre.lower()} se apaga."

    if tipo == "rearme_trampa":
        if _trampa_visible(partida, dueno):
            return f"Un chasquido: {dueno.nombre} vuelve a estar armada."
        return None

    if tipo == "cierre_puerta":
        if _salida_visible(partida, dueno):
            return "Una puerta de la sala se cierra sola."
        return None

    return None
