"""Reloj, rastro y entorno: reglas del enunciado y contratos de integración."""
import random
import pytest
from estructuras.heap_minimo import HeapMinimo
from modelo.reloj import Reloj
from modelo.historial import Historial
from modelo.rastro import Rastro
from modelo.entorno import Entorno
from modelo.entidades.actor import Actor
from modelo.entidades.jugador import Jugador
from modelo.entidades.enemigo import Enemigo
from modelo.entidades.trampa import Trampa
from modelo.mundo.sala import Sala
from modelo.mundo.salida import Salida
from modelo.mundo.cripta_modelo import CriptaModelo


def actor(velocidad=100):
    return Actor('actor', 100, 10, 2, velocidad)


def nada(reloj):
    pass


def mapa():
    c = CriptaModelo('prueba', 'v1', 1, 1000000000, None, 20, 10)
    for i in (1, 7, 1000000000):
        c.agregar_sala(Sala(i, str(i)))
    c.finalizar_carga()
    return c


def test_heap_consulta_limpieza_y_handle_restaurado():
    h = HeapMinimo()
    assert h.minimo() is None and h.descartar_cancelados() == 0
    a = h.insertarEntrada(40, 'cancelado')
    b = h.insertarEntrada(66, 'primero')
    c = h.insertarEntrada(66, 'segundo')
    h.invalidarEntrada(a)
    assert h.minimo() is a and len(h) == 3
    assert h.descartar_cancelados() == 1
    assert h.minimo() is b and len(h) == 2
    assert h.extraer_entrada() is b
    assert not b._en_heap
    h.restaurarEntrada(b)
    h.restaurarEntrada(b)
    assert len(h) == 2
    assert h.extraer_minimo() == 'primero'
    assert h.extraer_entrada() is c
    assert h.extraer_entrada() is None
    with pytest.raises(ValueError):
        HeapMinimo().restaurarEntrada(b)


@pytest.mark.parametrize('costo,velocidad,esperado', [(100,100,100),(100,150,66),(25,100,25),(50,100,50),(1,999999,1),(0,100,1)])
def test_intervalo_entero(costo, velocidad, esperado):
    assert Reloj.intervalo(costo, velocidad) == esperado


@pytest.mark.parametrize('valor', [True, 1.5, '100', None, -1])
def test_tiempos_invalidos_no_modifican_agenda(valor):
    r = Reloj(5)
    with pytest.raises(ValueError):
        r.programar_en(valor, nada)
    assert len(r.agenda) == 0 and r.tiempo_actual == 0


@pytest.mark.parametrize('velocidad', [0, -1, True, 100.5])
def test_velocidad_invalida_no_cancela_evento(velocidad):
    r = Reloj(2)
    a = actor()
    entrada = r.programar(a, 100, nada)
    with pytest.raises(ValueError):
        r.reprogramar_por_velocidad(a, velocidad)
    assert a.evento_actual is entrada and entrada.valido and a.velocidad == 100


def test_secuencia_213_exacta():
    r = Reloj(7)
    jugador, rata = actor(), actor(150)
    sucesos = []
    def actuar_rata(reloj):
        sucesos.append(('rata', reloj.tiempo_actual))
        reloj.programar(rata, 100, actuar_rata)
    r.programar_inicial(jugador, nada)
    r.programar(rata, 100, actuar_rata)
    for costo in (100, 25, 50):
        r.avanzar_hasta_turno(jugador)
        sucesos.append(('jugador', r.tiempo_actual))
        r.tomar_turno(jugador)
        r.programar(jugador, costo, nada)
    r.avanzar_hasta_turno(jugador)
    sucesos.append(('jugador', r.tiempo_actual))
    assert sucesos == [('jugador',0),('rata',66),('jugador',100),
                       ('jugador',125),('rata',132),('jugador',175)]
    assert rata.tiempo_siguiente == 198


@pytest.mark.parametrize('enemigo_primero', [False, True])
def test_empate_con_decision_respeta_seq(enemigo_primero):
    r, a, eventos = Reloj(0), actor(), []
    if enemigo_primero:
        r.programar_en(100, lambda _: eventos.append('antes'))
    turno = r.programar(a, 100, nada)
    if not enemigo_primero:
        r.programar_en(100, lambda _: eventos.append('despues'))
    assert r.avanzar_hasta_turno(a) is turno
    assert eventos == (['antes'] if enemigo_primero else [])
    r.tomar_turno(a)
    r.avanzar_y_ejecutar(100)
    assert eventos == (['antes'] if enemigo_primero else ['despues'])


def test_reprogramacion_escala_restante_y_cambia_seq():
    r, a = Reloj(1), actor()
    vieja = r.programar(a, 100, nada)
    r.avanzar_y_ejecutar(40)
    nueva = r.reprogramar_por_velocidad(a, 200)
    assert nueva.tiempo == 70 and nueva.secuencia > vieja.secuencia
    assert not vieja.valido
    r.avanzar_y_ejecutar(50)
    lenta = r.reprogramar_por_velocidad(a, 50)
    assert lenta.tiempo == 130 and a.tiempo_siguiente == 130
    minima = r.reprogramar_por_velocidad(a, 1000000)
    assert minima.tiempo == 51


