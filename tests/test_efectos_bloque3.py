"""Efectos temporales reales del rol 2 (Sec. 2.10, Apéndice B): veneno,
cambio de velocidad, antorcha y regeneración, con sus inversas por deltas.
"""
import pytest

from modelo.reloj import Reloj
from modelo.historial import Historial
from modelo.entorno import Entorno
from modelo.entidades.actor import Actor
from modelo.entidades.enemigo import Enemigo
from modelo.entidades.trampa import Trampa
from modelo.entidades.objetos.antorcha import Antorcha
from modelo.mundo.sala import Sala
import modelo.efectos as efectos


def sistema():
    h = Historial()
    r = Reloj(11, h)
    sala = Sala(1, 'inicio')
    jugador = Actor('j', 100, 10, 2, 100, sala)
    r.vincular_actor(jugador)
    return h, r, jugador


def rata(velocidad=150):
    return Enemigo('e-1', 'ent_rata_gigante', 'Rata', 12, 5, 1, velocidad, 'errante')


# ---------------------------------------------------------------------------
# Veneno
# ---------------------------------------------------------------------------

def test_veneno_pulsa_cada_80_hasta_los_5_pulsos_de_400():
    h, r, j = sistema()
    efectos.aplicar_veneno(r, j, dano_por_pulso=2)

    tiempos = []
    while r.avanzar_y_ejecutar(1000) or True:
        if r.agenda.minimo() is None:
            break
    # Avanzamos todo de una vez; comprobamos el resultado acumulado.
    assert j.vida == 100 - 2 * 5
    assert j.estado_veneno is None
    assert j.evento_veneno is None


def test_veneno_pulso_en_el_limite_400_se_ejecuta():
    h, r, j = sistema()
    efectos.aplicar_veneno(r, j, dano_por_pulso=1, pulsos=5, intervalo=80)
    r.avanzar_y_ejecutar(399)
    assert j.vida == 100 - 4  # los primeros 4 pulsos: 80,160,240,320
    r.avanzar_y_ejecutar(400)
    assert j.vida == 100 - 5  # el quinto pulso cae justo en 400 y sí ocurre
    assert j.estado_veneno is None


def test_antidoto_antes_del_proximo_pulso_evita_ese_dano():
    h, r, j = sistema()
    efectos.aplicar_veneno(r, j, dano_por_pulso=3)
    r.avanzar_y_ejecutar(50)  # todavía no llega el primer pulso (80)
    assert efectos.cancelar_veneno(r, j)
    r.avanzar_y_ejecutar(1000)
    assert j.vida == 100  # ningún pulso llegó a aplicarse
    assert j.estado_veneno is None and j.evento_veneno is None


def test_cancelar_veneno_sin_veneno_activo_no_hace_nada():
    h, r, j = sistema()
    assert efectos.cancelar_veneno(r, j) is False


def test_reaplicar_veneno_reinicia_el_conteo_de_pulsos():
    h, r, j = sistema()
    efectos.aplicar_veneno(r, j, dano_por_pulso=1, pulsos=5)
    r.avanzar_y_ejecutar(80)  # un pulso: vida 99, quedan 4 pulsos
    assert j.vida == 99

    efectos.aplicar_veneno(r, j, dano_por_pulso=5, pulsos=5)  # reinicia
    r.avanzar_y_ejecutar(1000)
    # 1 pulso viejo (1) + 5 pulsos nuevos (5 c/u) = 1 + 25
    assert j.vida == 100 - 1 - 25


def test_veneno_revertido_por_historial_restaura_vida_y_agenda():
    h, r, j = sistema()
    h.iniciar_accion(r)
    efectos.aplicar_veneno(r, j, dano_por_pulso=4)
    r.avanzar_y_ejecutar(80)
    assert j.vida == 96
    h.confirmar_accion()

    assert h.revertir()
    assert j.vida == 100
    assert j.estado_veneno is None
    assert j.evento_veneno is None


def test_veneno_mata_si_el_dano_acumulado_supera_la_vida():
    h, r, j = sistema()
    efectos.aplicar_veneno(r, j, dano_por_pulso=30, pulsos=5)
    r.avanzar_y_ejecutar(80)
    assert j.vida == 70
    r.avanzar_y_ejecutar(160)
    assert j.vida == 40
    r.avanzar_y_ejecutar(240)
    assert j.vida == 10
    r.avanzar_y_ejecutar(320)
    assert j.vida == 0 and j.vivo is False
    # Al morir no debe quedar un quinto pulso programado para un actor muerto.
    r.avanzar_y_ejecutar(1000)
    assert j.vida == 0


def test_veneno_se_integra_con_activar_trampa_via_aplicar_efecto():
    """Entorno.activar_trampa(trampa, actor, aplicar_efecto=...) es el punto
    de conexión ya existente; aquí lo usamos con un veneno de daño 3."""
    h, r, j = sistema()
    trampa = Trampa('t-1', 'trp_dardos', 'Dardos', 4, 300)

    def conectar_veneno(trampa, actor, reloj):
        efectos.aplicar_veneno(reloj, actor, dano_por_pulso=3)

    Entorno(r).activar_trampa(trampa, j, aplicar_efecto=conectar_veneno)
    assert j.estado_veneno is not None
    r.avanzar_y_ejecutar(80)
    assert j.vida == 97


