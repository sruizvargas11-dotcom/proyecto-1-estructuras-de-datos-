import builtins
import json
from pathlib import Path

import pytest

from adaptadores.datos_offline import DatosOffline
from controlador.controlador_juego import ControladorJuego
from controlador.guardado import guardar, cargar
from controlador.inicio_partida import nueva_partida
from controlador.reproduccion import reproducir
from herramientas.generar_cripta_prueba import generar
from modelo import efectos
from persistencia.PartidaBinaria import PartidaBinaria, ErrorFormatoBinario
from tests.test_controlador_juego import VistaGuion, _dar_objeto
from vista.vista_consola import VistaConsola


def sesion(tmp_path):
    carpeta = generar(tmp_path / 'datos')
    return nueva_partida(DatosOffline(str(carpeta)), 'cripta-prueba',
                        str(tmp_path / 'cache'), semilla=72,
                        ruta_bitacora=str(tmp_path / 'inicio.log'))


def punto_decision(s):
    s.partida.reloj.avanzar_hasta_turno(s.partida.jugador)
    if s.partida.historial.registrando:
        s.partida.historial.confirmar_accion()


def firma(p):
    j = p.jugador
    return (p.tiempo, j.vida, j.velocidad, j.ataque, j.defensa, j.sala_actual.id,
            p.acciones_jugador, p.enemigos_derrotados, p.estado,
            tuple((n.valor.instancia_id, n.valor.nombre) for n in j.inventario.recorrer_desde_frente()),
            p.reloj.azar.getstate(), p.reloj.agenda.siguiente_secuencia,
            tuple(sorted((e.tiempo, e.secuencia, e.dato.tipo,
                          getattr(e.dato.dueno, 'instancia_id', None))
                         for e in p.reloj.agenda._datos if e.valido)), len(p.historial))


def test_roundtrip_conserva_referencias_historial_azar_y_continuacion(tmp_path):
    s = sesion(tmp_path)
    c = ControladorJuego(s, VistaGuion(['R', 'R', 'EQ 2', 'U 2', 'N']))
    while s.partida.acciones_jugador < 5:
        c.ciclo()
    punto_decision(s)
    ruta = str(tmp_path / 'partida.sav')
    antes = firma(s.partida)
    guardar(s, ruta, c._protegidas)
    copia = cargar(ruta, s)
    assert firma(copia.partida) == antes
    assert copia.partida.jugador._reloj is copia.partida.reloj
    assert copia.partida.rastro.historial is copia.partida.historial
    assert copia.partida.jugador.sala_actual is copia.partida.cripta.sala_por_id(2)
    assert dict(copia.partida.encabezado()) == dict(s.partida.encabezado())
    assert PartidaBinaria(ruta).cargar_global()['semilla'] == 72
    sala = PartidaBinaria(ruta).cargar_sala_binaria(2)
    assert sala['id'] == 2 and sala['registros']
    assert len(sala['estado']['enemigos_activos']) == 2
    assert sala['estado']['enemigos_activos'][0]['vida'] > 0
    for actual in (s, copia):
        ControladorJuego(actual, VistaGuion(['A', 'W', 'Q'])).jugar()
    assert firma(s.partida) == firma(copia.partida)
    for actual in (s, copia):
        assert actual.partida.historial.revertir()
    assert firma(s.partida) == firma(copia.partida)


def test_guardar_cargar_desde_comandos_y_replay_de_carga(tmp_path):
    s = sesion(tmp_path)
    ruta = str(tmp_path / 'con espacios.sav')
    vista = VistaGuion(['R', 'U', f'G {ruta}', 'W', f'L {ruta}', 'W', 'Q'])
    c = ControladorJuego(s, vista)
    c.jugar()
    assert vista.textos('Partida guardada') and vista.textos('Partida cargada')
    assert c.partida.tiempo == 175
    assert Path(s.bitacora.ruta).is_file()
    assert c.bitacora.ruta != s.bitacora.ruta
    reproducida = reproducir(c.sesion.fuente, c.bitacora.ruta, str(tmp_path / 'replay-cache'))
    assert firma(reproducida) == firma(c.partida)


