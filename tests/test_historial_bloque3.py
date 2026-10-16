"""Deshacer intervalos completos, eventos, azar, objetos y pergaminos."""
import pytest
from modelo.historial import Historial, GrupoDeltas
from modelo.deltas import DeltaAtributos, DeltaObjeto, DeltaListaSimple
from modelo.reloj import Reloj
from modelo.rastro import Rastro
from modelo.entorno import Entorno
from modelo.entidades.jugador import Jugador
from modelo.entidades.objetos.fabrica_objetos import FabricaObjetos
from modelo.entidades.trampa import Trampa
from modelo.mundo.sala import Sala
from modelo.mundo.salida import Salida
from tests.test_rol3_bloque3 import actor, nada, mapa


def sistema():
    h = Historial()
    r = Reloj(73,h)
    sala = Sala(1,'inicio')
    jugador = Jugador('j',100,10,2,100,20,sala)
    r.vincular_actor(jugador)
    return h,r,jugador,sala


def objeto(fabrica, clase='arma'):
    return fabrica.crear({'id':clase,'clase':clase,'nombre':clase,
                         'peso':1,'valor':2,'ataque_bonus':3})


def inventario(j):
    return [n.valor.instancia_id for n in j.inventario.recorrer_desde_frente()]


def pendientes(r):
    # En tests se permite sorted como oráculo independiente, nunca en producción.
    return sorted((e.tiempo,e.secuencia,e.dato.tipo) for e in r.agenda._datos if e.valido)


def test_grupo_invierte_orden_sin_copia_estado():
    registro = []
    class D:
        def __init__(self, n): self.n=n
        def revertir(self): registro.append(self.n)
    g = GrupoDeltas()
    for n in (1,2,3): g.agregar(D(n))
    g.revertir_todo()
    assert registro == [3,2,1] and len(g) == 0
    g.revertir_todo()
    assert registro == [3,2,1]


def test_historial_solo_ultimas_cinco_y_no_registra_fuera_intervalo():
    h,r,j,_ = sistema()
    j.recibir_dano(1)
    assert len(h) == 0
    for _ in range(7):
        h.iniciar_accion(r)
        j.recibir_dano(1)
        h.confirmar_accion()
    assert j.vida == 92 and len(h) == 5
    assert h._grupos.contador_descartes_por_limite == 2
    for _ in range(5): assert h.revertir()
    assert j.vida == 97 and not h.revertir()


def test_intervalo_211_vida_veneno_rearme_tiempo_agenda():
    h,r,j,s = sistema()
    rata = actor()
    r.vincular_actor(rata)
    r.avanzar_y_ejecutar(100)
    trampa = Trampa('t','t','t',2,80)
    Entorno(r).activar_trampa(trampa,j)  # Rearme en 180; estado previo desarmada.
    r.programar_en(120,lambda _: j.recibir_dano(2),tipo='veneno',dueno=j)
    r.programar_en(150,lambda _: j.recibir_dano(4),tipo='accion_rata',dueno=rata,efecto=False)
    antes = pendientes(r)
    h.iniciar_accion(r)
    rata.recibir_dano(7)
    r.avanzar_y_ejecutar(200)
    h.confirmar_accion()
    assert j.vida == 92 and rata.vida == 93 and trampa.armada
    assert h.revertir()
    assert j.vida == 98 and rata.vida == 100 and not trampa.armada
    assert r.tiempo_actual == 100 and pendientes(r) == antes
    assert trampa.evento_rearme.valido


def test_revertir_muerte_restaura_handles_y_efectos_cancelados_ya_limpiados():
    h,r,j,_ = sistema()
    accion = r.programar(j,100,nada)
    efecto = r.programar_en(80,lambda _: j.recibir_dano(2),tipo='veneno',dueno=j)
    h.iniciar_accion(r)
    j.recibir_dano(100)
    assert not j.vivo and j.evento_actual is None and len(j.eventos_efectos) == 0
    assert r.proximo() is None  # Los cancelados ya salieron físicamente del heap.
    h.confirmar_accion()
    h.revertir()
    assert j.vivo and j.vida == 100 and j.evento_actual is accion
    assert efecto.valido and len(j.eventos_efectos) == 1
    assert r.proximo() is efecto
    r.avanzar_y_ejecutar(80)
    assert j.vida == 98


