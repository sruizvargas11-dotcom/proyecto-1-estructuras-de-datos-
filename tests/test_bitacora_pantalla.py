import tracemalloc

from adaptadores.datos_offline import DatosOffline
from controlador.controlador_juego import ControladorJuego
from controlador.inicio_partida import nueva_partida
from estructuras.array_circular import ArrayCircular
from vista.vista_consola import CAPACIDAD_MENSAJES, VistaConsola


def _vista():
    lineas = []
    vista = VistaConsola(leer=lambda *_: "Q", escribir=lambda texto="": lineas.append(texto))
    return vista, lineas


def _lineas_de_mensaje(lineas):
    return [linea.strip() for linea in lineas if linea.strip().startswith("[t=")]


def _ultima_pantalla(lineas):
    inicio = max(i for i, linea in enumerate(lineas) if linea.startswith("====="))
    return lineas[inicio:]


def test_la_capacidad_es_20():
    assert CAPACIDAD_MENSAJES == 20


def test_con_menos_de_20_muestra_todos_en_orden():
    buffer = ArrayCircular(20)
    for i in range(5):
        buffer.agregarValor(i)
    assert buffer.listar_en_orden() == [0, 1, 2, 3, 4]


def test_tras_varias_vueltas_quedan_los_ultimos_20_del_mas_antiguo_al_mas_nuevo():
    buffer = ArrayCircular(20)
    for i in range(47):
        buffer.agregarValor(i)
    assert buffer.listar_en_orden() == list(range(27, 47))
    assert buffer.contador_sobrescrituras == 47 - 20


def test_agregar_escribe_una_sola_posicion_y_no_desplaza_las_demas():
    buffer = ArrayCircular(20)
    for i in range(20):
        buffer.agregarValor(f"m{i}")
    for i in range(20, 65):
        antes = list(buffer._datos)
        buffer.agregarValor(f"m{i}")
        cambiadas = [p for p in range(20) if buffer._datos[p] is not antes[p]]
        # Solo cambia la casilla del más antiguo; los 19 restantes siguen siendo
        # exactamente los mismos objetos en las mismas posiciones.
        assert cambiadas == [(i - 20) % 20]
        assert buffer._datos[cambiadas[0]] == f"m{i}"


def test_el_almacenamiento_es_el_mismo_arreglo_de_20_toda_la_partida():
    buffer = ArrayCircular(20)
    arreglo = buffer._datos
    for i in range(20000):
        buffer.agregarValor(f"mensaje {i}")
    assert buffer._datos is arreglo and len(arreglo) == 20 and len(buffer) == 20


def test_la_memoria_no_crece_con_la_cantidad_de_mensajes():
    vista, _ = _vista()

    def medir(cantidad):
        tracemalloc.start()
        for i in range(cantidad):
            vista.agregar_mensaje(i, f"Mensaje de prueba número {i % 1000:04d}")
        actual, _ = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return actual

    poco = medir(1000)
    mucho = medir(100000)       # 100 veces más mensajes
    assert mucho - poco < 4096  # mismo consumo, salvo ruido de medición
    assert len(vista.mensajes()) == 20


def test_la_pantalla_muestra_solo_los_ultimos_20():
    vista, lineas = _vista()
    for i in range(30):
        vista.agregar_mensaje(i, f"evento {i}")
    sesion = nueva_partida(DatosOffline(), "cripta-01", None, semilla=3)
    vista.mostrar_estado(sesion.partida)
    mostrados = _lineas_de_mensaje(lineas)
    assert len(mostrados) == 20
    assert mostrados[0] == "[t=10] evento 10" and mostrados[-1] == "[t=29] evento 29"


def test_partida_larga_solo_20_mensajes_en_cada_pantalla(tmp_path):
    sesion = nueva_partida(DatosOffline(), "cripta-01", str(tmp_path / "cache"), semilla=3)
    sesion.partida.jugador.vida_max = sesion.partida.jugador.vida = 300
    comandos = iter(["W"] * 60 + ["Q"])
    leidos = []

    def leer(*_):
        leidos.append(next(comandos))
        return leidos[-1]

    lineas = []
    vista = VistaConsola(leer=leer, escribir=lambda texto="": lineas.append(texto))
    por_pantalla = []
    mostrar = vista.mostrar_estado

    def mostrar_y_contar(partida):
        antes = len(lineas)
        mostrar(partida)
        por_pantalla.append(len(_lineas_de_mensaje(lineas[antes:])))

    vista.mostrar_estado = mostrar_y_contar
    ControladorJuego(sesion, vista).jugar()

    assert vista._mensajes.contador_agregados >= 60    # muchos más que 20
    # Una pantalla por cada decisión (60 W + Q); mostrar_fin puede redibujar el
    # estado una vez más al terminar, así que no se fija el total exacto.
    assert len(leidos) == 61 and len(por_pantalla) >= len(leidos)
    assert max(por_pantalla) == 20 and all(n <= 20 for n in por_pantalla)
    assert vista.mensajes()[-1] == "[t=5900] Esperas."
    # La pantalla final del juego tampoco muestra más de 20.
    assert len(_lineas_de_mensaje(_ultima_pantalla(lineas))) == 20


def test_solo_guarda_texto_sin_referencias_al_modelo(tmp_path):
    sesion = nueva_partida(DatosOffline(), "cripta-01", str(tmp_path / "cache"), semilla=3)
    sesion.partida.jugador.vida_max = sesion.partida.jugador.vida = 300
    comandos = iter(["N", "A", "A", "A", "W", "W", "Q"])
    vista = VistaConsola(leer=lambda *_: next(comandos), escribir=lambda *_: None)
    ControladorJuego(sesion, vista).jugar()
    guardados = [valor for valor in vista._mensajes._datos if valor is not None]
    assert guardados and all(type(valor) is str for valor in guardados)
