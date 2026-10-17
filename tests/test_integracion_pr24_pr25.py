import json
import pytest
from utilidades.puntajes import Puntaje, TablaPuntajes as TablaBase
from persistencia.puntajes import TablaPuntajes, RegistroPuntaje
from estructuras.heap_minimo import HeapMinimo


def test_archivo_de_centeno_se_migra_sin_perder_registros(tmp_path):
    ruta = tmp_path / 'puntajes.json'
    antiguo = RegistroPuntaje('Daniel', 'c', 7, 10, 2, 100, 'victoria')
    ruta.write_text(json.dumps({'formato_puntajes': 1, 'registros': [antiguo.a_json()]}))
    original = ruta.read_bytes()
    tabla = TablaPuntajes(str(ruta)).cargar()
    assert ruta.read_bytes() == original  # leer no modifica el archivo
    tabla.agregar(RegistroPuntaje('Jose', 'c', '7', 11, 2, 120, 'en_curso'))
    tabla.guardar()
    releida = TablaBase.cargar(ruta)
    assert [releida.obtener(i).nombre for i in range(len(releida))] == ['Daniel', 'Jose']
    assert json.loads(ruta.read_text())['formato'] == 1


def test_archivo_pr25_lo_lee_el_adaptador_gui(tmp_path):
    ruta = tmp_path / 'puntajes.json'
    tabla = TablaBase()
    tabla.agregar(Puntaje('Jose', 'c', '1', 2, 0, 100, 'en_curso'))
    tabla.guardar(ruta)
    assert [(r.nombre_jugador, r.resultado) for r in TablaPuntajes(ruta).cargar()] == [('Jose', 'en_curso')]


def test_vista_del_heap_no_modifica_contadores_ni_entradas():
    h = HeapMinimo()
    entradas = [h.insertarEntrada(i, i) for i in range(20, 0, -1)]
    h.invalidarEntrada(entradas[-1])
    antes = (h.contadores(), h._datos.contadores(), list(h._datos))
    # El recorrido previo también cuenta: capturar después de tomar la copia.
    metricas = h._datos.contadores()
    assert [e.dato for e in h.vista_ordenada(5)] == [2, 3, 4, 5, 6]
    assert h.contadores() == antes[0] and h._datos.contadores() == metricas
    assert list(h._datos) == antes[2]


def test_cierre_no_duplica_resultado(tmp_path):
    from tests.test_puntajes_adaptador import _juego
    c, _, _ = _juego(tmp_path, ['Q'])
    c.jugar()
    c._registrar_puntaje()
    assert len(TablaBase.cargar(tmp_path / 'puntajes.json')) == 1


def test_filas_gui_no_exponen_objetos_mutables(tmp_path):
    from tests.vista.test_tabla_puntajes import _ganar
    c, filas = _ganar(tmp_path, 'Ada')
    filas[0].nombre_jugador = 'Modificado'
    assert c.tabla_puntajes()[0].nombre_jugador == 'Ada'


def test_carga_gui_renueva_sesion_hooks_y_nombre(tmp_path):
    from tests.vista.test_tabla_puntajes import _controlador, _esperar
    c = _controlador(tmp_path)
    try:
        c.iniciar_partida('cripta-prueba', 'Ada', semilla=999)
        assert _esperar(lambda: c.estado() is not None)
        ruta = tmp_path / 'carga.sav'
        c.guardar(str(ruta))
        assert _esperar(ruta.exists)
        anterior = c.sesion
        c.cargar(str(ruta))
        assert _esperar(lambda: c.sesion is not anterior)
        assert c.sesion is c._controlador.sesion
        assert len(c.sesion.partida.al_atacar) == 1
        assert len(c.sesion.partida.al_mover_enemigo) == 1
        assert c.reporte_red()
    finally:
        c.salir()
    assert c.resumen_fin().nombre_jugador == 'Ada'
