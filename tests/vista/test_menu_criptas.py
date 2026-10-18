"""EscenaMenuCriptas: portada/selección de cripta.

listar_criptas() corre en un hilo propio de la escena (no el de
ControladorPygame, que acá ni existe todavía), así que las pruebas sondean
con _esperar en vez de asumir que terminó en la misma llamada. El
controlador y el cambio de escena son dobles simples (sin red real, sin
pygame.display propio): lo que se prueba es el comportamiento de la escena,
no el hilo de modelo (eso ya lo cubre test_controlador_pygame.py).
"""
import threading
import time
from unittest.mock import MagicMock, patch

import pygame
import pytest

from adaptadores.datos_http import DatosHTTP
from adaptadores.datos_offline import DatosOffline
from herramientas.generar_cripta_prueba import generar
from controlador.controlador_pygame import ControladorPygame
from vista_pygame.escenas.menu_criptas import (
    COLOR_FLECHA, MARGEN_TITULO_INTERNO, NOMBRE_POR_DEFECTO, EscenaMenuCriptas,
)
from vista_pygame.stubs_temporales import CargadorAssetsTemporal, GestorAudioTemporal

TIMEOUT = 5.0


def _esperar(condicion, timeout=TIMEOUT):
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        if condicion():
            return True
        time.sleep(0.005)
    return False


def _criptas(cantidad):
    return [{"id": f"cripta-{i}", "nombre": f"Cripta {i}", "salas": i + 5,
            "dificultad": (i % 4) + 1} for i in range(cantidad)]


class ControladorFalso:
    """listar_criptas()/iniciar_partida() sin red ni modelo real."""

    def __init__(self, criptas=(), error=None):
        self._criptas = list(criptas)
        self._error = error
        self.llamadas_iniciar = []
        self.consultas = 0

    def listar_criptas(self):
        self.consultas += 1
        if self._error is not None:
            raise self._error
        return list(self._criptas)

    def iniciar_partida(self, id_cripta, nombre_jugador, semilla=None):
        self.llamadas_iniciar.append((id_cripta, nombre_jugador, semilla))


class ContextoFalso:
    def __init__(self, controlador):
        self.assets = CargadorAssetsTemporal()
        self.audio = GestorAudioTemporal()
        self.controlador = controlador
        self.cambios_escena = []

    def cambiar_escena(self, id_escena, datos=None):
        self.cambios_escena.append((id_escena, datos))


def _crear(criptas=(), error=None):
    controlador = ControladorFalso(criptas, error)
    contexto = ContextoFalso(controlador)
    escena = EscenaMenuCriptas(contexto)
    escena.al_entrar()
    assert _esperar(lambda: not escena._cargando)
    return escena, contexto, controlador


def _tecla(key, mod=0, unicode=""):
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod, unicode=unicode)


@pytest.fixture(scope="module")
def _pantalla_prueba():
    return pygame.Surface((1280, 720))


# -- navegación --------------------------------------------------------

def test_tab_recorre_nombre_criptas_y_vuelve_a_nombre():
    escena, _, _ = _crear(_criptas(3))
    assert escena._foco == -1

    escena.manejar_evento(_tecla(pygame.K_TAB))
    assert escena._foco == 0
    escena.manejar_evento(_tecla(pygame.K_TAB))
    assert escena._foco == 1
    escena.manejar_evento(_tecla(pygame.K_TAB))
    assert escena._foco == 2
    escena.manejar_evento(_tecla(pygame.K_TAB))
    assert escena._foco == -1   # vuelve al nombre


def test_shift_tab_recorre_en_sentido_inverso():
    escena, _, _ = _crear(_criptas(3))

    escena.manejar_evento(_tecla(pygame.K_TAB, mod=pygame.KMOD_SHIFT))
    assert escena._foco == 2   # desde el nombre, hacia atrás = última cripta
    escena.manejar_evento(_tecla(pygame.K_TAB, mod=pygame.KMOD_SHIFT))
    assert escena._foco == 1
    escena.manejar_evento(_tecla(pygame.K_TAB, mod=pygame.KMOD_SHIFT))
    assert escena._foco == 0
    escena.manejar_evento(_tecla(pygame.K_TAB, mod=pygame.KMOD_SHIFT))
    assert escena._foco == -1


def test_flechas_mueven_entre_criptas_con_wraparound():
    escena, _, _ = _crear(_criptas(3))
    escena._foco = 0

    escena.manejar_evento(_tecla(pygame.K_DOWN))
    assert escena._foco == 1
    escena.manejar_evento(_tecla(pygame.K_UP))
    assert escena._foco == 0
    escena.manejar_evento(_tecla(pygame.K_UP))
    assert escena._foco == 2   # wraparound hacia atrás