@pytest.mark.parametrize('tipo', ['veneno', 'velocidad', 'antorcha', 'regeneracion'])
def test_eventos_reconstruidos_ejecutan_igual(tmp_path, tipo):
    s = sesion(tmp_path)
    p, j = s.partida, s.partida.jugador
    if tipo == 'veneno':
        efectos.aplicar_veneno(p.reloj, j, 2)
    elif tipo == 'velocidad':
        efectos.aplicar_modificador_velocidad(p.reloj, j, 20, 150)
        # Al cambiar velocidad con turno pendiente t=0 pasa a t=1.
        p.reloj.tiempo_actual = j.evento_actual.tiempo
    elif tipo == 'antorcha':
        antorcha = _dar_objeto(s, 'itm_antorcha')
        p.usar_objeto(j.buscar_nodo(antorcha.instancia_id))
    else:
        p.activar_enemigos(p.cripta.sala_por_id(2))
        e = next(iter(p.cripta.sala_por_id(2).enemigos_activos))
        e.regeneracion = 2
        e.vida = 3
        efectos.iniciar_regeneracion(p.reloj, e)
    ruta = str(tmp_path / 'efecto.sav')
    guardar(s, ruta)
    copia = cargar(ruta, s)
    for actual in (s, copia):
        ControladorJuego(actual, VistaGuion(['W'] * 5 + ['Q'])).jugar()
    assert firma(s.partida) == firma(copia.partida)


@pytest.mark.parametrize('recorte', [0, 1, 4, 11, 20, -1])
def test_truncados_no_reemplazan_partida(tmp_path, recorte):
    s = sesion(tmp_path)
    ruta = tmp_path / 'roto.sav'
    guardar(s, str(ruta))
    datos = ruta.read_bytes()
    ruta.write_bytes(datos[:recorte])
    antes = firma(s.partida)
    with pytest.raises((ValueError, ErrorFormatoBinario)):
        cargar(str(ruta), s)
    assert firma(s.partida) == antes


def test_nombre_jugador_persiste_y_guardado_antiguo_es_incompatible(tmp_path):
    """§8.2 + §4.10: nombre_jugador se guarda y se recupera; un guardado con el
    esquema anterior (sin ese campo) da un error claro, no una carga a medias."""
    s = sesion(tmp_path)
    s.nombre_jugador = 'Ada'
    ruta = str(tmp_path / 'con_nombre.sav')
    guardar(s, ruta)
    copia = cargar(ruta, s)
    assert copia.nombre_jugador == 'Ada'

    # Simula un guardado de la versión anterior del programa: mismo contenido,
    # pero con el esquema viejo y sin 'nombre_jugador'.
    g, salas = PartidaBinaria(ruta).cargar_todo()
    g['esquema_estado'] = 1
    del g['nombre_jugador']
    PartidaBinaria(ruta).guardar(g, salas)

    antes = firma(s.partida)
    with pytest.raises(ValueError, match='[Ee]squema'):
        cargar(ruta, s)
    assert firma(s.partida) == antes   # la sesión en curso no se tocó


def test_guardado_fallido_conserva_archivo_previo(tmp_path, monkeypatch):
    s = sesion(tmp_path)
    ruta = tmp_path / 'bueno.sav'
    guardar(s, str(ruta))
    antes = ruta.read_bytes()
    def falla(*args):
        raise OSError('Disco lleno')
    monkeypatch.setattr(PartidaBinaria, 'guardar', falla)
    with pytest.raises(OSError):
        guardar(s, str(ruta))
    assert ruta.read_bytes() == antes


def test_pergamino_tras_carga_restaura_turno_sin_duplicados(tmp_path):
    s = sesion(tmp_path)
    c = ControladorJuego(s, VistaGuion(['R'] * 5 + ['W']))
    while s.partida.acciones_jugador < 6:
        c.ciclo()
    punto_decision(s)
    guardar(s, str(tmp_path / 'p.sav'))
    copia = cargar(str(tmp_path / 'p.sav'), s)
    v = VistaGuion(['P', 'W', 'Q'])
    ControladorJuego(copia, v).jugar()
    assert v.textos('el tiempo retrocede')
    activos = [e for e in copia.partida.reloj.agenda._datos
               if e.valido and e.dato.dueno is copia.partida.jugador and e.dato.tipo == 'accion']
    assert len(activos) == 1
    assert all(n.valor.clase != 'pergamino_retroceso'
               for n in copia.partida.jugador.inventario.recorrer_desde_frente())


def test_replay_sin_vista_ni_input_y_version_incompatible(tmp_path, monkeypatch):
    s = sesion(tmp_path)
    ControladorJuego(s, VistaGuion(['R', 'U', 'W', 'Q'])).jugar()
    def prohibido(*args, **kwargs):
        raise AssertionError('No debe instanciarse vista ni leer input')
    monkeypatch.setattr(VistaConsola, '__init__', prohibido)
    monkeypatch.setattr(builtins, 'input', prohibido)
    assert firma(reproducir(s.fuente, s.bitacora.ruta, str(tmp_path/'replay'))) == firma(s.partida)
    ruta = Path(s.bitacora.ruta)
    ruta.write_text(ruta.read_text(encoding='utf-8').replace('laboratorio-consola-v1', 'incompatible'), encoding='utf-8')
    with pytest.raises(ValueError, match='reproducción fiel'):
        reproducir(s.fuente, str(ruta), str(tmp_path/'replay'))


