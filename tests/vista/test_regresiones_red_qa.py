"""Regresiones F2-01/F2-02: sesiones HTTP y recuperación de la portada."""
import time
from urllib.parse import urlsplit
from unittest.mock import Mock, patch

import pygame
import pytest

from adaptadores.datos_http import DatosHTTP
from adaptadores.datos_offline import DatosOffline
from herramientas.generar_cripta_prueba import generar
from controlador.controlador_pygame import ControladorPygame
from vista_pygame.escenas.menu_criptas import EscenaMenuCriptas
from tests.vista.test_menu_criptas import ContextoFalso


def _esperar(condicion):
    limite = time.monotonic() + 8
    while not condicion() and time.monotonic() < limite:
        time.sleep(.002)
    assert condicion(), 'El controlador no publicó el resultado'


def test_dos_partidas_http_comparten_uuid_y_preservan_contadores(tmp_path):
    fuente_local = DatosOffline(str(generar(tmp_path / 'datos')))
    peticiones = []

    def responder(url, headers, params, timeout):
        ruta = urlsplit(url).path.removeprefix('/v1')
        peticiones.append((ruta, headers['X-Cripta-Client-Id']))
        if len(peticiones) == 1:
            return Mock(status_code=429, json=lambda: {'reintentar_en': 0})
        partes = ruta.strip('/').split('/')
        if ruta == '/criptas':
            datos = fuente_local.listar_criptas()
        elif ruta == '/catalogo/version':
            datos = fuente_local.version_catalogo()
        elif ruta == '/catalogo':
            datos = fuente_local.catalogo(params['ids'].split(','))
        elif len(partes) == 2:
            datos = fuente_local.datos_cripta(partes[1])
        elif partes[2] == 'salas':
            datos = fuente_local.esqueleto_cripta(partes[1], params['pagina'])
        elif partes[2] == 'version':
            datos = fuente_local.version_cripta(partes[1])
        else:
            datos = fuente_local.contenido_salas(
                partes[1], [int(x) for x in params['salas'].split(',')])
        return Mock(status_code=200, json=lambda: datos)

    c = ControladorPygame(DatosHTTP(), str(tmp_path / 'cache'),
                          partidas_dir=str(tmp_path / 'partidas'),
                          reportes=str(tmp_path / 'reportes.txt'))
    fuentes = []
    contadores = []
    try:
        with patch('adaptadores.datos_http.requests.get', responder), \
                patch('adaptadores.datos_http.DatosHTTP._esperar_reintento'):
            for semilla in (72, 73):
                c.listar_criptas()
                c.iniciar_partida('cripta-prueba', 'QA', semilla)
                _esperar(lambda: c.estado() is not None and not c.esperando_red())
                c.enviar_comando('R 1')
                _esperar(lambda: c.estado().acciones_jugador == 1 and not c.esperando_red())
                c.salir()
                fuentes.append(c._fuente)
                contadores.append(c._fuente.requests_realizados)
        ids = [client_id for _, client_id in peticiones]
        assert all(client_id == ids[0] for client_id in ids)
        assert fuentes[0] is not fuentes[1]
        assert fuentes[0].requests_realizados == contadores[0]
        assert sum(contadores) == len(peticiones)  # Incluye el 429.
        assert all(f.requests_realizados <= f.presupuesto for f in fuentes)
    finally:
        c.salir()


@pytest.mark.parametrize('datos', [
    {}, {'criptas': None}, {'criptas': [{}]}, {'criptas': [None]},
    {'criptas': [{'id': 'qa', 'nombre': None, 'salas': 1, 'dificultad': 1}]},
    {'criptas': [{'id': 'qa', 'nombre': 'QA', 'salas': True, 'dificultad': 1}]},
])
def test_listado_invalido_termina_carga_y_r_recupera(tmp_path, datos):
    fuente = DatosHTTP()
    c = ControladorPygame(fuente, partidas_dir=str(tmp_path))
    menu = EscenaMenuCriptas(ContextoFalso(c))
    valido = {'criptas': [{'id': 'qa', 'nombre': 'Cripta QA', 'salas': 1,
                           'dificultad': 0}]}
    respuestas = [Mock(status_code=200, json=lambda: datos),
                  Mock(status_code=200, json=lambda: valido)]
    with patch('adaptadores.datos_http.requests.get', side_effect=respuestas), \
            patch('threading.excepthook') as error_hilo:
        menu.al_entrar()
        menu._hilo_carga.join(3)
        assert not menu._cargando
        assert menu._error_carga and '/criptas' in menu._error_carga
        assert menu._criptas == []
        menu.dibujar(pygame.Surface((1280, 720)))
        menu.manejar_evento(pygame.event.Event(
            pygame.KEYDOWN, key=pygame.K_r, mod=0, unicode='r'))
        menu._hilo_carga.join(3)
        assert not menu._cargando and menu._error_carga is None
        assert menu._criptas == valido['criptas']
        assert fuente.requests_realizados == 2
        error_hilo.assert_not_called()