def test_revertir_velocidad_y_fin_de_efecto_restaura_seq():
    h,r,j,_ = sistema()
    original = r.programar(j,100,nada)
    h.iniciar_accion(r)
    r.reprogramar_por_velocidad(j,200)
    fin = r.programar_en(20,lambda reloj: reloj.reprogramar_por_velocidad(j,100),
                        tipo='fin_velocidad',dueno=j)
    r.avanzar_y_ejecutar(20)
    assert j.velocidad == 100 and j.tiempo_siguiente == 80
    h.confirmar_accion()
    h.revertir()
    assert j.velocidad == 100 and j.tiempo_siguiente == 100
    assert j.evento_actual is original and original.valido
    assert pendientes(r) == [(100,0,'accion')]
    assert not fin.valido and r.agenda.siguiente_secuencia == 1


def test_pulso_recurrente_y_cancelacion_reversible_sin_duplicados():
    h,r,j,_ = sistema()
    def pulso(reloj):
        j.recibir_dano(2)
        if reloj.tiempo_actual < 400 and j.vivo:
            reloj.programar_en(reloj.tiempo_actual+80,pulso,tipo='pulso',dueno=j)
    original = r.programar_en(80,pulso,tipo='pulso',dueno=j)
    h.iniciar_accion(r)
    r.avanzar_y_ejecutar(160)
    futuro = r.proximo()
    r.cancelar(futuro)  # Cancela el veneno como lo haría un antídoto.
    r.proximo()        # fuerza descarte físico
    h.confirmar_accion()
    h.revertir()
    assert j.vida == 100 and len(j.eventos_efectos) == 1
    assert r.proximo() is original
    assert pendientes(r) == [(80,0,'pulso')]
    r.avanzar_y_ejecutar(80)
    assert j.vida == 98 and len(j.eventos_efectos) == 1


def test_azar_y_secuencia_reproducen_la_accion_tras_deshacer():
    h,r,j,_ = sistema()
    def ejecutar():
        h.iniciar_accion(r)
        dano = r.calcular_dano(10,2)
        eleccion = r.azar.randrange(4)
        j.recibir_dano(dano)
        evento = r.programar(j,100,nada)
        h.confirmar_accion()
        return dano,eleccion,evento.secuencia
    a = ejecutar()
    h.revertir()
    assert j.vida == 100 and r.proximo() is None
    b = ejecutar()
    assert a == b
    assert len(pendientes(r)) == 1


def test_revertir_recoger_soltar_y_equipar_conserva_nodos_y_orden():
    h,r,j,sala = sistema()
    f = FabricaObjetos()
    a,b,c = [objeto(f) for _ in range(3)]
    for o in (a,b,c): sala.objetos_suelo.insertar_al_final(o)
    j.recoger(a)
    j.recoger(b)
    original = j.buscar_nodo(a.instancia_id)
    j.cursor = original
    orden = inventario(j)
    h.iniciar_accion(r)
    j.equipar_nodo(original)
    j.soltar_nodo(original)
    j.recoger(c)
    j.equipar(c.instancia_id)
    h.confirmar_accion()
    h.revertir()
    assert inventario(j) == orden
    assert j.buscar_nodo(a.instancia_id) is original and j.cursor is original
    assert list(sala.objetos_suelo) == [c]
    assert j.arma_equipada is None and j.ataque == 10


