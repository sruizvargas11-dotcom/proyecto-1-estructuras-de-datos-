import json

import pytest

from adaptadores.datos_offline import DatosOffline
from controlador.controlador_red import ControladorRed, cargar_esqueleto_completo
from modelo.entidades.enemigo import Enemigo
from modelo.entidades.objetos.arma import Arma
from modelo.entidades.trampa import Trampa


class FuenteContada:
    """Envuelve una fuente y cuenta cada llamada que sería un request."""

    def __init__(self, fuente):
        self._fuente = fuente
        self.contenido = []      # lotes de sala_ids pedidos
        self.lotes_catalogo = []  # lotes de tipo_ids pedidos
        self.versiones_catalogo = 0
        self.fallar_contenido = False

    def datos_cripta(self, cripta_id):
        return self._fuente.datos_cripta(cripta_id)

    def esqueleto_cripta(self, cripta_id, pagina):
        return self._fuente.esqueleto_cripta(cripta_id, pagina)

    def version_cripta(self, cripta_id):
        return self._fuente.version_cripta(cripta_id)

    def contenido_salas(self, cripta_id, sala_ids):
        assert 1 <= len(sala_ids) <= 10
        if self.fallar_contenido:
            raise RuntimeError("Presupuesto de solicitudes agotado.")
        self.contenido.append(list(sala_ids))
        return self._fuente.contenido_salas(cripta_id, sala_ids)

    def catalogo(self, tipo_ids):
        assert 1 <= len(tipo_ids) <= 10
        self.lotes_catalogo.append(list(tipo_ids))
        return self._fuente.catalogo(tipo_ids)

    def version_catalogo(self):
        self.versiones_catalogo += 1
        return self._fuente.version_catalogo()

    def salas_pedidas(self):
        return [s for lote in self.contenido for s in lote]

    def tipos_pedidos(self):
        return [t for lote in self.lotes_catalogo for t in lote]


class FuenteGrilla:
    """Cripta sintética de lado x lado salas; cada sala trae un enemigo de tipo propio."""

    def __init__(self, lado):
        self.lado = lado

    def _id(self, fila, col):
        return fila * self.lado + col + 1

    def datos_cripta(self, cripta_id):
        total = self.lado * self.lado
        return {'id': cripta_id, 'version': 'g1', 'salas_total': total, 'paginas': 1,
                'sala_inicial': 1, 'sala_salida': total, 'llave_salida': None,
                'presupuesto_solicitudes': 100, 'inventario_max': 10}

    def esqueleto_cripta(self, cripta_id, pagina):
        salas = []
        for f in range(self.lado):
            for c in range(self.lado):
                salidas = {}
                if f > 0:
                    salidas['N'] = {'sala': self._id(f - 1, c)}
                if f < self.lado - 1:
                    salidas['S'] = {'sala': self._id(f + 1, c)}
                if c < self.lado - 1:
                    salidas['E'] = {'sala': self._id(f, c + 1)}
                if c > 0:
                    salidas['O'] = {'sala': self._id(f, c - 1)}
                salas.append({'id': self._id(f, c), 'nombre': f'S{self._id(f, c)}',
                              'salidas': salidas})
        return {'pagina': 1, 'total_paginas': 1, 'salas': salas}

    def version_cripta(self, cripta_id):
        return {'id': cripta_id, 'version': 'g1'}

    def contenido_salas(self, cripta_id, sala_ids):
        return {'contenido': [
            {'sala': s, 'enemigos': [{'instancia': f'e-{s}', 'tipo': f'ent_{s}'}],
             'objetos': [], 'trampas': []}
            for s in sala_ids]}

    def catalogo(self, tipo_ids):
        return {'entidades': [
            {'id': t, 'clase': 'enemigo', 'nombre': t, 'vida_max': 5, 'ataque': 1,
             'defensa': 0, 'velocidad': 100, 'comportamiento': 'errante'}
            for t in tipo_ids]}

    def version_catalogo(self):
        return {'version': 'c1'}


@pytest.fixture
def offline():
    fuente = FuenteContada(DatosOffline())
    cripta = cargar_esqueleto_completo(fuente, 'cripta-01')
    return fuente, cripta


def _ids(lista_simple):
    return [x.instancia_id for x in lista_simple.recorrer_valores()]


def test_precarga_encola_vecinas_y_vecinas_de_vecinas(offline, tmp_path):
    fuente, cripta = offline
    red = ControladorRed(fuente, cripta, tmp_path)
    red.garantizar_contenido(1)
    fuente.contenido.clear()

    # Sala 1 -> 2 (directa) -> 3 y 5 (vecinas de vecinas). No vuelve a la 1.
    assert red.planificar_precarga(cripta.sala_por_id(1)) == 3
    assert red.procesar_cola() == 3
    assert fuente.contenido == [[2, 3, 5]]


def test_sala_vecina_lista_antes_de_que_el_jugador_decida(offline, tmp_path):
    fuente, cripta = offline
    red = ControladorRed(fuente, cripta, tmp_path)
    red.garantizar_contenido(1)
    red.planificar_precarga(cripta.sala_por_id(1))
    red.procesar_cola()
    pedidas = len(fuente.contenido)

    # El jugador decide ir a la sala 2: ya está cargada, no hay espera ni request.
    sala = red.garantizar_contenido(2)
    assert red.contenido_cargado(2)
    assert len(fuente.contenido) == pedidas
    assert len(sala.enemigos_dormidos) == 2


def test_misma_sala_no_se_solicita_dos_veces(offline, tmp_path):
    fuente, cripta = offline
    red = ControladorRed(fuente, cripta, tmp_path)
    red.garantizar_contenido(1)
    for _ in range(3):
        red.planificar_precarga(cripta.sala_por_id(1))
        red.planificar_precarga(cripta.sala_por_id(2))
        red.procesar_cola()
    for sala_id in range(1, 7):
        red.garantizar_contenido(sala_id)

    pedidas = fuente.salas_pedidas()
    assert sorted(pedidas) == [1, 2, 3, 4, 5, 6]