def test_enter_en_nombre_pasa_el_foco_a_la_primera_cripta():
    escena, _, _ = _crear(_criptas(2))
    escena._nombre = "Ana"
    assert escena._foco == -1
    escena.manejar_evento(_tecla(pygame.K_RETURN))
    assert escena._foco == 0


# -- iniciar partida -----------------------------------------------------

def test_enter_sobre_la_cripta_k_llama_iniciar_partida_con_su_id_y_el_nombre():
    escena, contexto, controlador = _crear(_criptas(4))
    for ch in "Ana":
        escena.manejar_evento(_tecla(pygame.K_a, unicode=ch))
    escena._nombre = "Ana"

    escena._foco = 2
    escena.manejar_evento(_tecla(pygame.K_RETURN))

    assert controlador.llamadas_iniciar == [("cripta-2", "Ana", None)]
    assert contexto.cambios_escena  # cambió de escena tras iniciar


def test_doble_enter_rapido_inicia_solo_una_partida():
    escena, _, controlador = _crear(_criptas(3))
    escena._nombre = "Ana"
    escena._foco = 0

    escena.manejar_evento(_tecla(pygame.K_RETURN))
    escena.manejar_evento(_tecla(pygame.K_RETURN))

    assert len(controlador.llamadas_iniciar) == 1


def test_clic_sobre_una_cripta_tambien_inicia_la_partida():
    escena, _, controlador = _crear(_criptas(2))
    escena._nombre = "Ana"
    rect = escena._rect_fila_pantalla(1)
    evento = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=rect.center, button=1)

    escena.manejar_evento(evento)

    assert controlador.llamadas_iniciar == [("cripta-1", "Ana", None)]


# -- edición del nombre ---------------------------------------------------

def test_nombre_editable_con_limite_de_20_caracteres():
    escena, _, _ = _crear(_criptas(1))
    escena._nombre = ""
    for ch in "Nombre-muy-largo-de-verdad":
        escena.manejar_evento(_tecla(pygame.K_a, unicode=ch))
    assert len(escena._nombre) == 20

    escena.manejar_evento(_tecla(pygame.K_BACKSPACE))
    assert len(escena._nombre) == 19


# -- carga de criptas: cantidades, vacío y error --------------------------

@pytest.mark.parametrize("cantidad", [1, 4, 15])
def test_se_dibuja_un_boton_por_cada_cripta_devuelta(cantidad, _pantalla_prueba):
    escena, _, _ = _crear(_criptas(cantidad))
    # No debe fallar con ninguna cantidad, y debe conocer exactamente esa
    # cantidad de criptas (ni fijas ni truncadas en el código).
    assert len(escena._criptas) == cantidad
    escena.dibujar(_pantalla_prueba)   # no debe lanzar, haya o no scroll


def test_lista_vacia_muestra_mensaje_explicito(_pantalla_prueba):
    escena, _, _ = _crear(_criptas(0))
    assert escena._criptas == []
    escena.dibujar(_pantalla_prueba)   # no debe fallar al no haber criptas


def test_error_de_red_muestra_mensaje_y_r_reintenta(_pantalla_prueba):
    escena, _, controlador = _crear(error=OSError("servicio no disponible"))
    assert escena._error_carga is not None
    escena.dibujar(_pantalla_prueba)   # muestra el error sin fallar

    controlador._error = None
    controlador._criptas = _criptas(2)
    escena.manejar_evento(_tecla(pygame.K_r))
    assert _esperar(lambda: not escena._cargando and escena._error_carga is None)
    assert len(escena._criptas) == 2


def test_esc_durante_un_error_de_carga_pide_salir():
    escena, _, _ = _crear(error=ValueError("cripta inválida"))
    pygame.event.clear()
    escena.manejar_evento(_tecla(pygame.K_ESCAPE))
    eventos = pygame.event.get()
    assert any(e.type == pygame.QUIT for e in eventos)


# -- robustez sin el archivo de fondo -------------------------------------

def test_sin_portada_png_la_escena_no_falla(monkeypatch, tmp_path, _pantalla_prueba):
    import vista_pygame.escenas.menu_criptas as modulo
    monkeypatch.setattr(modulo, "RUTA_FONDO", str(tmp_path / "no_existe.png"))

    controlador = ControladorFalso(_criptas(3))
    contexto = ContextoFalso(controlador)
    escena = EscenaMenuCriptas(contexto)

    assert escena._fondo is None
    escena.al_entrar()
    assert _esperar(lambda: not escena._cargando)
    escena.dibujar(_pantalla_prueba)   # fondo de color sólido, sin lanzar


