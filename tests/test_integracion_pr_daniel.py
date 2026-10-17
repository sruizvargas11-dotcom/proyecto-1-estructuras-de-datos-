import io
from pathlib import Path

import pytest

from adaptadores.datos_offline import DatosOffline
from bitacora_partida import BitacoraPartida
from controlador.controlador_juego import ControladorJuego
from controlador.controlador_replay import reproducir, ErrorReplayDivergente
from controlador.reporte_red import HistorialReportesRed
from main import main
from tests.test_consola_persistencia_replay import sesion, firma
from tests.test_controlador_juego import VistaGuion
from vista.vista_consola import VistaConsola


def test_carga_replay_con_cierre_verificado_y_metricas_conservadas(tmp_path):
    s = sesion(tmp_path)
    ruta = str(tmp_path / 'p.sav')
    c = ControladorJuego(s, VistaGuion(['R', 'U', f'G {ruta}', 'W', f'L {ruta}', 'W', 'Q']))
    c.jugar()
    assert c.sesion is not s
    assert c.sesion.esqueleto_desde_cache is s.esqueleto_desde_cache
    assert c.red.contador_solicitudes_contenido == s.red.contador_solicitudes_contenido
    assert c.red.contador_solicitudes_catalogo == s.red.contador_solicitudes_catalogo
    assert c.red._fichas.contador_aciertos >= s.red._fichas.contador_aciertos
    replay = reproducir(c.bitacora.ruta, s.fuente, str(tmp_path / 'cache-replay'))
    assert replay.verificado
    assert firma(replay.partida) == firma(c.partida)


def test_main_reporte_usa_sesion_y_log_despues_de_cargar(tmp_path, monkeypatch):
    # La sesión antes de L llega a t=100; la cargada termina en t=200.
    # Primera línea: nombre del jugador (vacía = usa el valor por defecto).
    monkeypatch.setattr('sys.stdin', io.StringIO('\nG\nW\nL\nW\nW\nQ\n'))
    reportes = tmp_path / 'reportes.txt'
    assert main(['--offline', '--cripta', 'cripta-01', '--partidas-dir', str(tmp_path),
                 '--cache-dir', str(tmp_path/'cache'), '--reportes', str(reportes)]) == 0
    texto = HistorialReportesRed(str(reportes)).leer().obtenerValor(0).texto
    assert 'tiempo_final: 200' in texto and 'acciones_jugador: 2' in texto
    assert 'carga_' in texto


@pytest.mark.parametrize('accion', ['cargar archivo.sav', 'guardar archivo.sav', 'salir', 'IC'])
def test_log_no_puede_ejecutar_comandos_de_archivos(tmp_path, accion):
    ruta = str(tmp_path/'inyectado.log')
    log = BitacoraPartida.partida_nueva(ruta, 'cripta-01', 'v', 'v', 1)
    log.registrar(0, accion)
    log.cerrar()
    assert main(['--offline', '--replay', ruta, '--reportes', str(tmp_path/'r.txt')]) == 3
    assert not (tmp_path/'archivo.sav').exists()


def test_cierre_alterado_no_se_declara_identico(tmp_path):
    s = sesion(tmp_path)
    ControladorJuego(s, VistaGuion(['W', 'Q'])).jugar()
    ruta = Path(s.bitacora.ruta)
    ruta.write_text(ruta.read_text(encoding='utf-8').replace('t=100 fin', 't=999 fin'), encoding='utf-8')
    with pytest.raises(ErrorReplayDivergente, match='cierre'):
        reproducir(str(ruta), s.fuente, str(tmp_path/'cache-r'))


@pytest.mark.parametrize('entrada', ['Q', '9'*5000])
def test_menu_cancelable_y_numero_enorme_no_crashea(entrada):
    comandos = iter([entrada, 'Q'])
    v = VistaConsola(leer=lambda _: next(comandos), escribir=lambda _: None)
    assert v.elegir_cripta([{'id':'cripta-01', 'nombre':'Prueba'}]) is None


def test_orden_nombre_muestra_indice_real_y_panel_no_tapa_comandos(tmp_path):
    s = sesion(tmp_path)
    salida=[]
    comandos=iter(['R','R','I nombre','Q'])
    v=VistaConsola(leer=lambda _: next(comandos), escribir=salida.append)
    ControladorJuego(s,v).jugar()
    filas=[l.strip().split() for l in salida if 'Antorcha' in l and 'luz por' in l]
    assert any(f[:2] == ['1','Antorcha'] for f in filas)


def test_restaurar_mensajes_descarta_panel_de_otra_partida():
    v=VistaConsola(escribir=lambda _:None)
    v.mostrar_ayuda()
    v.restaurar_mensajes(['[t=1] restaurado'])
    assert v.mensajes() == ['[t=1] restaurado'] and len(v._panel) == 0
