"""F4B-01: guardar los handles cancelados de un intervalo revertido."""
import pytest

from adaptadores.datos_offline import DatosOffline
from controlador.controlador_juego import ControladorJuego
from controlador.guardado import guardar, cargar
from controlador.inicio_partida import nueva_partida
from herramientas.generar_cripta_prueba import generar
from tests.test_controlador_juego import VistaGuion
from tests.test_consola_persistencia_replay import firma
from tests.test_regresion_retroceso_cache import _agregar_pergaminos


def _partida_retrocedida(tmp_path):
    datos = generar(tmp_path / 'datos')
    _agregar_pergaminos(datos, 1)
    sesion = nueva_partida(DatosOffline(str(datos)), 'cripta-prueba',
                           str(tmp_path / 'cache'), semilla=72)
    vista = VistaGuion(['R 5', 'R 7', 'R 1', 'W', 'P', 'Q'])
    ControladorJuego(sesion, vista).jugar()
    assert vista.textos('el tiempo retrocede')
    return sesion


def test_guardar_tras_pergamino_cargar_continuar_y_retroceder(tmp_path):
    sesion = _partida_retrocedida(tmp_path)
    partida = sesion.partida
    canceladas = [e for e in partida.reloj.agenda._datos if not e.valido]
    assert any(e.secuencia >= partida.reloj.agenda.siguiente_secuencia for e in canceladas)
    ruta = str(tmp_path / 'despues_de_P.sav')
    guardar(sesion, ruta)
    copia = cargar(ruta, sesion)
    assert firma(copia.partida) == firma(partida)
    vista = VistaGuion(['P', 'W', 'Q'])
    ControladorJuego(copia, vista).jugar()
    assert vista.textos('el tiempo retrocede')
    entradas = [e for e in copia.partida.reloj.agenda._datos
                if e.valido and e.dato.dueno is copia.partida.jugador]
    assert len(entradas) == 1
    assert not any(n.valor.clase == 'pergamino_retroceso'
                   for n in copia.partida.jugador.inventario.recorrer_desde_frente())


@pytest.mark.parametrize('campo,valor', [
    ('tiempo', -1), ('tiempo', True), ('secuencia', -1),
    ('secuencia', True), ('_en_heap', False), ('_propietario', None),
])
def test_canceladas_corruptas_siguen_rechazadas(tmp_path, campo, valor):
    sesion = _partida_retrocedida(tmp_path)
    entrada = next(e for e in sesion.partida.reloj.agenda._datos if not e.valido)
    setattr(entrada, campo, valor)
    ruta = str(tmp_path / 'corrupta.sav')
    guardar(sesion, ruta)
    with pytest.raises(ValueError, match='Entrada de agenda inconsistente'):
        cargar(ruta, sesion)


def test_secuencia_fuera_de_rango_en_evento_valido_se_rechaza(tmp_path):
    sesion = _partida_retrocedida(tmp_path)
    entrada = sesion.partida.jugador.evento_actual
    entrada.secuencia = sesion.partida.reloj.agenda.siguiente_secuencia
    ruta = str(tmp_path / 'secuencia_corrupta.sav')
    guardar(sesion, ruta)
    with pytest.raises(ValueError, match='Entrada de agenda inconsistente'):
        cargar(ruta, sesion)