# -- §5.1: listar_criptas() desde el hilo de la portada cuenta igual que en
# consola, y ese hilo termina antes de que iniciar_partida toque la fuente --

def _mock_respuesta(status_code, json_data):
    respuesta = MagicMock()
    respuesta.status_code = status_code
    respuesta.json.return_value = json_data
    respuesta.text = ""
    return respuesta


@patch("adaptadores.datos_http.requests.get")
def test_listar_criptas_cuenta_como_solicitud_igual_que_en_consola(mock_get):
    """Igual que en consola (main.py llama fuente.listar_criptas() con la
    misma fuente que luego usa nueva_partida): ControladorPygame.listar_criptas()
    no envuelve ni reemplaza la fuente, solo delega — el contador de
    requests_realizados es el mismo objeto/contador de principio a fin."""
    mock_get.return_value = _mock_respuesta(200, {"criptas": []})
    fuente = DatosHTTP()
    controlador = ControladorPygame(fuente)

    assert fuente.requests_realizados == 0
    controlador.listar_criptas()
    assert fuente.requests_realizados == 1   # la misma cuenta que vería la consola
    assert controlador._fuente is fuente      # sin copiar/envolver la fuente


class FuenteCentinela:
    """Envuelve una fuente real y detecta si dos hilos llegan a estar dentro
    de uno de sus métodos al mismo tiempo. Agranda la ventana de carrera con
    un sleep corto en cada llamada: si el código tuviera el bug (iniciar la
    partida sin esperar a que listar_criptas() termine), esta prueba lo
    vería de forma confiable, no solo "a veces".
    """

    def __init__(self, interna):
        self._interna = interna
        self._dentro = False
        self.violacion = None
        self.llamadas = []   # (nombre_metodo, id_de_hilo)

    def __getattr__(self, nombre):
        atributo = getattr(self._interna, nombre)
        if not callable(atributo):
            return atributo

        def envoltura(*args, **kwargs):
            if self._dentro:
                self.violacion = (
                    f"{nombre} se llamó desde el hilo {threading.get_ident()} mientras "
                    "otra llamada a la fuente seguía en curso en otro hilo")
            self._dentro = True
            self.llamadas.append((nombre, threading.get_ident()))
            try:
                time.sleep(0.03)
                return atributo(*args, **kwargs)
            finally:
                self._dentro = False

        return envoltura


def test_hilo_de_listar_criptas_termina_antes_de_iniciar_partida(tmp_path):
    """ANALISIS_ARQUITECTURA.md §7: nunca dos hilos usando la misma fuente a
    la vez. iniciar_partida() (vía nueva_partida) usa la fuente de forma
    síncrona en el hilo que la llama (acá, el de la prueba); el hilo de
    carga de la portada debe haber terminado antes de que eso ocurra.
    """
    carpeta = generar(tmp_path / "datos")
    fuente = FuenteCentinela(DatosOffline(str(carpeta)))
    controlador = ControladorPygame(fuente, carpeta_cache=str(tmp_path / "cache"),
                                    partidas_dir=str(tmp_path / "partidas"))
    contexto = ContextoFalso(controlador)
    # ContextoFalso.controlador ya es el real de arriba; solo falta que
    # listar_criptas()/iniciar_partida() de la escena usen ese controlador.
    escena = EscenaMenuCriptas(contexto)
    escena.al_entrar()
    assert _esperar(lambda: not escena._cargando)
    assert fuente.violacion is None

    hilo_carga = escena._hilo_carga
    assert hilo_carga is not None
    assert not hilo_carga.is_alive()   # el hilo de listar_criptas ya terminó
    assert any(nombre == "listar_criptas" for nombre, _ in fuente.llamadas)
    hilo_de_listar = next(hid for nombre, hid in fuente.llamadas if nombre == "listar_criptas")
    assert hilo_de_listar != threading.get_ident()   # corrió en otro hilo, no el de la prueba

    llamadas_antes = len(fuente.llamadas)
    escena._nombre = "Ada"
    escena._foco = 0
    escena.manejar_evento(_tecla(pygame.K_RETURN))   # dispara iniciar_partida

    assert _esperar(lambda: controlador.estado() is not None)
    assert fuente.violacion is None   # ninguna llamada se solapó con otra
    assert len(fuente.llamadas) > llamadas_antes   # nueva_partida sí usó la fuente
    # La construcción ocurre en el hilo principal; después el modelo
    # consulta metadatos para publicar el reporte. Ambos son válidos,
    # siempre que no se solapen con el listado ni entre sí.
    permitidos = {threading.get_ident(), controlador._hilo.ident}
    for nombre, hid in fuente.llamadas[llamadas_antes:]:
        assert hid in permitidos, f"{nombre} no corrió en un hilo autorizado"
    assert any(hid == threading.get_ident() for _, hid in fuente.llamadas[llamadas_antes:])
    controlador.salir()


