import random

from estructuras.vector_dinamico import Vector


def _actor(actor):
    veneno = getattr(actor, "estado_veneno", None)
    veneno = "-" if veneno is None else f"{veneno.dano_por_pulso}x{veneno.pulsos_restantes}"
    return (f"{actor.instancia_id}:{actor.vida}/{actor.vida_max}:{actor.ataque}:"
            f"{actor.defensa}:{actor.velocidad}:{actor.tiempo_siguiente}:{veneno}")


def _ids(lista):
    return ",".join(str(x.instancia_id) for x in lista)


def _siguiente_azar(reloj):
    """Próximo valor que daría el PRNG, sacado de una copia: no altera la partida."""
    copia = random.Random(0)
    copia.setstate(reloj.azar.getstate())
    return copia.getrandbits(64)


def lineas_estado(partida):
    """Estado observable de la partida como líneas de texto en orden fijo
    (salas por id). Dos partidas coinciden si y solo si coinciden sus líneas."""
    jugador = partida.jugador
    lineas = Vector()
    agregar = lineas.agregarValor
    agregar(f"estado={partida.estado} t={partida.tiempo} acciones={partida.acciones_jugador} "
            f"derrotados={partida.enemigos_derrotados}")
    agregar(f"jugador={_actor(jugador)} sala={jugador.sala_actual.id} "
            f"arma={getattr(jugador.arma_equipada, 'instancia_id', '-')} "
            f"armadura={getattr(jugador.armadura_equipada, 'instancia_id', '-')}")
    agregar("inventario=" + ",".join(str(n.valor.instancia_id)
                                     for n in jugador.inventario.recorrer_desde_frente()))
    for sala in partida.cripta.recorrer_salas():
        enemigos = ";".join(_actor(e) for e in sala.enemigos_activos)
        trampas = ",".join(f"{t.instancia_id}:{int(t.armada)}" for t in sala.trampas)
        salidas = ",".join(f"{s.direccion}:{int(s.cerrada)}" for s in sala.salidas)
        agregar(f"sala{sala.id} rastro={sala.tiempo_rastro} enemigos={enemigos} "
                f"dormidos={_ids(sala.enemigos_dormidos)} suelo={_ids(sala.objetos_suelo)} "
                f"trampas={trampas} salidas={salidas}")
    agregar(f"azar_siguiente={_siguiente_azar(partida.reloj)}")
    return lineas


def primera_diferencia(esperadas, obtenidas):
    """None si son iguales; si no, (numero_de_linea, esperada, obtenida)."""
    total = max(len(esperadas), len(obtenidas))
    for i in range(total):
        a = esperadas.obtenerValor(i) if i < len(esperadas) else "(no existe)"
        b = obtenidas.obtenerValor(i) if i < len(obtenidas) else "(no existe)"
        if a != b:
            return i + 1, a, b
    return None
