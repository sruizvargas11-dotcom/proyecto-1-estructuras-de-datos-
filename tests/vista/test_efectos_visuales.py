"""El estado visual muestra los efectos temporales reales del modelo."""
import pytest

from adaptadores.datos_offline import DatosOffline
from controlador.guardado import cargar, guardar
from controlador.inicio_partida import nueva_partida
from modelo.efectos import aplicar_modificador_velocidad
from controlador.controlador_pygame import construir_estado


@pytest.fixture
def sesion(tmp_path):
    actual = nueva_partida(DatosOffline(), 'cripta-01', str(tmp_path/'cache'), semilla=17)
    yield actual
    actual.red.cerrar(5)


@pytest.mark.parametrize('modificador', [25, -25])
def test_modificador_activo_se_identifica_y_muestra_tiempo_restante(sesion, modificador):
    p = sesion.partida
    aplicar_modificador_velocidad(p.reloj, p.jugador, modificador, 300)
    p.reloj.avanzar_y_ejecutar(100)
    foto = construir_estado(p)
    assert foto.velocidad == 100+modificador
    assert f'velocidad temporal: {100+modificador} (200 ut)' in foto.efectos


def test_modificador_expirado_desaparece_del_panel(sesion):
    p = sesion.partida
    aplicar_modificador_velocidad(p.reloj, p.jugador, 25, 300)
    p.reloj.avanzar_y_ejecutar(300)
    foto = construir_estado(p)
    assert foto.velocidad == 100
    assert not foto.efectos


def test_retroceso_retira_el_indicador_junto_con_el_efecto(sesion):
    p = sesion.partida
    p.historial.iniciar_accion(p.reloj)
    aplicar_modificador_velocidad(p.reloj, p.jugador, 25, 300)
    p.historial.confirmar_accion()
    assert construir_estado(p).efectos
    assert p.historial.revertir()
    foto = construir_estado(p)
    assert foto.velocidad == 100 and not foto.efectos


def test_guardado_y_carga_conservan_el_indicador(sesion, tmp_path):
    p = sesion.partida
    aplicar_modificador_velocidad(p.reloj, p.jugador, 25, 300)
    p.reloj.avanzar_hasta_turno(p.jugador)
    ruta = str(tmp_path/'efecto.sav')
    guardar(sesion, ruta)
    restaurada = cargar(ruta, sesion)
    try:
        foto = construir_estado(restaurada.partida)
        assert foto.velocidad == 125
        assert 'velocidad temporal: 125 (299 ut)' in foto.efectos
    finally:
        restaurada.red.cerrar(5)