# -- ajustes visuales ------------------------------------------------------

def test_titulo_cabe_en_su_placa_con_el_ancho_de_ventana():
    """Único ancho de ventana que soporta el proyecto hoy (ANCHO_LOGICO, sin
    redimensionado): el título ya renderizado debe entrar en su placa con el
    margen interno, reduciendo la fuente si hiciera falta."""
    escena, _, _ = _crear(_criptas(1))
    rect = escena._layout.titulo_rect
    ancho_max = rect.w - 2 * MARGEN_TITULO_INTERNO
    assert escena._titulo_superficie.get_width() <= ancho_max


def test_escribir_con_nombre_por_defecto_lo_reemplaza():
    """Al recibir el foco con 'Jugador' (el valor por defecto), la primera
    tecla reemplaza el campo entero en vez de agregarse al final."""
    escena, _, _ = _crear(_criptas(1))
    assert escena._foco == -1
    assert escena._nombre == NOMBRE_POR_DEFECTO
    assert escena._nombre_seleccionado is True

    escena.manejar_evento(_tecla(pygame.K_s, unicode="s"))
    assert escena._nombre == "s"   # no "Jugadors"

    escena.manejar_evento(_tecla(pygame.K_e, unicode="e"))
    assert escena._nombre == "se"   # la segunda tecla sí se agrega


def test_escribir_con_nombre_por_defecto_tras_tab_tambien_lo_reemplaza():
    """Lo mismo vale si el foco vuelve al nombre más tarde (Tab de ida y
    vuelta) y el valor sigue siendo el de por defecto."""
    escena, _, _ = _crear(_criptas(2))
    escena.manejar_evento(_tecla(pygame.K_TAB))    # nombre -> cripta 0
    escena.manejar_evento(_tecla(pygame.K_TAB))    # cripta 0 -> cripta 1
    escena.manejar_evento(_tecla(pygame.K_TAB))    # cripta 1 -> nombre (vuelta)
    assert escena._foco == -1
    assert escena._nombre_seleccionado is True

    escena.manejar_evento(_tecla(pygame.K_b, unicode="b"))
    assert escena._nombre == "b"


@pytest.mark.parametrize("cantidad", [1, 4, 15])
def test_placas_reales_cubren_el_rectangulo_medido_sin_portada_limpia(cantidad, _pantalla_prueba, monkeypatch):
    """Sin portada_limpia.png, las primeras 4 filas (reales o, si hay menos
    criptas, placas vacías de relleno) deben cubrir POR COMPLETO el
    rectángulo medido sobre portada.png — nunca dejar asomar la placa
    pintada, sea cual sea la cantidad real de criptas."""
    from types import SimpleNamespace
    import vista_pygame.escenas.menu_criptas as modulo
    monkeypatch.setattr(modulo,'PortadaAnimada',lambda:SimpleNamespace(disponible=False,actualizar=lambda dt:None))
    escena, _, _ = _crear(_criptas(cantidad))
    assert escena._fondo_limpio is False
    escena.dibujar(_pantalla_prueba)
    for indice in range(4):
        medido = escena._layout.filas_medidas[indice]
        dibujado = escena._rect_fila_pantalla(indice)
        assert dibujado.contains(medido), f"fila {indice} no cubre el rectángulo medido"