# ---------------------------------------------------------------------------
# Cambio de velocidad
# ---------------------------------------------------------------------------

def test_modificador_de_velocidad_cambia_velocidad_y_se_revierte_al_expirar():
    h, r, j = sistema()
    r.programar_inicial(j, lambda reloj: None)
    assert j.velocidad == 100

    efectos.aplicar_modificador_velocidad(r, j, modificador=-50, duracion=200)
    assert j.velocidad == 50

    r.avanzar_y_ejecutar(200)
    assert j.velocidad == 100
    assert j.evento_mod_velocidad is None


def test_modificador_de_velocidad_reajusta_el_turno_pendiente():
    h, r, j = sistema()
    r.programar(j, 100, lambda reloj: None)  # próxima acción en t=100 (vel 100)
    tiempo_original = j.evento_actual.tiempo
    assert tiempo_original == 100

    efectos.aplicar_modificador_velocidad(r, j, modificador=-50, duracion=10)
    # Progreso proporcional: restante*vel_anterior//vel_nueva = 100*100//50 = 200
    assert j.evento_actual.tiempo == 200


def test_no_se_puede_apilar_dos_modificadores_de_velocidad_activos():
    h, r, j = sistema()
    efectos.aplicar_modificador_velocidad(r, j, modificador=10, duracion=100)
    with pytest.raises(ValueError):
        efectos.aplicar_modificador_velocidad(r, j, modificador=5, duracion=50)


def test_modificador_de_velocidad_revertido_por_historial():
    h, r, j = sistema()
    h.iniciar_accion(r)
    efectos.aplicar_modificador_velocidad(r, j, modificador=-20, duracion=100)
    assert j.velocidad == 80
    h.confirmar_accion()

    assert h.revertir()
    assert j.velocidad == 100
    assert j.evento_mod_velocidad is None


# ---------------------------------------------------------------------------
# Antorcha
# ---------------------------------------------------------------------------

def test_antorcha_se_apaga_sola_tras_su_duracion():
    h, r, j = sistema()
    antorcha = Antorcha('i-1', 'itm_antorcha', 'Antorcha', 1, 5, duracion=2000)

    assert efectos.encender_antorcha(r, antorcha)
    assert antorcha.encendida is True

    r.avanzar_y_ejecutar(1999)
    assert antorcha.encendida is True

    r.avanzar_y_ejecutar(2000)
    assert antorcha.encendida is False
    assert antorcha.evento_apagado is None


def test_encender_antorcha_ya_encendida_no_hace_nada():
    h, r, j = sistema()
    antorcha = Antorcha('i-1', 'itm_antorcha', 'Antorcha', 1, 5, duracion=2000)
    assert efectos.encender_antorcha(r, antorcha)
    assert efectos.encender_antorcha(r, antorcha) is False


def test_antorcha_revertida_por_historial():
    h, r, j = sistema()
    antorcha = Antorcha('i-1', 'itm_antorcha', 'Antorcha', 1, 5, duracion=500)
    h.iniciar_accion(r)
    efectos.encender_antorcha(r, antorcha)
    h.confirmar_accion()

    assert h.revertir()
    assert antorcha.encendida is False
    assert antorcha.evento_apagado is None


# ---------------------------------------------------------------------------
# Regeneración
# ---------------------------------------------------------------------------

def test_regeneracion_cura_cada_200_hasta_el_tope_de_vida_max():
    h, r, _ = sistema()
    e = rata()
    e.regeneracion = 5
    e.recibir_dano(10)  # vida 2
    r.vincular_actor(e)

    assert efectos.iniciar_regeneracion(r, e)
    r.avanzar_y_ejecutar(200)
    assert e.vida == 7
    r.avanzar_y_ejecutar(400)
    assert e.vida == 12  # tope vida_max alcanzado, no sigue antes de él
    r.avanzar_y_ejecutar(600)
    assert e.vida == 12  # nunca supera vida_max aunque siga pulsando


def test_regeneracion_sin_campo_no_programa_nada():
    h, r, _ = sistema()
    e = rata()
    assert e.regeneracion == 0
    assert efectos.iniciar_regeneracion(r, e) is False
    assert e.evento_regeneracion is None


def test_regeneracion_se_cancela_sola_al_morir_el_enemigo():
    h, r, _ = sistema()
    e = rata()
    e.regeneracion = 5
    r.vincular_actor(e)
    efectos.iniciar_regeneracion(r, e)
    e.recibir_dano(12)
    assert e.vivo is False
    r.avanzar_y_ejecutar(1000)
    assert e.vida == 0


def test_regeneracion_revertida_por_historial():
    h, r, _ = sistema()
    e = rata()
    e.regeneracion = 5
    e.recibir_dano(8)  # vida 4
    r.vincular_actor(e)

    h.iniciar_accion(r)
    efectos.iniciar_regeneracion(r, e)
    r.avanzar_y_ejecutar(200)
    assert e.vida == 9
    h.confirmar_accion()

    assert h.revertir()
    assert e.vida == 4