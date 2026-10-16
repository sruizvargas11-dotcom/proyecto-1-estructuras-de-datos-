from adaptadores.datos_offline import DatosOffline
from controlador.controlador_juego import ControladorJuego
from controlador.inicio_partida import nueva_partida
from modelo import efectos
from modelo.entidades.objetos.fabrica_objetos import FabricaObjetos
from vista.vista_consola import CAPACIDAD_MENSAJES, VistaConsola


class Pantalla:
    """Captura lo que la vista escribe y le entrega entradas de una lista."""

    def __init__(self, entradas=()):
        self.lineas = []
        self._entradas = list(entradas)

    def escribir(self, texto=""):
        self.lineas.append(texto)

    def leer(self, prompt=""):
        if not self._entradas:
            raise EOFError
        return self._entradas.pop(0)

    def texto(self):
        return "\n".join(self.lineas)


def _vista(entradas=()):
    pantalla = Pantalla(entradas)
    return VistaConsola(leer=pantalla.leer, escribir=pantalla.escribir), pantalla


def _sesion(tmp_path, semilla=3, vida=300):
    sesion = nueva_partida(DatosOffline(), "cripta-01", str(tmp_path / "cache"),
                           semilla=semilla)
    jugador = sesion.partida.jugador
    jugador.vida_max = jugador.vida = vida
    return sesion


def _dar(sesion, tipo_id):
    sesion.red.resolver_catalogo([tipo_id])
    objeto = FabricaObjetos(prefijo="prueba").crear(sesion.red.ficha(tipo_id))
    sesion.partida.jugador.inventario.insertar_al_final(objeto)
    return objeto



def test_bitacora_en_pantalla_guarda_solo_los_ultimos_20_en_orden():
    vista, _ = _vista()
    for i in range(25):
        vista.agregar_mensaje(i, f"m{i}")
    mensajes = vista.mensajes()
    assert len(mensajes) == CAPACIDAD_MENSAJES == 20
    assert mensajes[0] == "[t=5] m5" and mensajes[-1] == "[t=24] m24"



def test_estado_muestra_lo_necesario_para_decidir(tmp_path):
    sesion = _sesion(tmp_path)
    vista, pantalla = _vista()
    partida = sesion.partida
    destino = partida.cripta.sala_por_id(2)
    partida.entrar_a_sala(destino)
    vista.mostrar_estado(partida)
    texto = pantalla.texto()
    assert "Pasillo de las urnas (sala 2)" in texto
    assert "Vida" in texto and "/300" in texto
    assert "E  Nicho sellado (cerrada, sin llave)" in texto
    # Enemigos identificables por instancia_id.
    assert "1. Rata gigante #e-201" in texto and "2. Rata gigante #e-202" in texto
    assert "1. Daga oxidada (+3 ataque)" in texto
    assert "Dardos en la pared (desarmada, se rearma en t=300)" in texto
    assert "Inventario (0/10): vacío" in texto


def test_estado_muestra_efectos_activos(tmp_path):
    sesion = _sesion(tmp_path)
    partida, jugador = sesion.partida, sesion.partida.jugador
    reloj = partida.reloj
    efectos.aplicar_veneno(reloj, jugador, 2)
    efectos.aplicar_modificador_velocidad(reloj, jugador, 50, 300)
    antorcha = _dar(sesion, "itm_antorcha")
    efectos.encender_antorcha(reloj, antorcha)
    vista, pantalla = _vista()
    vista.mostrar_estado(partida)
    texto = pantalla.texto()
    assert "envenenado (2 por pulso, 5 restantes, próximo t=80)" in texto
    assert "velocidad alterada hasta t=300" in texto
    assert "Antorcha encendida hasta t=2000" in texto
    assert "Antorcha [encendida]" in texto


def test_puerta_abierta_con_cierre_automatico_muestra_cuando_se_cierra(tmp_path):
    sesion = _sesion(tmp_path)
    partida = sesion.partida
    sala = partida.cripta.sala_por_id(2)
    partida.entrar_a_sala(sala)
    partida.abrir(sala.salida_hacia("E"))
    vista, pantalla = _vista()
    vista.mostrar_estado(partida)
    assert "E  Nicho sellado (abierta, se cierra en t=500)" in pantalla.texto()



