import pytest

from adaptadores.datos_offline import DatosOffline
from bench.bench_precarga import FuenteConGuardia, FuenteGrilla
from controlador.controlador_red import ControladorRed, cargar_esqueleto_completo
from controlador.inicio_partida import nueva_partida
from tests.test_controlador_red import FuenteContada


@pytest.mark.parametrize('listar', [False, True])
def test_recorrido_completo_cabe_en_presupuesto_frio_y_caliente(tmp_path, listar):
    cuentas = []
    for _ in range(2):
        fuente = FuenteConGuardia(DatosOffline())
        if listar:
            fuente.listar_criptas()
        sesion = nueva_partida(fuente, 'cripta-01', tmp_path, semilla=42)
        try:
            for sala_id in (2, 3, 4, 6):
                assert sesion.red.asegurar_entrada(sala_id) is None
                sesion.red.planificar_precarga(sesion.partida.cripta.sala_por_id(sala_id))
                sesion.red.procesar_cola()
            assert fuente.solicitudes <= sesion.partida.cripta.presupuesto_solicitudes
            cuentas.append(fuente.solicitudes)
        finally:
            sesion.red.cerrar()
    assert cuentas[1] < cuentas[0]


def test_lote_lleno_no_repite_salas_y_respeta_diez(tmp_path):
    fuente = FuenteContada(FuenteGrilla(5))
    cripta = cargar_esqueleto_completo(fuente, 'grilla')
    red = ControladorRed(fuente, cripta, tmp_path, completar_lotes=True)
    try:
        for sala_id in range(1, 26):
            red.planificar_precarga(cripta.sala_por_id(sala_id))
            red.garantizar_contenido(sala_id)
            red.procesar_cola()
        ids = fuente.salas_pedidas()
        assert len(ids) == len(set(ids)) == 25
        assert all(1 <= len(lote) <= 10 for lote in fuente.contenido)
        assert len(fuente.contenido[0]) == 10
        assert all(red.contenido_cargado(i) for i in range(1, 26))
    finally:
        red.cerrar()