def test_mensajes_efectos_y_orden_real_en_vista(tmp_path):
    s = sesion(tmp_path)
    salida = []
    comandos = iter(['R', 'R', 'U 1', 'I nombre', 'Q'])
    v = VistaConsola(leer=lambda _: next(comandos), escribir=salida.append)
    ControladorJuego(s, v).jugar()
    texto = '\n'.join(salida)
    assert 'Antorcha encendida hasta' in texto and 'Usas Antorcha.' in texto
    for i in range(30):
        v.agregar_mensaje(i, str(i))
    assert len(v.mensajes()) == 20 and v.mensajes()[0] == '[t=10] 10'
    assert len(v._mensajes._datos) == 20


def test_antidoto_consumido_y_muerte_por_veneno_termina(tmp_path):
    s = sesion(tmp_path)
    antidoto = _dar_objeto(s, 'itm_antidoto')
    p = s.partida
    efectos.aplicar_veneno(p.reloj, p.jugador, 2)
    assert p.usar_objeto(p.jugador.buscar_nodo(antidoto.instancia_id))
    assert p.jugador.buscar_nodo(antidoto.instancia_id) is None
    efectos.aplicar_veneno(p.reloj, p.jugador, 300)
    vista = VistaGuion(['W'])
    assert ControladorJuego(s, vista).jugar() == 'derrota'


def test_modificador_repetido_rechazado_sin_crash(tmp_path):
    s = sesion(tmp_path)
    p = s.partida
    pocion = _dar_objeto(s, 'itm_velocidad_prueba')
    efectos.aplicar_modificador_velocidad(p.reloj, p.jugador, 10, 500)
    v = VistaGuion(['U', 'Q'])
    ControladorJuego(s, v).jugar()
    assert v.textos('Ya hay un modificador')
    assert p.jugador.buscar_nodo(pocion.instancia_id) is not None


@pytest.mark.parametrize('texto', ['N basura', 'W 1', 'A 1 2', 'IC x', 'A ' + '9' * 5000])
def test_argumentos_invalidos_no_crashean(texto):
    from controlador.controlador_juego import interpretar
    comando, error = interpretar(texto)
    assert comando is None and error


def test_recorrer_ordenar_no_reordena_y_numero_sigue_siendo_real(tmp_path):
    s = sesion(tmp_path)
    salida = []
    comandos = iter(['R', 'R', 'I nombre', 'IS', 'IC', 'IA', 'IC', 'Q'])
    v = VistaConsola(leer=lambda _: next(comandos), escribir=salida.append)
    ControladorJuego(s, v).jugar()
    assert [n.valor.nombre for n in s.partida.jugador.inventario.recorrer_desde_frente()] == ['Antorcha', 'Daga oxidada']
    assert s.partida.tiempo == 50
    assert sum('Selección: Daga' in x for x in salida) == 2
    assert sum('Selección: Antorcha' in x for x in salida) == 2


def test_fin_muestra_ultimo_golpe_antes_de_derrota(tmp_path):
    s = sesion(tmp_path)
    s.partida.jugador.vida = 5
    salida = []
    comandos = iter(['N', 'W'])
    v = VistaConsola(leer=lambda _: next(comandos), escribir=salida.append)
    ControladorJuego(s, v).jugar()
    i = next(i for i, x in enumerate(salida) if x.startswith('Derrota:'))
    assert any('Has muerto.' in x for x in salida[:i])


@pytest.mark.parametrize('alteracion', ['tipo', 'referencia', 'ciclo', 'version'])
def test_estado_invalido_no_se_instala(tmp_path, alteracion):
    s = sesion(tmp_path)
    ruta = str(tmp_path / 'malicioso.sav')
    guardar(s, ruta)
    g, salas = PartidaBinaria(ruta).cargar_todo()
    registros = g['registros'] + [r for _, sala in salas for r in sala['registros']]
    if alteracion == 'tipo':
        registros[0]['tipo'] = 'os.system'
    elif alteracion == 'referencia':
        g['raiz'] = {'ref': -1}
    elif alteracion == 'version':
        g['version_cripta'] = 'otra'
    else:
        nodo = next(r for r in registros if r['tipo'] == 'estructuras.lista_simple.NodoSimple')
        nodo['datos']['siguiente'] = {'ref': nodo['id']}
    PartidaBinaria(ruta).guardar(g, salas)
    antes = firma(s.partida)
    with pytest.raises(ValueError):
        cargar(ruta, s)
    assert firma(s.partida) == antes


def test_bench_no_instancia_vista(tmp_path, monkeypatch):
    import main
    import bench.runner
    def prohibido(*args, **kwargs):
        raise AssertionError('No instanciar VistaConsola')
    monkeypatch.setattr(VistaConsola, '__init__', prohibido)
    monkeypatch.setattr(bench.runner, 'main_bench', lambda: [])
    assert main.main(['--bench']) == 0
