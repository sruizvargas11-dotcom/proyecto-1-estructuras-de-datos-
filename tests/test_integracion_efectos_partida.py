"""Integración extremo a extremo: Partida real (nueva_partida) conectada con
los efectos reales de rol 2, no solo efectos.py en aislamiento.

Confirma que el hook que dejó ROL 4 (Partida.aplicar_efecto, asignado en
controlador/inicio_partida.py) efectivamente dispara aplicar_efecto_objeto
cuando el jugador usa una poción con modificador de velocidad, un antídoto
o una antorcha, con datos reales del catálogo offline donde existen.
"""
from adaptadores.datos_offline import DatosOffline
from controlador.inicio_partida import nueva_partida
from modelo.entidades.objetos.fabrica_objetos import FabricaObjetos
import modelo.efectos as efectos


def _sesion(tmp_path, semilla=777):
    return nueva_partida(DatosOffline(), 'cripta-01', str(tmp_path), semilla=semilla)


def _nodo(jugador, instancia_id):
    for nodo in jugador.inventario.recorrer_desde_frente():
        if nodo.valor.instancia_id == instancia_id:
            return nodo
    return None


def test_aplicar_efecto_queda_conectado_al_arrancar_la_partida(tmp_path):
    sesion = _sesion(tmp_path)
    assert sesion.partida.aplicar_efecto is efectos.aplicar_efecto_objeto


def test_usar_antorcha_real_la_enciende_y_se_apaga_sola(tmp_path):
    """sala_1 (inicial de cripta-01) trae itm_antorcha de verdad."""
    sesion = _sesion(tmp_path)
    partida = sesion.partida
    jugador = partida.jugador
    sala = jugador.sala_actual

    antorcha = None
    for o in sala.objetos_suelo:
        if o.clase == 'antorcha':
            antorcha = o
    assert antorcha is not None
    assert jugador.recoger(antorcha)
    nodo = _nodo(jugador, antorcha.instancia_id)

    assert partida.usar_objeto(nodo) is True
    assert antorcha.encendida is True

    partida.reloj.avanzar_y_ejecutar(partida.reloj.tiempo_actual + antorcha.duracion)
    assert antorcha.encendida is False


def test_usar_antidoto_real_cancela_el_veneno_activo(tmp_path):
    """itm_antidoto existe en el catálogo offline (sala_5), lo resolvemos
    directo para no depender del bucle de movimiento en esta prueba."""
    sesion = _sesion(tmp_path)
    partida = sesion.partida
    jugador = partida.jugador

    sesion.red.resolver_catalogo(['itm_antidoto'])
    ficha = sesion.red.ficha('itm_antidoto')
    antidoto = FabricaObjetos(prefijo='prueba').crear(ficha)
    jugador.inventario.insertar_al_final(antidoto)
    nodo = _nodo(jugador, antidoto.instancia_id)

    efectos.aplicar_veneno(partida.reloj, jugador, dano_por_pulso=5)
    assert jugador.estado_veneno is not None

    assert partida.usar_objeto(nodo) is True
    assert jugador.estado_veneno is None
    assert jugador.evento_veneno is None


def test_usar_pocion_con_modificador_de_velocidad_la_cambia_y_restaura(tmp_path):
    """No hay poción de velocidad en el catálogo offline todavía: se construye
    una ficha de prueba, igual que cualquier otra clase ya validada por
    FabricaObjetos (Sec. 4.3). Esto no inventa reglas, solo prueba el cableado."""
    sesion = _sesion(tmp_path)
    partida = sesion.partida
    jugador = partida.jugador

    ficha = {
        'id': 'itm_pocion_prueba', 'clase': 'pocion', 'nombre': 'Poción de prueba',
        'peso': 1, 'valor': 5, 'cura': 0, 'modificador_velocidad': -40, 'duracion': 150,
    }
    pocion = FabricaObjetos(prefijo='prueba').crear(ficha)
    jugador.inventario.insertar_al_final(pocion)
    nodo = _nodo(jugador, pocion.instancia_id)

    velocidad_original = jugador.velocidad
    assert partida.usar_objeto(nodo) is True
    assert jugador.velocidad == velocidad_original - 40

    partida.reloj.avanzar_y_ejecutar(partida.reloj.tiempo_actual + 150)
    assert jugador.velocidad == velocidad_original