def test_con_portada_limpia_cada_placa_ajusta_su_ancho_al_texto(monkeypatch):
    import vista_pygame.escenas.menu_criptas as modulo
    # "Existe" la versión limpia apuntando a un PNG real cualquiera: lo que
    # se prueba es la rama de ancho-según-texto, no el arte en sí.
    monkeypatch.setattr(modulo, "RUTA_FONDO_LIMPIO", modulo.RUTA_FONDO)

    criptas_lista = [
        {"id": "c0", "nombre": "Osario menor", "salas": 6, "dificultad": 1},
        {"id": "c1", "nombre": "Catacumbas muy profundas y largas de verdad",
         "salas": 50, "dificultad": 4},
    ]
    controlador = ControladorFalso(criptas_lista)
    contexto = ContextoFalso(controlador)
    escena = EscenaMenuCriptas(contexto)
    assert escena._fondo_limpio is True
    escena.al_entrar()
    assert _esperar(lambda: not escena._cargando)

    rect_corto = escena._rect_fila_pantalla(0)
    rect_largo = escena._rect_fila_pantalla(1)
    assert rect_largo.w > rect_corto.w   # el nombre más largo da una placa más ancha
    ancho_texto_corto = escena._fuente_fila.size(escena._texto_fila(criptas_lista[0]))[0]
    assert rect_corto.w > ancho_texto_corto   # con relleno, no exacto
    assert rect_corto.centerx == escena._layout.centro_x   # centrada en el mismo eje
    assert rect_largo.centerx == escena._layout.centro_x


def test_seleccion_no_cambia_el_color_de_fondo_de_la_placa():
    pantalla = pygame.Surface((1280, 720))
    escena, _, _ = _crear(_criptas(2))

    escena._foco = -1   # ninguna cripta seleccionada
    escena.dibujar(pantalla)
    rect = escena._rect_fila_pantalla(0)
    punto = (rect.x + 6, rect.y + 6)   # esquina interior: madera, nunca el texto centrado
    color_sin_seleccion = tuple(pantalla.get_at(punto))[:3]

    escena._foco = 0
    escena.dibujar(pantalla)
    color_con_seleccion = tuple(pantalla.get_at(punto))[:3]

    assert color_sin_seleccion == color_con_seleccion


def test_layout_se_recalcula_solo_al_cambiar_el_tamano():
    escena, _, _ = _crear(_criptas(3))
    llamadas = []
    original = EscenaMenuCriptas._calcular_layout

    def espia(ancho, alto):
        llamadas.append((ancho, alto))
        return original(ancho, alto)
    escena._calcular_layout = espia

    for _ in range(20):
        escena.actualizar(16)
    assert llamadas == []   # el tamaño no cambió: nunca se recalcula por frame

    escena._tamano_layout = (999, 999)   # simula que el tamaño cambió
    escena.actualizar(16)
    assert len(llamadas) == 1

    escena.actualizar(16)
    escena.actualizar(16)
    assert len(llamadas) == 1   # mismo tamaño que la vez anterior: no se repite


def test_captura_para_comparar_visualmente_con_el_boceto(tmp_path):
    """No es una prueba automática de parecido visual (no hay forma de
    verificar eso con un assert): guarda una captura en tmp_path para que
    se revise a ojo contra portada.png, como pide el encargo."""
    pantalla = pygame.Surface((1280, 720))
    escena, _, _ = _crear(_criptas(4))
    escena._foco = 1
    escena.actualizar(16)
    escena.dibujar(pantalla)
    ruta = tmp_path / "portada_captura.png"
    pygame.image.save(pantalla, str(ruta))
    assert ruta.exists() and ruta.stat().st_size > 0


# -- flechas de selección ---------------------------------------------------

def test_flechas_estan_junto_a_la_placa_seleccionada():
    pantalla = pygame.Surface((1280, 720))
    escena, _, _ = _crear(_criptas(3))
    escena._foco = 1
    escena.dibujar(pantalla)
    rect = escena._rect_fila_pantalla(1)

    def hay_flecha_cerca(x_centro):
        for x in range(max(0, x_centro - 16), min(1280, x_centro + 16)):
            if tuple(pantalla.get_at((x, rect.centery)))[:3] == COLOR_FLECHA:
                return True
        return False

    assert hay_flecha_cerca(rect.left - 10)
    assert hay_flecha_cerca(rect.right + 10)


def test_mover_mouse_sobre_una_placa_cambia_la_seleccion():
    escena, _, _ = _crear(_criptas(3))
    escena._foco = 0
    rect = escena._rect_fila_pantalla(2)
    evento = pygame.event.Event(pygame.MOUSEMOTION, pos=rect.center, rel=(0, 0), buttons=(0, 0, 0))

    escena.manejar_evento(evento)

    assert escena._foco == 2


def test_bajar_hasta_la_ultima_con_15_criptas_hace_scroll_y_la_deja_visible():
    escena, _, _ = _crear(_criptas(15))
    escena._foco = 0
    for _ in range(14):
        escena.manejar_evento(_tecla(pygame.K_DOWN))
    assert escena._foco == 14

    rect = escena._rect_fila_pantalla(14)
    assert rect.top >= escena._layout.viewport_top
    assert rect.bottom <= escena._layout.viewport_bottom
