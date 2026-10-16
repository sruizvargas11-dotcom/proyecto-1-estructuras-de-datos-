"""Pruebas de la LRU del catálogo y sus referencias activas.

Comprueban que los enemigos vivos protejan sus fichas y que estas puedan
desalojarse después de liberar todas las referencias.
"""

import pytest

from adaptadores.datos_offline import DatosOffline
from controlador.controlador_red import ControladorRed, cargar_esqueleto_completo
from estructuras.listalru import ListaLRU


@pytest.fixture
def offline():
    fuente = DatosOffline()
    cripta = cargar_esqueleto_completo(fuente, 'cripta-01')
    return fuente, cripta


def test_catalogo_es_una_listalru_real(offline, tmp_path):
    """El catálogo en memoria debe ser la estructura propia, no ArrayOrdenado
    ni dict: lo confirmamos por tipo, no solo por comportamiento."""
    fuente, cripta = offline
    red = ControladorRed(fuente, cripta, tmp_path)

    assert isinstance(red._fichas, ListaLRU)


def test_resolver_catalogo_deja_la_ficha_buscable(offline, tmp_path):
    fuente, cripta = offline
    red = ControladorRed(fuente, cripta, tmp_path)

    red.resolver_catalogo(['ent_rata_gigante'])

    ficha = red.ficha('ent_rata_gigante')
    assert ficha is not None
    assert ficha['id'] == 'ent_rata_gigante'
    assert ficha['clase'] == 'enemigo'


def test_ficha_inexistente_devuelve_none(offline, tmp_path):
    fuente, cripta = offline
    red = ControladorRed(fuente, cripta, tmp_path)

    assert red.ficha('tipo_que_no_existe') is None


def test_incorporar_sala_marca_en_uso_a_sus_enemigos(offline, tmp_path):
    """Al incorporar el contenido de una sala con enemigos, su ficha queda
    protegida (en_uso > 0) sin que nadie la marque manualmente."""
    fuente, cripta = offline
    red = ControladorRed(fuente, cripta, tmp_path)

    red.garantizar_contenido(2)  # sala_2.json trae una rata gigante

    sala = cripta.sala_por_id(2)
    enemigos = list(sala.enemigos_dormidos.recorrer_valores())
    assert len(enemigos) >= 1

    tipo_id = enemigos[0].tipo_id
    nodo = red._fichas._nodo(tipo_id)
    assert nodo is not None
    assert nodo.valor.en_uso > 0


def test_ficha_protegida_no_se_desaloja_aunque_la_cache_se_llene(offline, tmp_path):
    """sala_2 trae 3 tipos distintos (rata, daga, dardos); con capacidad 3
    los tres entran, y una cuarta ficha debe desalojar una sin uso, nunca
    la del enemigo vivo."""
    fuente, cripta = offline
    red = ControladorRed(fuente, cripta, tmp_path, cache_size=3)

    red.garantizar_contenido(2)
    sala = cripta.sala_por_id(2)
    tipo_protegido = list(sala.enemigos_dormidos.recorrer_valores())[0].tipo_id
    assert red.ficha(tipo_protegido) is not None

    # Forzamos un desalojo con un cuarto tipo que no estaba en memoria.
    red.resolver_catalogo(['itm_llave_bronce'])

    # La protegida debe seguir disponible: no se desalojó.
    assert red.ficha(tipo_protegido) is not None


def test_notificar_muerte_enemigo_libera_la_ficha_para_desalojo(offline, tmp_path):
    """Las dos ratas de la sala 2 comparten ficha (e-201 y e-202).

    La ficha solo queda libre después de notificar la muerte de ambas.
    """
    fuente, cripta = offline
    red = ControladorRed(fuente, cripta, tmp_path, cache_size=3)

    red.garantizar_contenido(2)
    sala = cripta.sala_por_id(2)
    enemigos = list(sala.enemigos_dormidos.recorrer_valores())
    tipo_id = enemigos[0].tipo_id
    assert len(enemigos) == 2 and enemigos[1].tipo_id == tipo_id

    red.notificar_muerte_enemigo(enemigos[0])
    nodo = red._fichas._nodo(tipo_id)
    assert nodo.valor.en_uso == 1  # la segunda rata la sigue protegiendo

    red.notificar_muerte_enemigo(enemigos[1])
    nodo = red._fichas._nodo(tipo_id)
    assert nodo.valor.en_uso == 0  # ya murieron las dos

    # Ahora sí debe poder desalojarse al resolver otra ficha distinta.
    red.resolver_catalogo(['itm_llave_bronce'])
    assert red.ficha(tipo_id) is None
    assert red.ficha('itm_llave_bronce') is not None