def test_dos_pergaminos_no_reaparecen_y_recoleccion_queda_excluida():
    h,r,j,sala = sistema()
    f = FabricaObjetos()
    a,b = objeto(f,'pergamino_retroceso'),objeto(f,'pergamino_retroceso')
    sala.objetos_suelo.insertar_al_final(a)
    sala.objetos_suelo.insertar_al_final(b)
    h.iniciar_accion(r)
    j.recoger(a)
    j.recibir_dano(3)
    r.avanzar_y_ejecutar(25)
    h.confirmar_accion()
    h.iniciar_accion(r)
    j.recoger(b)
    j.recibir_dano(4)
    r.avanzar_y_ejecutar(50)
    h.confirmar_accion()
    assert h.usar_pergamino(j,j.buscar_nodo(a.instancia_id))
    assert inventario(j) == [b.instancia_id] and list(sala.objetos_suelo) == []
    assert j.vida == 97 and r.tiempo_actual == 25
    assert h.usar_pergamino(j,j.buscar_nodo(b.instancia_id))
    assert len(j.inventario) == 0 and list(sala.objetos_suelo) == []
    assert j.vida == 100 and r.tiempo_actual == 0 and len(h) == 0
    assert j.cursor is None


def test_soltar_pergamino_tambien_queda_fuera_de_reversion():
    h,r,j,sala = sistema()
    f = FabricaObjetos()
    a,b = objeto(f,'pergamino_retroceso'),objeto(f,'pergamino_retroceso')
    for o in (a,b):
        sala.objetos_suelo.insertar_al_inicio(o)
        j.recoger(o)
    h.iniciar_accion(r)
    j.soltar(a.instancia_id)
    j.recibir_dano(1)
    h.confirmar_accion()
    h.usar_pergamino(j,j.buscar_nodo(b.instancia_id))
    assert len(j.inventario) == 0 and list(sala.objetos_suelo) == [a]
    assert j.vida == 100


def test_cursor_no_apunta_al_pergamino_consumido_tras_otro_delta():
    h,r,j,sala = sistema()
    f = FabricaObjetos()
    perg,arma = objeto(f,'pergamino_retroceso'),objeto(f)
    for o in (perg,arma):
        sala.objetos_suelo.insertar_al_inicio(o)
        j.recoger(o)
    j.cursor = j.buscar_nodo(perg.instancia_id)
    h.iniciar_accion(r)
    j.equipar(arma.instancia_id)
    h.confirmar_accion()
    h.usar_pergamino(j,j.buscar_nodo(perg.instancia_id))
    assert inventario(j) == [arma.instancia_id]
    assert j.inventario.pertenece(j.cursor)


def test_rearme_y_puerta_se_revierten_con_sus_eventos():
    h,r,j,sala = sistema()
    entorno = Entorno(r)
    trampa = Trampa('t','t','t',5,20)
    puerta = Salida('N',2,True,cierre_automatico=30)
    h.iniciar_accion(r)
    entorno.activar_trampa(trampa,j)
    entorno.abrir(puerta)
    r.avanzar_y_ejecutar(50)
    h.confirmar_accion()
    assert trampa.armada and puerta.cerrada
    h.revertir()
    assert trampa.armada and puerta.cerrada and j.vida == 100
    assert trampa.evento_rearme is None and puerta.evento_cierre is None
    assert r.proximo() is None and r.tiempo_actual == 0


def test_rastro_y_sala_se_revierten_sin_tocar_cache():
    h,r,j,_ = sistema()
    c = mapa()
    rastro = Rastro(c,h)
    j.sala_actual = c.sala_por_id(1)
    rastro.registrar(1,0)
    h.iniciar_accion(r)
    h.registrar(DeltaAtributos(j,'sala_actual'))
    j.sala_actual = c.sala_por_id(7)
    rastro.registrar(7,0)
    r.avanzar_y_ejecutar(100)
    h.confirmar_accion()
    h.revertir()
    assert j.sala_actual.id == 1 and rastro.consultar(7) == -1
    assert rastro.consultar(1) == 0


def test_turno_jugador_restaurado_y_evento_futuro_no_duplicado():
    h,r,j,_ = sistema()
    inicial = r.programar_inicial(j,nada)
    h.iniciar_accion(r)
    r.tomar_turno(j)
    proximo = r.programar(j,100,nada)
    r.avanzar_hasta_turno(j)
    h.confirmar_accion()
    h.revertir()
    assert j.evento_actual is inicial and r.proximo() is inicial
    assert not proximo.valido and j.tiempo_siguiente == 0
    assert r.tiempo_actual == 0


