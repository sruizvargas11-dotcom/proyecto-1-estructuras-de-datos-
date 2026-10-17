"""B3: semilla de partida, inicio con red/disco y reglas de modelo de Partida."""
import random

import pytest

from adaptadores.datos_offline import DatosOffline
from bitacora_partida import BitacoraPartida
from controlador.inicio_partida import nueva_partida, ruta_bitacora_por_defecto
from controlador.semilla import SEMILLA_MAX, generar_semilla, validar_semilla
from estructuras.vector_dinamico import Vector
from estructuras.ordenamientos import ordenar
from modelo.partida import (DERROTA, EN_CURSO, VICTORIA, Partida,
                            comparar_instancias)

SOLICITUDES = ('listar_criptas', 'datos_cripta', 'esqueleto_cripta', 'contenido_salas',
               'catalogo', 'version_cripta', 'version_catalogo')


class FuenteContada(DatosOffline):
    """DatosOffline que cuenta cada consulta como si fuera una solicitud de red."""

    def __init__(self):
        super().__init__()
        self.solicitudes = 0

    def __getattribute__(self, nombre):
        if nombre in SOLICITUDES:
            object.__setattr__(self, 'solicitudes', object.__getattribute__(self, 'solicitudes') + 1)
        return object.__getattribute__(self, nombre)


def _sesion(tmp_path, semilla=12345, **extra):
    return nueva_partida(FuenteContada(), 'cripta-01', str(tmp_path), semilla=semilla, **extra)


def _mover(partida, destino, costo=100):
    """Ejecuta una acción siguiendo el ciclo del controlador descrito en ROL3_BLOQUE3.md."""
    reloj, jugador, historial = partida.reloj, partida.jugador, partida.historial
    reloj.avanzar_hasta_turno(jugador)
    historial.iniciar_accion(reloj)
    reloj.tomar_turno(jugador)
    partida.entrar_a_sala(destino)
    partida.contar_accion_jugador()
    if jugador.vivo and not partida.terminada:
        partida.programar_siguiente_jugador(costo)
        reloj.avanzar_hasta_turno(jugador)
    historial.confirmar_accion()


def _ids(lista):
    return [e.instancia_id for e in lista]


# ----------------------------------------------------------------- semilla

def test_semilla_en_rango_y_validada():
    assert validar_semilla(0) == 0
    assert validar_semilla(SEMILLA_MAX) == SEMILLA_MAX
    for mala in (-1, SEMILLA_MAX + 1, 3.0, '5', True, None):
        with pytest.raises(ValueError):
            validar_semilla(mala)


def test_dos_partidas_nuevas_tienen_semillas_distintas():
    generador = random.Random(99)   # inyectado solo para que la prueba sea exacta
    assert generar_semilla(generador) != generar_semilla(generador)
    assert 0 <= generar_semilla() <= SEMILLA_MAX


def test_generar_semilla_no_usa_el_generador_global():
    random.seed(2026)
    estado = random.getstate()
    generar_semilla()
    assert random.getstate() == estado


def test_partida_nueva_genera_semilla_y_la_escribe_en_la_bitacora(tmp_path):
    ruta = str(tmp_path / 'p.log')
    sesion = nueva_partida(DatosOffline(), 'cripta-01', str(tmp_path), ruta_bitacora=ruta)
    partida = sesion.partida
    assert 0 <= partida.semilla <= SEMILLA_MAX
    assert partida.reloj.semilla == partida.semilla
    sesion.bitacora.cerrar()
    leida = BitacoraPartida.abrir(ruta)
    assert leida.semilla == partida.semilla
    assert leida.version_cripta == partida.version_cripta
    assert leida.version_catalogo == partida.version_catalogo == 'be68d322d2f5'


def test_semilla_recibida_se_reutiliza_para_replay(tmp_path):
    assert _sesion(tmp_path, semilla=777).partida.semilla == 777
    with pytest.raises(ValueError):
        _sesion(tmp_path, semilla=-3)


