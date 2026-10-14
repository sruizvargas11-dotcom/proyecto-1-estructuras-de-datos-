import random
import threading
import time

import pytest

from adaptadores.datos_offline import DatosOffline
from controlador.buffer_reordenamiento import BufferReordenamiento
from controlador.controlador_red import ControladorRed, cargar_esqueleto_completo
from controlador.despacho_red import DespachoEnHilos
from controlador.inicio_partida import nueva_partida
from tests.test_controlador_red import FuenteContada, FuenteGrilla


class DespachoManual:
    """Retiene cada envío; la prueba decide en qué orden 'llegan' las respuestas."""

    def __init__(self):
        self.retenidas = []

    def enviar(self, tarea, entregar):
        self.retenidas.append((tarea, entregar))

    def completar(self, indice):
        tarea, entregar = self.retenidas[indice]
        self.retenidas[indice] = None
        try:
            respuesta = tarea()
        except Exception as error:
            entregar(None, error)
        else:
            entregar(respuesta, None)

    def sin_completar(self):
        return [i for i, r in enumerate(self.retenidas) if r is not None]

    def cerrar(self, tiempo_maximo=None):
        pass


class FuenteGrillaObjetos(FuenteGrilla):
    """Grilla donde cada sala trae además un objeto: permite observar los ids."""

    def contenido_salas(self, cripta_id, sala_ids):
        respuesta = super().contenido_salas(cripta_id, sala_ids)
        for datos in respuesta['contenido']:
            datos['objetos'] = [f"itm_{datos['sala']}"]
        return respuesta

    def catalogo(self, tipo_ids):
        entidades = []
        for t in tipo_ids:
            if t.startswith('itm_'):
                entidades.append({'id': t, 'clase': 'arma', 'nombre': t, 'peso': 1,
                                  'valor': 1, 'ataque_bonus': 1})
            else:
                entidades.extend(super().catalogo([t])['entidades'])
        return {'entidades': entidades}


class FuenteLenta:
    """Envoltura con latencia aleatoria (semilla propia) para probar hilos reales."""

    def __init__(self, fuente, semilla, maximo=0.03, lentas=()):
        self._fuente = fuente
        self._azar = random.Random(semilla)
        self._candado = threading.Lock()
        self._maximo = maximo
        self._lentas = lentas
        self.llamadas_contenido = 0

    def contenido_salas(self, cripta_id, sala_ids):
        with self._candado:
            self.llamadas_contenido += 1
            espera = self._azar.uniform(0, self._maximo)
        if any(s in self._lentas for s in sala_ids):
            espera = 0.25
        time.sleep(espera)
        return self._fuente.contenido_salas(cripta_id, sala_ids)

    def __getattr__(self, nombre):
        return getattr(self._fuente, nombre)


def _grilla(despachador, tmp_path):
    fuente = FuenteContada(FuenteGrillaObjetos(5))
    cripta = cargar_esqueleto_completo(fuente, 'grilla')
    red = ControladorRed(fuente, cripta, tmp_path, version_catalogo={'version': 'c1'},
                         despachador=despachador)
    return fuente, cripta, red


def _ids_objetos(cripta):
    """sala_id -> ids de sus objetos, para comparar ejecuciones."""
    return tuple((s.id, tuple(o.instancia_id for o in s.objetos_suelo))
                 for s in cripta.recorrer_salas())


def _registro(red):
    return tuple(red.registro_solicitudes())


def _linea_base(tmp_path):
    """Misma secuencia de decisiones con respuestas inmediatas (orden natural)."""
    _, cripta, red = _grilla(None, tmp_path / 'base')
    red.planificar_precarga(cripta.sala_por_id(13))
    red.procesar_cola()
    red.procesar_cola()
    red.incorporar_listas()
    return _registro(red), _ids_objetos(cripta)


def test_numero_se_asigna_al_decidir_y_es_creciente(tmp_path):
    manual = DespachoManual()
    fuente, cripta, red = _grilla(manual, tmp_path)
    red.planificar_precarga(cripta.sala_por_id(13))
    assert red.procesar_cola() == 0          # en vuelo: nada incorporado todavía
    assert red.procesar_cola() == 0
    registro = _registro(red)
    assert [(n, sub, clase) for n, sub, clase, _, _ in registro] == [
        (1, 0, 'contenido'), (2, 0, 'contenido')]
    assert [len(ids) for _, _, _, ids, _ in registro] == [10, 2]
    assert red.solicitudes_en_vuelo() == 2
    # Lo ya solicitado no se vuelve a encolar aunque su respuesta no haya llegado.
    assert red.planificar_precarga(cripta.sala_por_id(13)) == 0