def test_abortar_no_apila_y_restaura_azar_y_vida():
    h,r,j,_ = sistema()
    estado = r.azar.getstate()
    h.iniciar_accion(r)
    j.recibir_dano(r.calcular_dano(10,2))
    r.programar(j,100,nada)
    h.abortar_accion()
    assert j.vida == 100 and len(h) == 0 and r.proximo() is None
    assert r.azar.getstate() == estado and not h.registrando


def test_errores_contrato_historial_no_alteran_grupos():
    h,r,j,sala = sistema()
    with pytest.raises(RuntimeError): h.confirmar_accion()
    with pytest.raises(ValueError): h.iniciar_accion(Reloj(1))
    h.iniciar_accion(r)
    with pytest.raises(RuntimeError): h.iniciar_accion(r)
    with pytest.raises(RuntimeError): h.revertir()
    h.abortar_accion()
    perg = objeto(FabricaObjetos(),'pergamino_retroceso')
    sala.objetos_suelo.insertar_al_inicio(perg)
    j.recoger(perg)
    assert not h.usar_pergamino(j,j.cursor)
    assert len(j.inventario) == 1


@pytest.mark.parametrize('pasos', [1,5,20,100])
def test_estres_reprogramar_cancelar_ejecutar_deshacer(pasos):
    h,r,j,_ = sistema()
    original = r.programar(j,1000,nada)
    esperado = pendientes(r)
    estado_azar = r.azar.getstate()
    h.iniciar_accion(r)
    for n in range(pasos):
        r.reprogramar_por_velocidad(j,100 + n % 3 * 50)
        e = r.programar_en(r.tiempo_actual+1,lambda _: j.recibir_dano(0),dueno=j)
        if n % 2: r.cancelar(e)
        r.avanzar_y_ejecutar(r.tiempo_actual+1)
        r.calcular_dano(10,2)
    h.confirmar_accion()
    h.revertir()
    assert pendientes(r) == esperado and j.evento_actual is original
    assert r.azar.getstate() == estado_azar and j.velocidad == 100
    assert r.tiempo_actual == 0 and len(j.eventos_efectos) == 0


def test_movimiento_enemigo_restaura_listas_y_referencia_sala():
    h,r,j,a = sistema()
    b = Sala(2,'destino')
    enemigo = actor()
    enemigo.sala_actual = a
    a.enemigos_activos.insertar_al_inicio(enemigo)
    h.iniciar_accion(r)
    for lista in (a.enemigos_activos,b.enemigos_activos):
        h.registrar(DeltaListaSimple(lista,enemigo))
    h.registrar(DeltaAtributos(enemigo,'sala_actual'))
    a.enemigos_activos.eliminar_valor(enemigo)
    b.enemigos_activos.insertar_al_inicio(enemigo)
    enemigo.sala_actual = b
    h.confirmar_accion()
    h.revertir()
    assert list(a.enemigos_activos) == [enemigo]
    assert len(b.enemigos_activos) == 0 and enemigo.sala_actual is a


@pytest.mark.parametrize('semilla', [0,1,7,53,999])
def test_cinco_intervalos_mixtos_restauran_cada_estado(semilla):
    h,r,j,sala = sistema()
    r.azar.seed(semilla)  # La semilla se fija aquí para repetir exactamente el escenario de prueba.
    f = FabricaObjetos()
    for _ in range(5):
        sala.objetos_suelo.insertar_al_final(objeto(f))
    estados = []
    def estado():
        return (j.vida,j.ataque,tuple(inventario(j)),
                tuple(o.instancia_id for o in sala.objetos_suelo),
                r.tiempo_actual,r.azar.getstate(),tuple(pendientes(r)))
    for _ in range(5):
        estados.append(estado())
        h.iniciar_accion(r)
        nuevo = next(iter(sala.objetos_suelo))
        j.recoger(nuevo)
        j.equipar(nuevo.instancia_id)
        j.recibir_dano(r.calcular_dano(4,0))
        r.programar_en(r.tiempo_actual+1,lambda _: j.curar(1),dueno=j)
        r.avanzar_y_ejecutar(r.tiempo_actual+3)
        h.confirmar_accion()
    for esperado in reversed(estados):
        assert h.revertir()
        assert estado() == esperado
