"""Regresiones de puntajes, mediciones y reporte final del bloque 4."""
import io
import pytest

from bench.ciclo import crear_escenario, ejecutar_intervalo, medir_escala, resumen
from bench.casos import heap, mensajes
from bench.medicion import Fila, mediana, medir
from estructuras.vector_dinamico import Vector
from utilidades.puntajes import Puntaje, TablaPuntajes


def test_mediana_par_y_calentamiento_no_es_repeticion():
    assert mediana([8, 2, 4, 6]) == 5
    llamadas = []
    medir(llamadas.append, 1, repeticiones=5)
    assert len(llamadas) == 6
    with pytest.raises(ValueError):
        medir(llamadas.append, 1, repeticiones=0)
    with pytest.raises(ValueError):
        mediana([])


def test_resumen_no_reordena_muestras():
    valores = Vector()
    for valor in (4, 1, 3, 2):
        valores.agregarValor(valor)
    r = resumen(valores)
    assert (r['min_ms'], r['mediana_ms'], r['p95_ms'], r['max_ms']) == (1, 2.5, 4, 4)
    assert list(valores) == [4, 1, 3, 2]


def test_comparaciones_procesan_mismos_datos(monkeypatch):
    monkeypatch.setattr(heap, 'EXTRACCIONES', 201)
    assert heap._con_heap([7, 1, 4, 1]) == heap._con_lista([7, 1, 4, 1])
    for cantidad in (0, 1, 20, 21, 20000):
        assert mensajes.circular(cantidad) == mensajes.desplazar(cantidad)


def test_intervalo_incluye_enemigos_efectos_y_flush(tmp_path):
    ruta = tmp_path / 'ciclo.log'
    c = crear_escenario(6, ruta_log=ruta)
    try:
        for _ in range(5):
            ejecutar_intervalo(c)
            assert c.reloj.proximo().dato.dueno is c.jugador
            assert not c.historial.registrando
        assert c.partida.acciones_jugador == 5
        assert c.contador_turnos_enemigo >= 30
        assert c.contador_efectos > 0
        # Se puede leer antes del cierre: el flush pertenece al intervalo.
        assert 'mover E' in ruta.read_text(encoding='utf-8')
    finally:
        c._cerrar(False)


def test_medicion_guarda_muestras_y_contadores(tmp_path):
    r = medir_escala(ciclos=6, repeticiones=2, salas_base=4, carpeta=tmp_path)
    assert r['ciclos_medidos'] == 6
    assert len(r['corridas']) == 2
    assert all(len(c['muestras_ms']) == 3 for c in r['corridas'])


def test_obtener_puntaje_no_permite_desordenar_tabla():
    tabla = TablaPuntajes()
    tabla.agregar(Puntaje('A', 'c', '1', 3, 2, 4, 'victoria'))
    copia = tabla.obtener(0)
    copia.nombre = 'Mutado'
    copia.enemigos_derrotados = 100
    assert tabla.obtener(0).nombre == 'A'
    assert tabla.obtener(0).enemigos_derrotados == 2


def test_bench_headless_con_reporte_y_sin_puntaje(tmp_path, monkeypatch, capsys):
    import main
    import bench.runner
    from vista.vista_consola import VistaConsola
    def prohibido(*args, **kwargs):
        raise AssertionError('Bench no instancia la vista ni una fuente HTTP')
    monkeypatch.setattr(VistaConsola, '__init__', prohibido)
    monkeypatch.setattr(main, 'crear_fuente', prohibido)
    monkeypatch.setattr(bench.runner, 'main_bench', lambda: [
        Fila('cache', 'ListaLRU', 1000, 1, contadores=(('aciertos', 600), ('fallos', 400)))])
    reporte = tmp_path / 'red.txt'
    assert main.main(['--bench', '--reportes', str(reporte), '--partidas-dir', str(tmp_path)]) == 0
    texto = capsys.readouterr().out
    assert 'solicitudes_realizadas: 0' in texto
    assert 'fichas_lru_aciertos: 600' in texto
    assert 'fichas_lru_fallos: 400' in texto
    assert 'no aplica' in texto and reporte.exists()
    assert not (tmp_path / 'puntajes.json').exists()


def test_delta_compacto_restaura_handle_y_tiempo():
    from modelo.historial import Historial
    from modelo.reloj import Reloj
    from modelo.entidades.actor import Actor
    from modelo.ejecutor_evento import EjecutorEvento
    historial = Historial()
    reloj = Reloj(42, historial)
    actor = Actor('prueba', 100, 10, 2, 100)
    anterior = reloj.programar_inicial(actor, EjecutorEvento('decision'))
    historial.iniciar_accion(reloj)
    reloj.tomar_turno(actor)
    nueva = reloj.programar(actor, 100, EjecutorEvento('decision'))
    historial.confirmar_accion()
    assert actor.evento_actual is nueva and actor.tiempo_siguiente == 100
    historial.revertir()
    assert actor.evento_actual is anterior and actor.tiempo_siguiente == 0
    assert reloj.proximo() is anterior and not nueva.valido


def test_delta_antiguo_sin_campos_nuevos_sigue_revirtiendo():
    from modelo.deltas import DeltaEvento, DeltaAtributos
    from modelo.reloj import Reloj
    from modelo.entidades.actor import Actor
    from modelo.ejecutor_evento import EjecutorEvento
    reloj = Reloj(42)
    actor = Actor('prueba', 100, 10, 2, 100)
    anterior = reloj.programar_inicial(actor, EjecutorEvento('decision'))
    delta = DeltaEvento(reloj, anterior)
    for campo in ('campo', 'anterior', 'tiempo_anterior'):
        delattr(delta, campo)  # forma almacenada por la versión anterior
    atributos = DeltaAtributos(actor, 'evento_actual')
    reloj.extraer_siguiente()
    atributos.revertir()
    delta.revertir()
    assert actor.evento_actual is anterior and reloj.proximo() is anterior


def test_extraer_entrada_conocida_rechaza_una_entrada_fuera_de_orden():
    import pytest
    from modelo.reloj import Reloj
    from modelo.ejecutor_evento import EjecutorEvento
    reloj = Reloj(42)
    primera = reloj.programar_en(10, EjecutorEvento('decision'))
    segunda = reloj.programar_en(20, EjecutorEvento('decision'))
    with pytest.raises(ValueError):
        reloj.extraer_siguiente(segunda)
    assert reloj.proximo() is primera
    assert reloj.extraer_siguiente(primera) is primera
    assert reloj.proximo() is segunda