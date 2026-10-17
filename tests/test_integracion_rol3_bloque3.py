"""Integración del modelo con datos offline, sin pasar por el bucle de consola."""
from adaptadores.datos_offline import DatosOffline
from controlador.controlador_red import cargar_esqueleto_completo, ControladorRed
from estructuras.vector_dinamico import Vector
from estructuras.ordenamientos import ordenar
from modelo.entidades.jugador import Jugador
from modelo.deltas import DeltaAtributos, DeltaListaSimple
from modelo.historial import Historial
from modelo.reloj import Reloj
from modelo.rastro import Rastro
from modelo.entorno import Entorno


def test_sala_offline_activar_enemigos_trampa_y_revertir(tmp_path):
    fuente = DatosOffline()
    cripta = cargar_esqueleto_completo(fuente,'cripta-01')
    red = ControladorRed(fuente,cripta,tmp_path)
    red.solicitar_contenido_lote([1,2])
    h = Historial()
    reloj = Reloj(51,h)
    rastro = Rastro(cripta,h)
    inicial, destino = cripta.sala_por_id(1),cripta.sala_por_id(2)
    jugador = Jugador.desde_generales(fuente.datos_cripta(cripta.id),inicial)
    reloj.vincular_actor(jugador)
    rastro.registrar(inicial.id,0)
    vida_inicial = jugador.vida
    turno = reloj.programar_inicial(jugador,lambda _: None)
    enemigos = Vector()
    for enemigo in destino.enemigos_dormidos:
        enemigos.agregarValor(enemigo)
    ordenar(enemigos,lambda a,b:(a.instancia_id>b.instancia_id)-(a.instancia_id<b.instancia_id))
    h.iniciar_accion(reloj)
    reloj.tomar_turno(jugador)
    h.registrar(DeltaAtributos(jugador,'sala_actual'))
    jugador.sala_actual = destino
    rastro.registrar(destino.id,reloj.tiempo_actual)
    Entorno(reloj).al_entrar(jugador,destino)
    for enemigo in enemigos:
        for lista in (destino.enemigos_dormidos,destino.enemigos_activos):
            h.registrar(DeltaListaSimple(lista,enemigo))
        destino.enemigos_dormidos.eliminar_valor(enemigo)
        destino.enemigos_activos.insertar_al_final(enemigo)
        def actuar(r, e=enemigo):
            if e.vivo and jugador.vivo:
                jugador.recibir_dano(r.calcular_dano(e.ataque,jugador.defensa))
        reloj.programar(enemigo,100,actuar)
    reloj.programar(jugador,100,lambda _: None)
    reloj.avanzar_hasta_turno(jugador)
    h.confirmar_accion()
    assert jugador.vida < vida_inicial
    assert len(destino.enemigos_activos) == 2
    h.revertir()
    assert jugador.vida == vida_inicial and jugador.sala_actual is inicial
    assert destino.tiempo_rastro == -1 and inicial.tiempo_rastro == 0
    assert len(destino.enemigos_dormidos) == 2 and len(destino.enemigos_activos) == 0
    assert reloj.proximo() is turno and reloj.tiempo_actual == 0
    assert all(t.armada for t in destino.trampas)
    assert red.contenido_cargado(2)  # La caché y contenido cargado no se deshacen.