def test_inventario_y_ayuda_salen_debajo_del_siguiente_estado(tmp_path):
    sesion = _sesion(tmp_path)
    _dar(sesion, "itm_coraza_cuero")
    _dar(sesion, "itm_daga_oxidada")
    vista, pantalla = _vista()
    jugador = sesion.partida.jugador
    vista.mostrar_inventario(sesion.partida, jugador.inventario_ordenado("peso"), "peso")
    assert pantalla.lineas == []        # no se imprime hasta el próximo estado
    vista.mostrar_estado(sesion.partida)
    texto = pantalla.texto()
    assert "vista ordenada por peso" in texto
    panel = texto[texto.index("vista ordenada por peso"):]
    assert panel.index("Daga oxidada") < panel.index("Coraza de cuero")
    # El panel se muestra una sola vez.
    pantalla.lineas.clear()
    vista.mostrar_estado(sesion.partida)
    assert "vista ordenada" not in pantalla.texto()


def test_la_vista_ordenada_no_altera_el_orden_real(tmp_path):
    sesion = _sesion(tmp_path)
    _dar(sesion, "itm_coraza_cuero")
    _dar(sesion, "itm_daga_oxidada")
    jugador = sesion.partida.jugador
    VistaConsola(escribir=lambda *_: None).mostrar_inventario(
        sesion.partida, jugador.inventario_ordenado("peso"), "peso")
    reales = [n.valor.nombre for n in jugador.inventario.recorrer_desde_frente()]
    assert reales == ["Coraza de cuero", "Daga oxidada"]



def test_elegir_cripta_por_numero_id_o_enter():
    criptas = [{"id": "c-1", "nombre": "Una"}, {"id": "c-2", "nombre": "Dos"}]
    assert _vista(["2"])[0].elegir_cripta(criptas) == "c-2"
    assert _vista(["c-1"])[0].elegir_cripta(criptas) == "c-1"
    assert _vista([""])[0].elegir_cripta(criptas) == "c-1"
    vista, pantalla = _vista(["9", "x", "2"])
    assert vista.elegir_cripta(criptas) == "c-2"
    assert pantalla.texto().count("Opción inválida") == 2


def test_fin_de_entrada_es_salida_controlada():
    vista, _ = _vista([])
    assert vista.leer_comando() == "Q"



def test_pulsos_de_veneno_llegan_a_la_bitacora_en_pantalla(tmp_path):
    sesion = _sesion(tmp_path, vida=300)
    efectos.aplicar_veneno(sesion.partida.reloj, sesion.partida.jugador, 3)
    vista, _ = _vista(["W", "W", "W", "W", "W"])
    ControladorJuego(sesion, vista).jugar()
    pulsos = [m for m in vista.mensajes() if "veneno te quema" in m]
    assert pulsos[0] == "[t=80] El veneno te quema: -3 de vida."
    assert len(pulsos) == 5 and "se disipa" in pulsos[-1]


def test_el_veneno_puede_matar_sin_que_actue_nadie_mas(tmp_path):
    # Sala inicial sin enemigos: antes la agenda podía quedar sin el turno del
    # jugador y el bucle fallaba; ahora el pulso letal termina la partida.
    sesion = _sesion(tmp_path, vida=5)
    efectos.aplicar_veneno(sesion.partida.reloj, sesion.partida.jugador, 3)
    vista, pantalla = _vista(["W", "W", "W"])
    estado = ControladorJuego(sesion, vista).jugar()
    assert estado == "derrota"
    assert "Derrota" in pantalla.texto()


def test_eventos_lejanos_no_se_narran(tmp_path):
    sesion = _sesion(tmp_path)
    partida = sesion.partida
    sala2 = partida.cripta.sala_por_id(2)
    partida.entrar_a_sala(sala2)                  # activa la trampa (rearme t=300)
    partida.entrar_a_sala(partida.cripta.sala_por_id(1))
    vista, _ = _vista(["W", "W", "W", "W"])
    ControladorJuego(sesion, vista).jugar()
    assert not [m for m in vista.mensajes() if "vuelve a estar armada" in m]