def test_espera_turno_considera_velocidad_cambiada_durante_intervalo():
    r, a = Reloj(3), actor()
    r.programar(a, 100, nada)
    r.programar_en(40, lambda reloj: reloj.reprogramar_por_velocidad(a, 200))
    assert r.avanzar_hasta_turno(a).tiempo == 70
    assert r.tiempo_actual == 70


def test_cancelacion_no_avanza_tiempo_y_futuro_no_se_extrae():
    r = Reloj(4)
    a = r.programar_en(40, lambda _: pytest.fail('Evento cancelado ejecutado'))
    futuro = r.programar_en(132, nada)
    assert r.cancelar(a) and not r.cancelar(a)
    assert r.tiempo_actual == 0
    assert r.avanzar_y_ejecutar(100) == 0
    assert r.proximo() is futuro
    with pytest.raises(ValueError):
        r.avanzar_y_ejecutar(99)
    with pytest.raises(ValueError):
        r.programar_en(99, nada)


def test_azar_compartido_reproducible_no_global():
    random.seed(123)
    estado_global = random.getstate()
    r1, r2 = Reloj(9), Reloj(9)
    assert [r1.calcular_dano(10,2) for _ in range(40)] == [r2.calcular_dano(10,2) for _ in range(40)]
    assert r1.calcular_dano(0,999) == 1
    assert random.getstate() == estado_global


def test_muerte_cancela_accion_y_efectos_solo_del_dueno():
    r, a, b = Reloj(0), actor(), actor()
    r.programar(a,100,lambda _: pytest.fail('Actor muerto actuó'))
    r.programar_en(20,lambda _: pytest.fail('Efecto de muerto ejecutado'),dueno=a)
    ajeno = r.programar(b,100,nada)
    r.vincular_actor(a)
    a.recibir_dano(100)
    assert not a.vivo and len(a.eventos_efectos) == 0
    assert ajeno.valido
    assert r.avanzar_y_ejecutar(100) == 1


@pytest.mark.parametrize('tiempo,esperado', [(0,False),(9,False),(10,True),(409,True),(410,False),(1000,False)])
def test_rastro_limites_y_ids_dispersos(tiempo, esperado):
    c = mapa()
    r = Rastro(c)
    assert not r.es_fresco(7, 0)
    assert r.registrar(1000000000,10) == -1
    assert r.es_fresco(1000000000,tiempo) is esperado
    assert c.sala_por_id(1000000000).tiempo_rastro == 10
    r.revertir(1000000000,-1)
    assert not r.es_fresco(1000000000,10)
    with pytest.raises(ValueError):
        r.registrar(2,0)


def test_rearme_300_y_no_repetir_antes():
    r, a = Reloj(1), actor()
    e = Entorno(r)
    trampa = Trampa('t1','t','Trampa',3,None)
    assert e.activar_trampa(trampa,a)
    assert a.vida == 97 and trampa.evento_rearme.tiempo == 300
    assert not e.activar_trampa(trampa,a)
    r.avanzar_y_ejecutar(299)
    assert not trampa.armada
    r.avanzar_y_ejecutar(300)
    assert trampa.armada and trampa.evento_rearme is None
    assert e.activar_trampa(trampa,a) and a.vida == 94


def test_entrada_trampa_inmediata_antes_del_siguiente_evento():
    r = Reloj(0)
    sala = Sala(1,'s')
    j = Jugador('j',100,10,0,100,10,sala)
    sala.trampas.insertar_al_inicio(Trampa('t','tipo','t',5,10))
    observado = []
    r.programar_en(0,lambda _: observado.append(j.vida))
    assert Entorno(r).al_entrar(j,sala) == 1
    r.avanzar_y_ejecutar(0)
    assert observado == [95]


@pytest.mark.parametrize('intervalo', [None,0,50])
def test_cierre_no_teletransporta_y_errante_no_atraviesa(intervalo):
    r = Reloj(0)
    a, b = Sala(1,'a'), Sala(2,'b')
    salida = Salida('N',2,True,cierre_automatico=intervalo)
    salida.sala_destino = b
    a.salidas.insertar_al_inicio(salida)
    jugador = Jugador('j',20,1,0,100,2,b)
    enemigo = Enemigo('e','tipo','e',20,1,0,100,'errante',a)
    entorno = Entorno(r)
    assert entorno.abrir(salida)
    assert not entorno.abrir(salida)
    r.avanzar_y_ejecutar(50)
    assert jugador.sala_actual is b
    assert salida.cerrada is (intervalo is not None)
    if intervalo is not None:
        assert enemigo.decidir_accion(jugador,50,r.azar) == ('esperar',None)


def test_cancelar_otro_reloj_y_reentrada_se_rechazan():
    r, otro = Reloj(1), Reloj(2)
    entrada = otro.programar_en(0,nada)
    with pytest.raises(ValueError):
        r.cancelar(entrada)
    r.programar_en(0,lambda reloj: reloj.avanzar_y_ejecutar())
    with pytest.raises(RuntimeError):
        r.avanzar_y_ejecutar()
    assert not r._ejecutando
