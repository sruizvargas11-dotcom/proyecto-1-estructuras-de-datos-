import gc
import random

import pytest

from controlador.controlador_juego import ControladorJuego
from estructuras.heap_minimo import HeapMinimo
from estructuras.vector_dinamico import Vector
from herramientas import perfilar_ciclo as pc
from modelo.entidades.enemigo import Enemigo
from modelo.historial import Historial
from modelo.mundo.sala import Sala
from modelo.mundo.salida import Salida
from modelo.reloj import Reloj


def test_heap_extrae_en_el_mismo_orden_que_una_referencia():
    """Inserciones, cancelaciones y restauraciones al azar: el heap optimizado
    entrega exactamente el orden (tiempo, secuencia) de una lista de control."""
    azar = random.Random(5)
    heap, vivas = HeapMinimo(), []
    for paso in range(4000):
        operacion = azar.random()
        if operacion < 0.55 or not vivas:
            entrada = heap.insertarEntrada(azar.randint(0, 300), paso)
            vivas.append(entrada)
        elif operacion < 0.7:
            entrada = vivas.pop(azar.randrange(len(vivas)))
            heap.invalidarEntrada(entrada)
        else:
            esperada = min(vivas, key=lambda e: (e.tiempo, e.secuencia))
            assert heap.extraer_entrada() is esperada
            vivas.remove(esperada)
    while vivas:
        esperada = min(vivas, key=lambda e: (e.tiempo, e.secuencia))
        assert heap.extraer_entrada() is esperada
        vivas.remove(esperada)
    assert heap.extraer_entrada() is None


def test_heap_sigue_contando_comparaciones_y_conserva_la_clave():
    heap = HeapMinimo()
    for i in range(50):
        heap.insertarEntrada(50 - i, i)
    assert heap.contador_comparaciones > 0
    entrada = heap.extraer_entrada()
    assert entrada.clave() == (entrada.tiempo, entrada.secuencia) == (1, 49)


def test_vector_expone_su_almacenamiento_sin_copiarlo():
    vector = Vector()
    for i in range(3):
        vector.agregarValor(i)
    datos = vector.almacenamiento()
    assert datos[:3] == [0, 1, 2] and datos is vector.almacenamiento()


def _decidir_como_antes(enemigo, jugador, tiempo, azar):
    """Versión original (una búsqueda por dirección), para comparar."""
    disponibles = Vector()
    for direccion in ("N", "S", "E", "O"):
        salida = enemigo.sala_actual.salida_hacia(direccion)
        if salida is not None and not salida.cerrada:
            disponibles.agregarValor(salida.sala_destino)
    if len(disponibles) == 0:
        return ("esperar", None)
    return ("mover", disponibles.obtenerValor(azar.randrange(len(disponibles))))


def test_errante_elige_igual_que_antes_aunque_las_salidas_esten_desordenadas():
    azar_salidas = random.Random(9)
    for prueba in range(200):
        origen = Sala(1, "origen")
        direcciones = ["O", "E", "S", "N"]
        azar_salidas.shuffle(direcciones)
        for numero, direccion in enumerate(direcciones[:azar_salidas.randint(1, 4)], 2):
            salida = Salida(direccion, numero, cerrada=azar_salidas.random() < 0.3)
            salida.sala_destino = Sala(numero, f"s{numero}")
            origen.salidas.insertar_al_final(salida)
        enemigo = Enemigo("e-1", "t", "Murciélago", 10, 1, 1, 100, "errante", origen)
        jugador = Enemigo("j", "t", "J", 10, 1, 1, 100, "guardián", Sala(99, "otra"))
        a, b = random.Random(prueba), random.Random(prueba)
        nuevo = enemigo.decidir_accion(jugador, 0, a)
        viejo = _decidir_como_antes(enemigo, jugador, 0, b)
        assert nuevo == viejo and a.getstate() == b.getstate()


def _rastreador_como_antes(enemigo, tiempo):
    """Versión original del rastreador, para comparar."""
    mejor = None
    for direccion in ("N", "S", "E", "O"):
        salida = enemigo.sala_actual.salida_hacia(direccion)
        if salida is None or salida.cerrada:
            continue
        sala = salida.sala_destino
        if sala.tiempo_rastro < 0 or not 0 <= tiempo - sala.tiempo_rastro < 400:
            continue
        if (mejor is None or sala.tiempo_rastro > mejor.tiempo_rastro
                or (sala.tiempo_rastro == mejor.tiempo_rastro and sala.id < mejor.id)):
            mejor = sala
    return ("esperar", None) if mejor is None else ("mover", mejor)


