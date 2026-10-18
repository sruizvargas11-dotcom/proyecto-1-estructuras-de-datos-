"""F4B-02: el retroceso restaura las referencias de enemigos revividos."""
import json
from unittest.mock import patch

from adaptadores.datos_offline import DatosOffline
from controlador.controlador_juego import ControladorJuego
from controlador.inicio_partida import nueva_partida
from herramientas.generar_cripta_prueba import generar
from tests.test_controlador_juego import VistaGuion, _dar_pergamino


def test_matar_revivir_y_matar_ambos_conserva_referencias(tmp_path):
    datos = generar(tmp_path / 'datos')
    sesion = nueva_partida(DatosOffline(str(datos)), 'cripta-prueba',
                           str(tmp_path / 'cache'), semilla=72)
    muestras = []

    class VistaReferencias(VistaGuion):
        def leer_comando(self):
            comando = super().leer_comando()
            sala = sesion.partida.cripta.sala_por_id(2)
            vivos = sum(e.vivo for lista in (sala.enemigos_activos,
                                             sala.enemigos_dormidos) for e in lista)
            entrada = sesion.red._fichas._nodo('ent_rata_gigante').valor
            muestras.append((comando, vivos, entrada.en_uso))
            return comando

    vista = VistaReferencias(['R 5', 'N', 'A', 'P', 'A', 'A', 'W', 'Q'])
    controlador = ControladorJuego(sesion, vista)
    assert controlador.jugar() == 'en_curso'
    assert muestras == [('R 5', 2, 2), ('N', 2, 2), ('A', 2, 2),
                        ('P', 1, 1), ('A', 2, 2), ('A', 1, 1),
                        ('W', 0, 0), ('Q', 0, 0)]
    assert sesion.partida.enemigos_derrotados == 2
    assert vista.textos('el tiempo retrocede')


def _agregar_pergaminos(datos, cantidad):
    ruta = datos / 'cripta-prueba' / 'contenido' / 'sala_1.json'
    contenido = json.loads(ruta.read_text(encoding='utf-8'))
    contenido['objetos'].extend(['itm_pergamino_retroceso'] * cantidad)
    ruta.write_text(json.dumps(contenido), encoding='utf-8')


def test_varios_retrocesos_no_duplican_referencias_ni_descargas(tmp_path):
    datos = generar(tmp_path / 'datos')
    _agregar_pergaminos(datos, 2)
    sesion = nueva_partida(DatosOffline(str(datos)), 'cripta-prueba',
                           str(tmp_path / 'cache'), semilla=72)
    ficha_original = sesion.red.ficha('ent_rata_gigante')
    tipos_originales = [n.valor.id_ficha
                        for n in sesion.red._fichas._lista.recorrer_desde_frente()]
    reversiones = []

    class VistaReferencias(VistaGuion):
        def leer_comando(self):
            sala = sesion.partida.cripta.sala_por_id(2)
            vivos = sum(e.vivo for lista in (sala.enemigos_activos,
                                             sala.enemigos_dormidos) for e in lista)
            entrada = sesion.red._fichas._nodo('ent_rata_gigante').valor
            assert entrada.en_uso == vivos
            assert entrada.ficha is ficha_original
            if self._comandos and self._comandos[0] == 'P':
                reversiones.append(vivos)
            return super().leer_comando()

    comandos = ['R 5', 'R 7', 'R 7', 'N', 'A', 'P', 'W', 'P',
                'A', 'P', 'A', 'A', 'W', 'Q']
    vista = VistaReferencias(comandos)
    with patch.object(sesion.fuente, 'catalogo', wraps=sesion.fuente.catalogo) as catalogo:
        ControladorJuego(sesion, vista).jugar()
    assert reversiones == [1, 2, 1]
    assert catalogo.call_count == 0
    assert sesion.partida.enemigos_derrotados == 2
    assert sesion.red._fichas._nodo('ent_guardian_oseo').valor.en_uso == 1
    assert all(sesion.red._fichas._nodo(tipo) is not None for tipo in tipos_originales)


def test_revivir_recupera_ficha_desalojada_desde_disco(tmp_path):
    datos = generar(tmp_path / 'datos')
    _agregar_pergaminos(datos, 1)
    tipos = []
    for i in range(30):
        tipo = f'qa_presion_{i}'
        tipos.append(tipo)
        ficha = {'id': tipo, 'nombre': tipo, 'clase': 'arma',
                 'peso': 1, 'valor': 1, 'ataque_bonus': 1}
        (datos / 'catalogo' / (tipo + '.json')).write_text(
            json.dumps(ficha), encoding='utf-8')
    fuente = DatosOffline(str(datos))
    sesion = nueva_partida(fuente, 'cripta-prueba', str(tmp_path / 'cache'),
                           semilla=72)
    tras_desalojo = []

    class VistaPresion(VistaGuion):
        def leer_comando(self):
            comando = super().leer_comando()
            if comando == 'P':
                assert sesion.red._fichas._nodo('ent_rata_gigante').valor.en_uso == 0
                sesion.red.resolver_catalogo(tipos)
                assert sesion.red.ficha('ent_rata_gigante') is None
                tras_desalojo.append((catalogo.call_count,
                                      sesion.red.contador_fichas_desde_disco))
            elif tras_desalojo and comando == 'A':
                assert catalogo.call_count == tras_desalojo[0][0]
                assert sesion.red.contador_fichas_desde_disco == tras_desalojo[0][1] + 1
                assert sesion.red._fichas._nodo('ent_rata_gigante').valor.en_uso == 1
            return comando

    vista = VistaPresion(['R 5', 'R 7', 'N', 'A', 'A', 'P', 'A', 'W', 'Q'])
    with patch.object(fuente, 'catalogo', wraps=fuente.catalogo) as catalogo:
        ControladorJuego(sesion, vista).jugar()
    assert tras_desalojo
    assert sesion.partida.enemigos_derrotados == 2
    assert sesion.red._fichas._nodo('ent_rata_gigante').valor.en_uso == 0


def test_pergamino_tras_derrota_explica_que_la_partida_termino(tmp_path):
    datos = generar(tmp_path / 'datos')
    sesion = nueva_partida(DatosOffline(str(datos)), 'cripta-prueba',
                           str(tmp_path / 'cache'), semilla=72)
    vista = VistaGuion(['W', 'Q'])
    c = ControladorJuego(sesion, vista)
    c.jugar()
    _dar_pergamino(sesion)
    c.jugador.recibir_dano(c.jugador.vida)
    c.partida.verificar_fin()
    antes = (c.partida.tiempo, c.partida.acciones_jugador,
             len(c.historial), len(c.jugador.inventario))
    assert not c._usar_pergamino()
    assert vista.textos('No puedes usar un pergamino: la partida terminó.')
    assert antes == (c.partida.tiempo, c.partida.acciones_jugador,
                     len(c.historial), len(c.jugador.inventario))