def test_catalogo_se_numera_como_subsolicitud_del_contenido(tmp_path):
    fuente = FuenteContada(DatosOffline())
    cripta = cargar_esqueleto_completo(fuente, 'cripta-01')
    red = ControladorRed(fuente, cripta, tmp_path)
    red.solicitar_contenido_lote([1, 2, 3, 4, 5, 6])
    assert [(n, sub, clase, len(ids)) for n, sub, clase, ids, _ in _registro(red)] == [
        (1, 0, 'contenido', 6), (1, 1, 'catalogo', 10), (1, 2, 'catalogo', 1)]


def test_catalogo_fuera_de_incorporacion_recibe_numero_propio(tmp_path):
    fuente = FuenteContada(DatosOffline())
    cripta = cargar_esqueleto_completo(fuente, 'cripta-01')
    red = ControladorRed(fuente, cripta, tmp_path)
    red.garantizar_contenido(1)
    red.resolver_catalogo(['ent_guardian_oseo'])
    red.garantizar_contenido(5)
    numeros = [(n, sub, clase) for n, sub, clase, _, _ in _registro(red)]
    assert numeros == [(1, 0, 'contenido'), (1, 1, 'catalogo'), (2, 0, 'catalogo'),
                       (3, 0, 'contenido'), (3, 1, 'catalogo')]



def test_respuesta_adelantada_no_se_incorpora_antes_de_tiempo(tmp_path):
    manual = DespachoManual()
    _, cripta, red = _grilla(manual, tmp_path)
    red.planificar_precarga(cripta.sala_por_id(13))
    red.procesar_cola()                      # #1: 10 salas
    red.procesar_cola()                      # #2: 2 salas
    _, _, _, ids_1, _ = red.registro_solicitudes().obtenerValor(0)
    _, _, _, ids_2, _ = red.registro_solicitudes().obtenerValor(1)

    manual.completar(1)                      # llega primero la #2
    assert red.incorporar_listas() == 0
    assert not any(red.contenido_cargado(s) for s in ids_2)

    manual.completar(0)
    assert red.incorporar_listas() == 12
    assert all(red.contenido_cargado(s) for s in ids_1 + ids_2)
    # Los ids de objetos salen en orden de número, no de llegada.
    assert _ids_objetos(cripta) == _linea_base(tmp_path)[1]


@pytest.mark.parametrize('semilla', range(6))
def test_mismo_juego_misma_secuencia_con_llegadas_permutadas(tmp_path, semilla):
    manual = DespachoManual()
    _, cripta, red = _grilla(manual, tmp_path / str(semilla))
    red.planificar_precarga(cripta.sala_por_id(13))
    red.procesar_cola()
    red.procesar_cola()
    azar = random.Random(semilla)
    pendientes = manual.sin_completar()
    azar.shuffle(pendientes)
    for indice in pendientes:
        manual.completar(indice)
        if azar.random() < 0.5:              # puntos fijos en momentos distintos
            red.incorporar_listas()
    red.incorporar_listas()
    assert (_registro(red), _ids_objetos(cripta)) == _linea_base(tmp_path)


@pytest.mark.parametrize('semilla', [1, 2, 3])
def test_hilos_con_latencias_aleatorias_dan_el_mismo_resultado(tmp_path, semilla):
    fuente = FuenteLenta(FuenteGrillaObjetos(5), semilla)
    cripta = cargar_esqueleto_completo(fuente, 'grilla')
    red = ControladorRed(fuente, cripta, tmp_path / str(semilla),
                         version_catalogo={'version': 'c1'}, despachador=DespachoEnHilos())
    red.planificar_precarga(cripta.sala_por_id(13))
    red.procesar_cola()
    red.procesar_cola()
    red.garantizar_contenido(18)             # estaba en vuelo: espera las anteriores
    assert red.contenido_cargado(18)
    red.esperar_todas()
    red.cerrar(5)
    assert red.solicitudes_en_vuelo() == 0
    base_registro, base_ids = _linea_base(tmp_path / str(semilla))
    assert _registro(red) == base_registro
    assert _ids_objetos(cripta) == base_ids


