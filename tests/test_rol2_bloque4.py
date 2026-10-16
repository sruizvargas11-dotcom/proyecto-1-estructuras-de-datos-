"""Cierre del rol 2: regresiones de ordenamiento y partida con latencias."""
import pytest
from adaptadores.datos_simulado import DatosSimulado, suma_verificacion
from adaptadores.datos_offline import DatosOffline
from bench.casos.ordenamiento import vector, comparar, _datos
from estructuras.ordenamientos import insertion_sort, merge_sort, ordenar, UMBRAL_TAMANO_PEQUENO
from herramientas.verificar_determinismo import verificar
from tests.test_controlador_juego import RUTA_VICTORIA
from tests.test_controlador_replay import OfflineResistente


def test_diez_latencias_offline_y_replays_coinciden_byte_a_byte(tmp_path):
    filas = verificar(OfflineResistente, 'cripta-01', RUTA_VICTORIA, tmp_path / 'corridas')
    assert len(filas) == 11
    assert all(f['resultado'] == 'victoria' and f['replay_verificado'] for f in filas)
    for campo in ('estado', 'mensajes', 'mensajes_replay', 'log'):
        assert all(f[campo] == filas[0][campo] for f in filas)


def test_checksum_estable_y_sensible_a_cambios():
    assert suma_verificacion('') == 'cbf29ce484222325'
    assert suma_verificacion('hello') == 'a430d84680aabd0b'
    assert suma_verificacion('á') != suma_verificacion('a')


def test_latencia_no_depende_del_orden_de_llamadas():
    a, b = [], []
    fuente = DatosOffline()
    primero = DatosSimulado(fuente, 7, esperar=a.append)
    segundo = DatosSimulado(fuente, 7, esperar=b.append)
    assert primero.version_cripta('cripta-01') == fuente.version_cripta('cripta-01')
    primero.version_catalogo()
    segundo.version_catalogo()
    segundo.version_cripta('cripta-01')
    assert a == b[::-1]


@pytest.mark.parametrize('n', [0, 1, 5, 10, 15, 20, 25, 30, 50, 100])
@pytest.mark.parametrize('casi', [False, True])
def test_algoritmos_reales_coinciden_y_preservan_datos(n, casi):
    datos = _datos(n, casi) if n else []
    a, b = vector(datos), vector(datos)
    insertion_sort(a, comparar)
    merge_sort(b, comparar)
    assert list(a) == list(b)
    assert all(a.obtenerValor(i) <= a.obtenerValor(i+1) for i in range(n-1))
    assert len(a) == len(datos) and sum(a) == sum(datos)


def test_selector_en_frontera_medida_y_estabilidad():
    for n in (UMBRAL_TAMANO_PEQUENO, UMBRAL_TAMANO_PEQUENO + 1):
        datos = vector(range(n, 0, -1))
        nombre = ordenar(datos, comparar)
        assert nombre == ('insertion_sort' if n == UMBRAL_TAMANO_PEQUENO else 'merge_sort')
        assert list(datos) == list(range(1, n+1))
    def por_clave(a, b):
        return comparar(a[0], b[0])
    for algoritmo in (insertion_sort, merge_sort):
        datos = vector([(2, 'a'), (1, 'b'), (2, 'c'), (1, 'd')])
        algoritmo(datos, por_clave)
        assert list(datos) == [(1, 'b'), (1, 'd'), (2, 'a'), (2, 'c')]

@pytest.mark.parametrize('patron', range(10))
def test_diez_patrones_con_lotes_en_vuelo(tmp_path, patron):
    from tests.test_orden_determinista import FuenteGrillaObjetos, _linea_base, _ids_objetos, _registro
    from controlador.controlador_red import cargar_esqueleto_completo, ControladorRed
    from controlador.despacho_red import DespachoEnHilos
    fuente = DatosSimulado(FuenteGrillaObjetos(5), patron, maximo=0.02)
    cripta = cargar_esqueleto_completo(fuente, 'grilla')
    red = ControladorRed(fuente, cripta, tmp_path / 'latencia',
                         version_catalogo={'version': 'c1'}, despachador=DespachoEnHilos())
    try:
        red.planificar_precarga(cripta.sala_por_id(13))
        red.procesar_cola()
        red.procesar_cola()
        red.esperar_todas()
        assert (_registro(red), _ids_objetos(cripta)) == _linea_base(tmp_path)
    finally:
        red.cerrar(5)


def test_errante_aislado_espera_costo_100_sin_consumir_azar(tmp_path):
    from controlador.inicio_partida import nueva_partida
    from modelo.entidades.enemigo import Enemigo
    sesion = nueva_partida(DatosOffline(), 'cripta-01', str(tmp_path), semilla=7)
    partida = sesion.partida
    sala = partida.cripta.sala_por_id(6)
    for salida in sala.salidas:
        salida.cerrada = True
    enemigo = Enemigo('aislado', 'tipo', 'Errante', 10, 1, 0, 100, 'errante', sala)
    antes = partida.reloj.azar.getstate()
    assert partida.turno_enemigo(enemigo) == 'esperar'
    assert enemigo.sala_actual is sala
    assert enemigo.evento_actual.tiempo == partida.tiempo + 100
    assert partida.reloj.azar.getstate() == antes
    sesion.red.cerrar(5)