def test_rastreador_elige_igual_que_antes():
    azar = random.Random(13)
    for _ in range(300):
        origen = Sala(1, "origen")
        direcciones = ["O", "E", "S", "N"]
        azar.shuffle(direcciones)
        for numero, direccion in enumerate(direcciones[:azar.randint(1, 4)], 2):
            salida = Salida(direccion, numero, cerrada=azar.random() < 0.25)
            salida.sala_destino = Sala(numero, f"s{numero}")
            # Rastros repetidos a propósito para ejercitar el desempate por id.
            salida.sala_destino.tiempo_rastro = azar.choice((-1, 100, 300, 300, 650))
            origen.salidas.insertar_al_final(salida)
        enemigo = Enemigo("e-1", "t", "Rata", 10, 1, 1, 150, "rastreador", origen)
        jugador = Enemigo("j", "t", "J", 10, 1, 1, 100, "guardián", Sala(99, "otra"))
        assert enemigo.decidir_accion(jugador, 700, random.Random(1)) == \
            _rastreador_como_antes(enemigo, 700)


def test_programar_guarda_handle_y_tiempo_siguiente_en_un_delta_y_los_revierte():
    historial = Historial()
    reloj = Reloj(1, historial)
    actor = Enemigo("e-1", "t", "Rata", 10, 1, 1, 150, "rastreador", Sala(1, "s"))
    historial.iniciar_accion(reloj)
    antes = historial.contador_deltas
    reloj.programar(actor, 100, lambda r: None)
    # El delta compacto conserva entrada, handle y tiempo_siguiente juntos.
    assert historial.contador_deltas - antes == 1
    assert actor.evento_actual is not None and actor.tiempo_siguiente == 66
    historial.abortar_accion()
    assert actor.evento_actual is None and actor.tiempo_siguiente == 0
    assert len(reloj.agenda) == 1 and not reloj.agenda.minimo().valido


def test_historial_sigue_rechazando_deltas_sin_revertir():
    historial = Historial()
    reloj = Reloj(1, historial)
    historial.iniciar_accion(reloj)
    with pytest.raises(TypeError):
        historial.registrar(object())


def test_lista_simple_inserta_varios_y_conserva_primeros():
    from estructuras.lista_simple import ListaSimple
    lista = ListaSimple()
    lista.insertar_varios_al_final([1, 2])
    lista.insertar_varios_al_final([3, 4, 5])
    assert list(lista) == [1, 2, 3, 4, 5] and len(lista) == 5
    lista.conservar_primeros(2)
    assert list(lista) == [1, 2] and len(lista) == 2
    lista.insertar_al_final(9)
    assert list(lista) == [1, 2, 9]
    lista.conservar_primeros(0)
    assert list(lista) == [] and lista.esta_vacia()
    with pytest.raises(IndexError):
        lista.conservar_primeros(1)


def test_la_cola_de_la_lista_simple_sigue_al_ultimo_nodo():
    """Operaciones al azar contra una lista de control; agregar al final usa la cola."""
    from estructuras.lista_simple import ListaSimple
    azar = random.Random(3)
    lista, control = ListaSimple(), []
    for paso in range(3000):
        operacion = azar.random()
        if operacion < 0.25 or not control:
            lista.insertar_al_final(paso)
            control.append(paso)
        elif operacion < 0.35:
            lista.insertar_al_inicio(paso)
            control.insert(0, paso)
        elif operacion < 0.45:
            indice = azar.randint(0, len(control))
            lista.insertar_en(indice, paso)
            control.insert(indice, paso)
        elif operacion < 0.6:
            valor = azar.choice(control)
            assert lista.eliminar_valor(valor)
            control.remove(valor)
        elif operacion < 0.8:
            valor = azar.choice(control)
            assert lista.eliminar_valor_y_posicion(valor) == control.index(valor)
            control.remove(valor)
        elif operacion < 0.85:
            cantidad = azar.randint(0, len(control))
            lista.conservar_primeros(cantidad)
            del control[cantidad:]
        else:
            nuevos = [paso * 10 + i for i in range(azar.randint(0, 3))]
            lista.insertar_varios_al_final(nuevos)
            control.extend(nuevos)
        assert list(lista) == control and len(lista) == len(control)
    assert lista.eliminar_valor_y_posicion(object()) is None