def test_ruta_por_defecto_incluye_cripta_y_semilla(tmp_path):
    ruta = ruta_bitacora_por_defecto('cripta-01', 42, str(tmp_path))
    assert ruta.endswith('cripta-01_42.log')


# ----------------------------------------------------------------- inicio

def test_inicializar_no_supera_el_presupuesto(tmp_path):
    sesion = _sesion(tmp_path)
    assert sesion.fuente.solicitudes <= sesion.partida.cripta.presupuesto_solicitudes
    # Segunda partida con caché caliente: solo generales y versión del catálogo.
    otra = _sesion(tmp_path)
    assert otra.fuente.solicitudes <= 2


def test_jugador_con_estadisticas_del_api_en_sala_inicial(tmp_path):
    fuente = DatosOffline()
    datos = fuente.datos_cripta('cripta-01')
    partida = nueva_partida(fuente, 'cripta-01', str(tmp_path), semilla=1).partida
    j = partida.jugador
    assert (j.vida_max, j.ataque, j.defensa, j.velocidad) == (
        datos['jugador']['vida_max'], datos['jugador']['ataque'],
        datos['jugador']['defensa'], datos['jugador']['velocidad'])
    assert j.inventario_max == datos['inventario_max']
    assert j.sala_actual.id == datos['sala_inicial']


def test_estado_inicial_t0(tmp_path):
    sesion = _sesion(tmp_path)
    partida = sesion.partida
    assert partida.estado == EN_CURSO and partida.tiempo == 0
    assert partida.jugador.sala_actual.tiempo_rastro == 0
    assert partida.reloj.proximo() is partida.jugador.evento_actual
    assert partida.jugador.tiempo_siguiente == 0
    assert sesion.red.contenido_cargado(partida.cripta.sala_inicial_id)
    # Primer lote incluye vecinas: entrar a la sala 2 no requiere esperar red.
    assert sesion.red.contenido_cargado(2)
    with pytest.raises(RuntimeError):
        partida.inicializar()


def test_incorporar_contenido_no_activa_enemigos(tmp_path):
    partida = _sesion(tmp_path).partida
    sala2 = partida.cripta.sala_por_id(2)
    assert len(sala2.enemigos_dormidos) == 2 and len(sala2.enemigos_activos) == 0
    # Solo el turno del jugador está en la agenda.
    assert len(partida.reloj.agenda) == 1


# ----------------------------------------------------------------- activación

class _Falso:
    def __init__(self, instancia_id):
        self.instancia_id = instancia_id


def test_orden_de_instancia_es_natural():
    v = Vector()
    for i in ('e-100', 'e-9', 'e-10', 'a-50'):
        v.agregarValor(_Falso(i))
    ordenar(v, comparar_instancias)
    assert _ids(v) == ['a-50', 'e-9', 'e-10', 'e-100']


def test_entrar_activa_dormidos_en_orden_y_con_tiempo_correcto(tmp_path):
    partida = _sesion(tmp_path).partida
    sala2 = partida.cripta.sala_por_id(2)
    partida.reloj.avanzar_hasta_turno(partida.jugador)
    partida.historial.iniciar_accion(partida.reloj)
    partida.reloj.tomar_turno(partida.jugador)
    partida.entrar_a_sala(sala2)
    assert len(sala2.enemigos_dormidos) == 0
    assert _ids(sala2.enemigos_activos) == ['e-201', 'e-202']
    r1, r2 = sala2.enemigos_activos.a_lista_python()
    # Rata velocidad 150, activada en t=0: 100*100//150 = 66 (§2.4).
    assert r1.tiempo_siguiente == r2.tiempo_siguiente == 66
    assert r1.evento_actual.secuencia < r2.evento_actual.secuencia
    assert sala2.tiempo_rastro == 0


