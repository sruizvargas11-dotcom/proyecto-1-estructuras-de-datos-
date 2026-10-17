"""Los stubs temporales cumplen las interfaces de contratos.py."""
import dataclasses

import pygame
import pytest

from vista_pygame.contratos import CargadorAssets, ColaAnimaciones, EscenaBase, GestorAudio, ResumenPartida
from vista_pygame.stubs_temporales import (
    CargadorAssetsTemporal, ColaAnimacionesTemporal, GestorAudioTemporal,
)


def test_cargador_assets_temporal_cumple_el_contrato():
    assets = CargadorAssetsTemporal()
    assert isinstance(assets, CargadorAssets)
    assert isinstance(assets.sprite_jugador("parado", "S"), pygame.Surface)
    assert isinstance(assets.sprite_enemigo("ent_rata_gigante", "rastreador"), pygame.Surface)
    assert isinstance(assets.sprite_objeto("itm_antorcha", "antorcha"), pygame.Surface)
    assert isinstance(assets.sprite_entorno("piso"), pygame.Surface)
    assert isinstance(assets.sprite_efecto("veneno"), pygame.Surface)
    assert isinstance(assets.icono("vida"), pygame.Surface)
    assert isinstance(assets.fuente(18), pygame.font.Font)


def test_cargador_assets_temporal_es_reproducible_y_cachea():
    assets = CargadorAssetsTemporal()
    a = assets.sprite_enemigo("ent_rata_gigante", "rastreador")
    b = assets.sprite_enemigo("ent_rata_gigante", "rastreador")
    assert a is b   # misma clave -> misma superficie (cache), no la recrea
    otro = assets.sprite_enemigo("ent_guardian_oseo", "guardián")
    assert otro is not a


def test_gestor_audio_temporal_cumple_el_contrato():
    audio = GestorAudioTemporal()
    assert isinstance(audio, GestorAudio)
    assert isinstance(audio.disponible, bool)
    audio.reproducir_musica("partida")
    audio.reproducir_sfx("ataque")
    audio.set_volumen(0.5, 0.5)
    assert audio.alternar_mute() is True
    assert audio.alternar_mute() is False


def test_cola_animaciones_temporal_cumple_el_contrato():
    cola = ColaAnimacionesTemporal()
    assert isinstance(cola, ColaAnimaciones)
    assert cola.ocupada is False
    cola.agregar_desde_eventos([])
    cola.actualizar(16)
    superficie = pygame.Surface((10, 10))
    cola.dibujar(superficie)   # no debe lanzar


def test_escena_base_es_abstracta():
    class EscenaIncompleta(EscenaBase):
        def manejar_evento(self, evento): pass
        def actualizar(self, dt_ms): pass
        # falta dibujar()

    with pytest.raises(TypeError):
        EscenaIncompleta(contexto=None)


def test_resumen_partida_tiene_los_campos_documentados():
    campos = {f.name for f in dataclasses.fields(ResumenPartida)}
    assert campos == {
        "resultado", "nombre_jugador", "id_cripta", "version_cripta",
        "acciones_jugador", "enemigos_derrotados", "tiempo_final",
        "solicitudes_realizadas", "presupuesto_solicitudes",
        "aciertos_cache", "fallos_cache",
    }