def test_procesar_cola_envia_un_lote_de_maximo_diez(tmp_path):
    fuente = FuenteContada(FuenteGrilla(5))
    cripta = cargar_esqueleto_completo(fuente, 'grilla')
    red = ControladorRed(fuente, cripta, tmp_path, version_catalogo={'version': 'c1'})
    centro = cripta.sala_por_id(13)          # 4 directas + 8 a distancia 2

    assert red.planificar_precarga(centro) == 12
    assert red.procesar_cola() == 10
    assert red.procesar_cola() == 2
    assert red.procesar_cola() == 0
    assert [len(l) for l in fuente.contenido] == [10, 2]
    # Las vecinas directas van en el primer lote.
    assert set([8, 12, 14, 18]) <= set(fuente.contenido[0])


def test_garantizar_aprovecha_el_lote_con_pendientes(tmp_path):
    fuente = FuenteContada(FuenteGrilla(5))
    cripta = cargar_esqueleto_completo(fuente, 'grilla')
    red = ControladorRed(fuente, cripta, tmp_path, version_catalogo={'version': 'c1'})
    red.planificar_precarga(cripta.sala_por_id(13))

    red.garantizar_contenido(25)             # no estaba en la cola
    assert fuente.contenido[0][0] == 25
    assert len(fuente.contenido[0]) == 10    # 25 + 9 pendientes de la cola
    assert red.pendientes() == 3


def test_poblar_entidades_sin_activar_enemigos(offline, tmp_path):
    fuente, cripta = offline
    red = ControladorRed(fuente, cripta, tmp_path)
    sala = red.garantizar_contenido(2)

    assert _ids(sala.enemigos_dormidos) == ['e-201', 'e-202']
    assert len(sala.enemigos_activos) == 0
    rata = next(sala.enemigos_dormidos.recorrer_valores())
    assert isinstance(rata, Enemigo) and rata.vida == 12 and rata.sala_actual is sala
    objeto = next(sala.objetos_suelo.recorrer_valores())
    assert isinstance(objeto, Arma) and objeto.tipo_id == 'itm_daga_oxidada'
    trampa = next(sala.trampas.recorrer_valores())
    assert isinstance(trampa, Trampa) and trampa.instancia_id == 't-17'


def test_tipos_nuevos_se_resuelven_una_vez_y_en_lotes(offline, tmp_path):
    fuente, cripta = offline
    red = ControladorRed(fuente, cripta, tmp_path)
    red.solicitar_contenido_lote([1, 2, 3, 4, 5, 6])

    tipos = fuente.tipos_pedidos()
    assert len(tipos) == len(set(tipos)) == 11
    assert [len(l) for l in fuente.lotes_catalogo] == [10, 1]
    assert list(red.tipos_descubiertos())[:3] == ['itm_antorcha', 'ent_rata_gigante',
                                                  'itm_daga_oxidada']
    assert len(fuente.contenido) == 1 and fuente.versiones_catalogo == 1


def test_lote_rechaza_mas_de_diez_salas(tmp_path):
    fuente = FuenteContada(FuenteGrilla(4))
    cripta = cargar_esqueleto_completo(fuente, 'grilla')
    red = ControladorRed(fuente, cripta, tmp_path)
    with pytest.raises(ValueError):
        red.solicitar_contenido_lote(list(range(1, 12)))
    assert fuente.contenido == []


def test_contenido_y_fichas_vigentes_en_disco_no_generan_request(offline, tmp_path):
    fuente, cripta = offline

    (tmp_path / 'cripta-01').mkdir()
    (tmp_path / 'cripta-01' / 'version.json').write_text(
        json.dumps({'version': cripta.version}), encoding='utf-8')
    version_cat = DatosOffline().version_catalogo()
    (tmp_path / 'catalogo_version.json').write_text(json.dumps(version_cat), encoding='utf-8')

    ControladorRed(fuente, cripta, tmp_path, version_catalogo=version_cat
                   ).solicitar_contenido_lote([1, 2, 3, 4, 5, 6])
    antes = (len(fuente.contenido), len(fuente.lotes_catalogo))

    otra = cargar_esqueleto_completo(fuente, 'cripta-01')
    red = ControladorRed(fuente, otra, tmp_path, version_catalogo=version_cat)
    red.solicitar_contenido_lote([1, 2, 3, 4, 5, 6])
    assert (len(fuente.contenido), len(fuente.lotes_catalogo)) == antes
    assert red.contador_salas_desde_disco == 6
    assert red.contador_fichas_desde_disco == 11


def test_precarga_fallida_no_cae_el_juego(offline, tmp_path):
    fuente, cripta = offline
    red = ControladorRed(fuente, cripta, tmp_path)
    red.garantizar_contenido(1)
    red.planificar_precarga(cripta.sala_por_id(1))

    fuente.fallar_contenido = True
    assert red.procesar_cola() == 0
    assert 'Presupuesto' in red.ultimo_error
    assert not red.contenido_cargado(2)


def test_garantizar_informa_el_fallo_sin_cargar_a_medias(offline, tmp_path):
    fuente, cripta = offline
    fuente.fallar_contenido = True
    red = ControladorRed(fuente, cripta, tmp_path)
    with pytest.raises(RuntimeError):
        red.garantizar_contenido(1)
    assert not red.contenido_cargado(1)

    # se reintenta cuando hay presupuesto
    fuente.fallar_contenido = False
    assert len(red.garantizar_contenido(1).objetos_suelo) == 1