def test_mover_enemigo_y_revertir_restaura_ambas_salas():
    sesion, _ = pc.preparar(salas=30, enemigos=40, sala_multitud=2)
    partida = sesion.partida
    origen = partida.cripta.sala_por_id(2)
    destino = next(s.sala_destino for s in origen.salidas if s.sala_destino is not None)
    enemigos = list(origen.enemigos_activos)
    assert len(enemigos) >= 3
    antes = (list(origen.enemigos_activos), list(destino.enemigos_activos))
    partida.historial.iniciar_accion(partida.reloj)
    for enemigo in (enemigos[1], enemigos[-1], enemigos[0]):   # medio, cola y cabeza
        partida._mover_enemigo(enemigo, destino)
    assert list(destino.enemigos_activos)[-3:] == [enemigos[1], enemigos[-1], enemigos[0]]
    assert list(origen.enemigos_activos) == enemigos[2:-1]
    partida.historial.abortar_accion()
    assert (list(origen.enemigos_activos), list(destino.enemigos_activos)) == antes
    assert all(e.sala_actual is origen for e in enemigos)
    origen.enemigos_activos.insertar_al_final("cola")   # la cola quedó bien después de revertir
    assert list(origen.enemigos_activos)[-1] == "cola"


def test_activar_y_revertir_dejan_las_listas_exactamente_como_estaban():
    sesion, _ = pc.preparar(salas=30, enemigos=40, sala_multitud=2, activar=False)
    partida = sesion.partida
    sala = partida.cripta.sala_por_id(2)
    sesion.red.garantizar_contenido(2)
    # Un activo previo y un dormido muerto, para cubrir ambos casos.
    previo = sala.enemigos_dormidos._head.valor
    sala.enemigos_dormidos.eliminar_valor(previo)
    sala.enemigos_activos.insertar_al_final(previo)
    muerto = sala.enemigos_dormidos._head.siguiente.valor
    muerto.vivo = False
    dormidos_antes, activos_antes = list(sala.enemigos_dormidos), list(sala.enemigos_activos)

    partida.historial.iniciar_accion(partida.reloj)
    activados = partida.activar_enemigos(sala)
    vivos = sorted((e for e in dormidos_antes if e.vivo),
                   key=lambda e: int(e.instancia_id.split("-")[1]))
    assert activados == len(vivos) == len(dormidos_antes) - 1
    assert list(sala.enemigos_activos) == activos_antes + vivos     # orden de instancia_id
    assert len(sala.enemigos_dormidos) == 0
    partida.historial.abortar_accion()
    assert list(sala.enemigos_dormidos) == dormidos_antes
    assert list(sala.enemigos_activos) == activos_antes


def test_la_partida_no_modifica_el_recolector_global():
    sesion, _ = pc.preparar(salas=20, enemigos=10)
    congelados = []
    antes = gc.get_freeze_count()

    class Guion(pc.GuionPerfil):
        def leer_comando(self):
            congelados.append(gc.get_freeze_count())
            return super().leer_comando()

    ControladorJuego(sesion, Guion(sesion.partida, 5)).jugar()
    assert congelados and all(n == antes for n in congelados)
    assert gc.get_freeze_count() == antes


def test_fuente_sintetica_respeta_el_contrato_del_api():
    fuente = pc.FuenteSintetica(salas=120, enemigos=30)
    general = fuente.datos_cripta(fuente.cripta_id)
    assert general["paginas"] == 3 and general["salas_total"] == 120
    pagina = fuente.esqueleto_cripta(fuente.cripta_id, 3)
    assert pagina["total_paginas"] == 3 and len(pagina["salas"]) == 20
    assert len(fuente.contenido_salas(fuente.cripta_id, list(range(1, 11)))["contenido"]) == 10
    with pytest.raises(ValueError):
        fuente.contenido_salas(fuente.cripta_id, list(range(1, 12)))
    with pytest.raises(ValueError):
        fuente.catalogo(["x"] * 11)


def test_medir_devuelve_las_cuatro_cifras_del_plan():
    resultado = pc.medir(salas=20, enemigos=10, ciclos=30)
    assert resultado["ciclos"] == 30
    assert (0 <= resultado["min_ms"] <= resultado["mediana_ms"] <= resultado["p95_ms"]
            <= resultado["max_ms"])


def test_estadisticas_ordenan_con_el_ordenamiento_propio():
    tiempos = Vector()
    for valor in (5_000_000, 1_000_000, 3_000_000, 2_000_000, 4_000_000):
        tiempos.agregarValor(valor)
    r = pc.estadisticas(tiempos)
    assert (r["min_ms"], r["mediana_ms"], r["max_ms"]) == (1.0, 3.0, 5.0)


def test_la_medicion_es_reproducible():
    """Misma cripta y semilla: mismo estado final, con o sin el recolector congelado."""
    from controlador.estado_final import lineas_estado
    finales = []
    for _ in range(2):
        sesion, _ = pc.preparar(salas=30, enemigos=40)
        ControladorJuego(sesion, pc.GuionPerfil(sesion.partida, 40)).jugar()
        finales.append([linea for linea in lineas_estado(sesion.partida)])
    assert finales[0] == finales[1]