def test_buffer_cuenta_adelantadas_y_descarta_tardias():
    buffer = BufferReordenamiento()
    a, b, c = buffer.reservar('a'), buffer.reservar('b'), buffer.reservar('c')
    assert (a, b, c) == (1, 2, 3)
    assert buffer.entregar(3, 'r3')
    assert buffer.tomar_siguiente() is None
    buffer.abandonar_hasta(2, RuntimeError('tarde'))
    assert not buffer.entregar(1, 'r1')       # llegó después de abandonarse
    assert buffer.tomar_siguiente()[0] == 'a'
    assert buffer.tomar_siguiente()[0] == 'b'
    assert buffer.tomar_siguiente() == ('c', 'r3', None)
    assert dict(buffer.contadores())['adelantadas'] == 1


def test_buffer_compacta_y_conserva_el_orden():
    buffer = BufferReordenamiento()
    tomados = []
    for ronda in range(10):
        numeros = [buffer.reservar(f's{ronda}-{i}') for i in range(15)]
        for numero in reversed(numeros):
            buffer.entregar(numero, numero)
        while True:
            t = buffer.tomar_siguiente()
            if t is None:
                break
            tomados.append(t[1])
    assert tomados == list(range(1, 151))
    assert len(buffer._ranuras) < 150



def test_incorporar_contenido_no_programa_eventos_ni_gasta_secuencia(tmp_path):
    sesion = nueva_partida(DatosOffline(), 'cripta-01', str(tmp_path), semilla=4)
    partida, red = sesion.partida, sesion.red
    agenda = len(partida.reloj.agenda)
    secuencia = partida.reloj.agenda.siguiente_secuencia
    red.planificar_precarga(partida.cripta.sala_por_id(3))
    red.procesar_cola()                      # incorpora salas 4 y 6
    assert red.contenido_cargado(4)
    sala4 = partida.cripta.sala_por_id(4)
    assert len(sala4.enemigos_dormidos) == 1 and len(sala4.enemigos_activos) == 0
    assert len(partida.reloj.agenda) == agenda
    assert partida.reloj.agenda.siguiente_secuencia == secuencia
    assert partida.tiempo == 0



def test_movimiento_hacia_sala_pendiente_espera_sin_mover_el_reloj(tmp_path):
    fuente = FuenteLenta(DatosOffline(), 7, maximo=0.0, lentas=(4,))
    sesion = nueva_partida(fuente, 'cripta-01', str(tmp_path), semilla=9,
                           despachador=DespachoEnHilos())
    partida, red = sesion.partida, sesion.red
    red.planificar_precarga(partida.cripta.sala_por_id(3))
    red.procesar_cola()                      # 4 y 6 en vuelo (lento)
    assert not red.contenido_cargado(4) and red.contenido_solicitado(4)
    antes = (partida.tiempo, partida.reloj.agenda.siguiente_secuencia,
             len(partida.reloj.agenda))
    inicio = time.perf_counter()
    assert red.asegurar_entrada(4) is None
    assert time.perf_counter() - inicio > 0.1   # sí hubo espera real
    assert red.contenido_cargado(4)
    assert (partida.tiempo, partida.reloj.agenda.siguiente_secuencia,
            len(partida.reloj.agenda)) == antes
    assert fuente.llamadas_contenido == 2       # inicial + la precarga; sin repetir
    assert dict(red.contadores())['esperas_bloqueantes'] == 1
    red.cerrar(5)


def test_movimiento_rechazado_con_mensaje_si_no_se_obtiene_contenido(tmp_path):
    fuente = FuenteContada(DatosOffline())
    sesion = nueva_partida(fuente, 'cripta-01', str(tmp_path), semilla=9)
    partida, red = sesion.partida, sesion.red
    fuente.fallar_contenido = True
    antes = (partida.tiempo, partida.reloj.agenda.siguiente_secuencia)
    mensaje = red.asegurar_entrada(4)
    assert mensaje is not None and 'sala 4' in mensaje and 'Presupuesto' in mensaje
    assert not red.contenido_cargado(4)
    assert (partida.tiempo, partida.reloj.agenda.siguiente_secuencia) == antes
    # Se recupera cuando la fuente vuelve a responder.
    fuente.fallar_contenido = False
    assert red.asegurar_entrada(4) is None and red.contenido_cargado(4)