def test_secuencia_213_y_determinismo_por_semilla(tmp_path):
    """Jugador entra a la sala 2 en t=0; las ratas actúan en 66 antes que él en 100."""
    resultados = []
    for _ in range(2):
        partida = _sesion(tmp_path, semilla=2026).partida
        mensajes = []
        partida.al_mensaje.agregarValor(lambda t, texto: mensajes.append((t, texto)))
        _mover(partida, partida.cripta.sala_por_id(2))
        assert partida.tiempo == 100 and partida.jugador.tiempo_siguiente == 100
        ataques = [t for t, texto in mensajes if 'te ataca' in texto]
        assert ataques == [66, 66]
        resultados.append((partida.jugador.vida, tuple(mensajes)))
    assert resultados[0] == resultados[1]


def test_retroceso_deshace_entrada_activacion_y_ataques(tmp_path):
    partida = _sesion(tmp_path, semilla=5).partida
    inicial, sala2 = partida.jugador.sala_actual, partida.cripta.sala_por_id(2)
    vida = partida.jugador.vida
    _mover(partida, sala2)
    assert partida.jugador.vida < vida and partida.acciones_jugador == 1
    assert partida.historial.revertir()
    assert partida.jugador.sala_actual is inicial and partida.jugador.vida == vida
    assert len(sala2.enemigos_activos) == 0 and len(sala2.enemigos_dormidos) == 2
    assert sala2.tiempo_rastro == -1 and partida.tiempo == 0
    assert partida.acciones_jugador == 0
    assert partida.reloj.proximo() is partida.jugador.evento_actual


# ----------------------------------------------------------------- muerte y fin

def test_muerte_de_enemigo_suelta_botin_y_libera_ficha(tmp_path):
    sesion = _sesion(tmp_path, semilla=3)
    partida = sesion.partida
    sala2 = partida.cripta.sala_por_id(2)
    _mover(partida, sala2)
    rata = sala2.enemigos_activos.a_lista_python()[0]
    muertos = []
    partida.al_morir_enemigo.agregarValor(muertos.append)
    suelo_antes = len(sala2.objetos_suelo)

    partida.historial.iniciar_accion(partida.reloj)
    partida.reloj.tomar_turno(partida.jugador)
    partida.danar_enemigo(rata, 999)
    assert not rata.vivo and rata.evento_actual is None
    assert not sala2.enemigos_activos.contiene_valor(rata)
    assert partida.enemigos_derrotados == 1 and muertos == [rata]
    assert len(sala2.objetos_suelo) == suelo_antes + 1
    assert sala2.objetos_suelo.a_lista_python()[-1].tipo_id == 'itm_pocion_menor'
    partida.programar_siguiente_jugador(100)
    partida.reloj.avanzar_hasta_turno(partida.jugador)
    partida.historial.confirmar_accion()

    assert partida.historial.revertir()
    assert rata.vivo and sala2.enemigos_activos.contiene_valor(rata)
    assert partida.enemigos_derrotados == 0 and len(sala2.objetos_suelo) == suelo_antes


def test_derrota_cuando_los_enemigos_matan_al_jugador(tmp_path):
    partida = _sesion(tmp_path, semilla=8).partida
    partida.jugador.vida = 1
    _mover(partida, partida.cripta.sala_por_id(2))
    assert not partida.jugador.vivo and partida.estado == DERROTA
    assert partida.terminada
    # Ningún enemigo queda reprogramado tras el fin de la partida.
    for rata in partida.cripta.sala_por_id(2).enemigos_activos:
        assert rata.evento_actual is None
    assert partida.jugador.evento_actual is None


def test_victoria_al_entrar_a_la_sala_de_salida(tmp_path):
    partida = _sesion(tmp_path).partida
    _mover(partida, partida.cripta.sala_por_id(partida.cripta.sala_salida_id))
    assert partida.estado == VICTORIA
    puntaje = partida.resumen_puntaje()
    assert ('acciones_jugador', 1) in puntaje and ('resultado', VICTORIA) in puntaje


def test_partida_sin_sala_inicial_es_invalida(tmp_path):
    partida = _sesion(tmp_path).partida
    partida.jugador.sala_actual = None
    with pytest.raises(ValueError):
        Partida(partida.cripta, partida.jugador, 1)
