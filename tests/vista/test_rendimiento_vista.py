"""§5.2: un ciclo de eventos del modelo debe costar menos de 20 ms, sin
contar el render (que corre aparte, en el hilo de pygame). Esta prueba mide
el modelo solo (como ya hace la consola) y, por separado, un frame de
dibujo con muchos actores, para no mezclar ambos presupuestos.
"""
import time

import pygame
import pytest

from adaptadores.datos_offline import DatosOffline
from controlador.inicio_partida import nueva_partida
from herramientas.generar_cripta_prueba import generar
from vista_pygame.controlador_pygame import ActorVisual, EstadoPartida, SalidaVisual
from vista_pygame.render.render_actores import dibujar_enemigos, dibujar_jugador
from vista_pygame.render.render_sala import dibujar_sala
from vista_pygame.stubs_temporales import CargadorAssetsTemporal

LIMITE_CICLO_MS = 20.0
CANTIDAD_ENEMIGOS_ESTRES = 50


def _sesion_con_movimiento(tmp_path):
    carpeta = generar(tmp_path / "datos")
    return nueva_partida(DatosOffline(str(carpeta)), "cripta-prueba", str(tmp_path / "cache"),
                         semilla=2026, nombre_jugador="Ada")


@pytest.mark.rendimiento
def test_ciclo_del_modelo_bajo_20ms_promedio_y_peor_caso(tmp_path):
    sesion = _sesion_con_movimiento(tmp_path)
    partida, reloj, jugador = sesion.partida, sesion.partida.reloj, sesion.partida.jugador

    duraciones = []
    objetivo = partida.cripta.sala_por_id(2)
    for _ in range(20):
        reloj.avanzar_hasta_turno(jugador)
        partida.historial.iniciar_accion(reloj)
        inicio = time.perf_counter()
        reloj.tomar_turno(jugador)
        if jugador.sala_actual.id == objetivo.id:
            partida.entrar_a_sala(partida.cripta.sala_por_id(1))
        else:
            partida.entrar_a_sala(objetivo)
        partida.contar_accion_jugador()
        if jugador.vivo and not partida.terminada:
            partida.programar_siguiente_jugador(100)
        duraciones.append((time.perf_counter() - inicio) * 1000)
        partida.historial.confirmar_accion()
        if partida.terminada:
            break

    assert duraciones
    promedio = sum(duraciones) / len(duraciones)
    peor = max(duraciones)
    assert promedio < LIMITE_CICLO_MS, f"promedio {promedio:.3f} ms"
    assert peor < LIMITE_CICLO_MS, f"peor caso {peor:.3f} ms"


def _estado_con_muchos_enemigos(cantidad):
    enemigos = [ActorVisual(f"e-{i}", "ent_rata_gigante", f"Rata gigante #{i}",
                            12, 12, "rastreador", False) for i in range(cantidad)]
    return EstadoPartida(
        tiempo=0, sala_id=1, sala_nombre="Sala de pruebas",
        salidas=[SalidaVisual("N", 2, "Siguiente", False, False)],
        enemigos_activos=enemigos, enemigos_dormidos=[], objetos_suelo=[], trampas=[],
        jugador=ActorVisual("jugador", "", "", 30, 30, "", False),
        ataque=6, defensa=2, velocidad=100, arma_equipada="", armadura_equipada="",
        inventario=[], efectos=[], enemigos_derrotados=0, acciones_jugador=0,
        estado="en_curso", salas_visitadas=[1],
    )


@pytest.mark.rendimiento
def test_frame_con_muchos_actores_promedio_y_peor_caso():
    pantalla = pygame.Surface((1280, 720))
    assets = CargadorAssetsTemporal()
    estado = _estado_con_muchos_enemigos(CANTIDAD_ENEMIGOS_ESTRES)

    duraciones = []
    for _ in range(30):
        inicio = time.perf_counter()
        dibujar_sala(pantalla, assets, estado)
        dibujar_jugador(pantalla, assets, estado, "Ada")
        dibujar_enemigos(pantalla, assets, estado, objetivo_indice=1)
        duraciones.append((time.perf_counter() - inicio) * 1000)

    promedio = sum(duraciones) / len(duraciones)
    peor = max(duraciones)
    # El render no tiene el límite de 20 ms del modelo (corre aparte), pero
    # con rectángulos de colores debe seguir siendo holgadamente < 1 frame.
    assert promedio < 16.0, f"promedio {promedio:.3f} ms"
    assert peor < 50.0, f"peor caso {peor:.3f} ms"
