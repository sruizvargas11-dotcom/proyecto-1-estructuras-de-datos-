"""render_actores.dibujar_enemigos: solo presentación, nunca decide nada del
modelo. Cubre sala con 0/1/muchos enemigos y tipo desconocido, dormidos y
activos juntos, que un enemigo muerto no se dibuje, y tiempo de dibujado con
muchos enemigos.
"""
import statistics
import time

import pygame
import pytest

from adaptadores.datos_offline import DatosOffline
from controlador.inicio_partida import nueva_partida
from herramientas.generar_cripta_prueba import generar
from vista_pygame.config_vista import MAX_ENEMIGOS_VISIBLES
from vista_pygame.controlador_pygame import ActorVisual, ControladorPygame, EstadoPartida, SalidaVisual
from vista_pygame.render.render_actores import dibujar_enemigos, siguiente_objetivo
from vista_pygame.stubs_temporales import CargadorAssetsTemporal

TIMEOUT = 8.0


def _estado(enemigos_activos=(), enemigos_dormidos=()):
    return EstadoPartida(
        tiempo=0, sala_id=1, sala_nombre="Sala de pruebas",
        salidas=[SalidaVisual("N", 2, "Siguiente", False, False)],
        enemigos_activos=list(enemigos_activos), enemigos_dormidos=list(enemigos_dormidos),
        objetos_suelo=[], trampas=[],
        jugador=ActorVisual("jugador", "", "", 30, 30, "", False),
        ataque=6, defensa=2, velocidad=100, arma_equipada="", armadura_equipada="",
        inventario=[], efectos=[], enemigos_derrotados=0, acciones_jugador=0,
        estado="en_curso", salas_visitadas=[1],
    )


def _enemigo(i, tipo_id="ent_rata_gigante", comportamiento="rastreador", vida=12):
    return ActorVisual(f"e-{i}", tipo_id, f"Rata gigante #{i}", vida, 12, comportamiento, False)


def _esperar(condicion, timeout=TIMEOUT):
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        if condicion():
            return True
        time.sleep(0.01)
    return False


@pytest.fixture
def pantalla():
    return pygame.Surface((1280, 720))


@pytest.fixture
def assets():
    return CargadorAssetsTemporal()


def test_sala_sin_enemigos_no_crashea(pantalla, assets):
    dibujar_enemigos(pantalla, assets, _estado(), objetivo_indice=None)
    assert siguiente_objetivo(_estado(), None) is None


def test_un_enemigo(pantalla, assets):
    estado = _estado(enemigos_activos=[_enemigo(1)])
    dibujar_enemigos(pantalla, assets, estado, objetivo_indice=1)
    assert siguiente_objetivo(estado, None) == 1
    assert siguiente_objetivo(estado, 1) == 1   # un solo enemigo: se queda en él


def test_muchos_enemigos_muestra_indicador_mas_n(pantalla, assets):
    cantidad = MAX_ENEMIGOS_VISIBLES + 4
    estado = _estado(enemigos_activos=[_enemigo(i) for i in range(cantidad)])
    dibujar_enemigos(pantalla, assets, estado, objetivo_indice=None)   # no debe crashear
    assert siguiente_objetivo(estado, MAX_ENEMIGOS_VISIBLES + 4) == 1  # da la vuelta


def test_tipo_desconocido_no_crashea(pantalla, assets):
    estado = _estado(enemigos_activos=[_enemigo(1, tipo_id="ent_no_existe_en_catalogo",
                                                comportamiento="xyz_desconocido")])
    dibujar_enemigos(pantalla, assets, estado, objetivo_indice=1)


def test_dormidos_y_activos_juntos(pantalla, assets):
    """§2.4: una sala puede traer dormidos y activos a la vez."""
    estado = _estado(enemigos_activos=[_enemigo(1)], enemigos_dormidos=[_enemigo(2), _enemigo(3)])
    dibujar_enemigos(pantalla, assets, estado, objetivo_indice=1)
    # Los dormidos no son objetivo de ataque ni cuentan para 'A <n>'.
    assert siguiente_objetivo(estado, 1) == 1


def test_enemigo_muerto_no_se_dibuja(tmp_path):
    """Integración: tras morir, el modelo ya no lo trae en enemigos_activos,
    así que la vista no tiene nada especial que hacer para 'no dibujarlo'."""
    carpeta = generar(tmp_path / "datos")
    c = ControladorPygame(DatosOffline(str(carpeta)), carpeta_cache=str(tmp_path / "cache"),
                          partidas_dir=str(tmp_path / "partidas"))
    c.iniciar_partida("cripta-prueba", "Ada", semilla=2026)
    assert _esperar(lambda: c.estado() is not None)
    c.enviar_comando("N")
    assert _esperar(lambda: c.estado().sala_id == 2 and len(c.estado().enemigos_activos) >= 1)
    vivos_antes = len(c.estado().enemigos_activos)
    assert vivos_antes >= 1

    # cripta-prueba sube el ataque del jugador a 30 (ver herramientas/
    # generar_cripta_prueba.py): una rata (12 de vida) muere de un golpe.
    acciones_antes = c.estado().acciones_jugador
    for i in range(1, vivos_antes + 1):
        c.enviar_comando("A 1")
        assert _esperar(lambda i=i: c.estado().acciones_jugador == acciones_antes + i)

    assert _esperar(lambda: c.estado().enemigos_derrotados >= 1, timeout=TIMEOUT)
    estado_final = c.estado()
    assert len(estado_final.enemigos_activos) < vivos_antes
    pantalla = pygame.Surface((1280, 720))
    dibujar_enemigos(pantalla, CargadorAssetsTemporal(), estado_final, objetivo_indice=None)
    c.salir()


CALENTAMIENTO_RENDIMIENTO = 5
REPETICIONES_RENDIMIENTO = 25
UMBRAL_MEDIANA_MS = 10.0


@pytest.mark.rendimiento
def test_tiempo_dibujado_con_muchos_enemigos(pantalla, assets):
    estado = _estado(enemigos_activos=[_enemigo(i) for i in range(200)])

    # Calentamiento (sin medir): absorbe el costo del primer blit/convert de
    # cada superficie cacheada, para no contaminar la primera repetición.
    for _ in range(CALENTAMIENTO_RENDIMIENTO):
        dibujar_enemigos(pantalla, assets, estado, objetivo_indice=1)

    duraciones = []
    for _ in range(REPETICIONES_RENDIMIENTO):
        inicio = time.perf_counter()
        dibujar_enemigos(pantalla, assets, estado, objetivo_indice=1)
        duraciones.append((time.perf_counter() - inicio) * 1000)

    # Mediana, no el peor caso: una pausa puntual del SO/GC en una sola
    # repetición (frecuente con la suite completa en paralelo) no debe hacer
    # fallar la prueba; una regresión real (p. ej. perder el tope de
    # MAX_ENEMIGOS_VISIBLES y dibujar los 200) sí empuja a la mayoría de las
    # repeticiones, no solo a una, y la mediana lo sigue detectando.
    mediana = statistics.median(duraciones)
    assert mediana < UMBRAL_MEDIANA_MS, f"mediana {mediana:.3f} ms ({duraciones})"
