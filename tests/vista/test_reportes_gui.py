"""El cierre gráfico persiste el reporte una vez y respeta --reportes."""
import json
import pytest
import main
from adaptadores.datos_offline import DatosOffline
from herramientas.generar_cripta_prueba import generar
from controlador.reporte_red import HistorialReportesRed
from vista_pygame.app import AppPygame
from controlador.controlador_pygame import ControladorPygame
from tests.vista.test_controlador_pygame import _esperar


def crear(tmp_path, reportes=None, vida=None):
    datos=generar(tmp_path/'datos')
    if vida is not None:
        ruta=datos/'cripta-prueba'/'general.json'
        generales=json.loads(ruta.read_text(encoding='utf-8'))
        generales['jugador']['vida_max']=vida
        ruta.write_text(json.dumps(generales),encoding='utf-8')
    ruta=reportes if reportes is not None else str(tmp_path/'reportes'/'red.txt')
    return ControladorPygame(DatosOffline(str(datos)),str(tmp_path/'cache'),
                             partidas_dir=str(tmp_path/'partidas'),reportes=ruta),ruta


def iniciar(c,semilla=2026):
    c.iniciar_partida('cripta-prueba','Ada',semilla)
    assert _esperar(lambda:c.estado() is not None and not c.esperando_red())


def test_main_transmite_ruta_del_reporte_hasta_el_cierre_gui(tmp_path,monkeypatch):
    datos=generar(tmp_path/'datos')
    ruta=tmp_path/'salida elegida'/'reporte.txt'
    def ejecutar(app):
        try:
            app._escenas[0]._hilo_carga.join(timeout=5)
            iniciar(app._contexto.controlador)
        finally:
            app._contexto.controlador.salir()
    monkeypatch.setattr(AppPygame,'ejecutar',ejecutar)
    assert main.main(['--gui','--offline','--offline-dir',str(datos),
                      '--cache-dir',str(tmp_path/'cache'),
                      '--partidas-dir',str(tmp_path/'partidas'),
                      '--reportes',str(ruta)])==0
    bloques=HistorialReportesRed(str(ruta)).leer()
    assert len(bloques)==1
    assert 'solicitudes_realizadas: 0' in bloques.obtenerValor(0).texto
    assert 'salida controlada' in bloques.obtenerValor(0).texto


def test_no_duplica_al_cerrar_y_agrega_la_siguiente_partida(tmp_path):
    c,ruta=crear(tmp_path)
    try:
        iniciar(c,11);c.salir();c.salir()
        assert len(HistorialReportesRed(ruta).leer())==1
        iniciar(c,22);c.salir()
        bloques=HistorialReportesRed(ruta).leer()
        assert len(bloques)==2
        assert 'semilla: 22' in bloques.obtenerValor(0).texto
        assert 'semilla: 11' in bloques.obtenerValor(1).texto
    finally:c.salir()


@pytest.mark.parametrize('resultado',['victoria','derrota'])
def test_guarda_al_terminar_sin_esperar_a_cerrar_la_ventana(tmp_path,resultado):
    c,ruta=crear(tmp_path,vida=1 if resultado=='derrota' else None)
    try:
        iniciar(c)
        comandos=['N'] if resultado=='derrota' else ['N','N','N','R','AB E','E']
        for comando in comandos:c.enviar_comando(comando)
        assert _esperar(lambda:not c._hilo.is_alive())
        bloques=HistorialReportesRed(ruta).leer()
        assert len(bloques)==1
        assert f'estado_final: {resultado}' in bloques.obtenerValor(0).texto
        assert c.error_pendiente() is None
    finally:c.salir()
    assert len(HistorialReportesRed(ruta).leer())==1


def test_error_del_motor_tambien_deja_reporte(tmp_path,monkeypatch):
    c,ruta=crear(tmp_path)
    try:
        iniciar(c)
        def fallar(comando):raise RuntimeError('fallo controlado QA')
        monkeypatch.setattr(c._controlador,'_aplicar',fallar)
        c.enviar_comando('W')
        assert _esperar(lambda:not c._hilo.is_alive())
        bloques=HistorialReportesRed(ruta).leer()
        assert len(bloques)==1
        assert 'error: RuntimeError: fallo controlado QA' in bloques.obtenerValor(0).texto
        assert 'fallo controlado QA' in c.error_pendiente()
    finally:c.salir()


def test_ruta_no_escribible_conserva_reporte_y_cierra_el_hilo(tmp_path):
    c,_=crear(tmp_path,reportes=str(tmp_path))  # Un directorio no puede ser el archivo de salida.
    iniciar(c)
    c.salir()
    assert c._hilo is None and c.error_pendiente() is None
    assert any('no se pudo guardar en' in linea for linea in c.reporte_red())
