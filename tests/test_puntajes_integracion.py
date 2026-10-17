import io
import json
import sys
from pathlib import Path
import pytest
import main as juego
from vista.vista_consola import VistaConsola
from adaptadores.datos_offline import DatosOffline
from tests.test_controlador_juego import RUTA_VICTORIA

def args(tmp_path):
    return ['--offline','--cripta','cripta-01','--partidas-dir',str(tmp_path),
            '--cache-dir',str(tmp_path/'cache'),'--reportes',str(tmp_path/'red.txt')]

def datos(tmp_path):
    return json.loads((tmp_path/'puntajes.json').read_text(encoding='utf-8'))['puntajes']

def test_q_y_replay_no_duplica(tmp_path,monkeypatch):
    monkeypatch.setattr('sys.stdin',io.StringIO('José\nW\nQ\n'))
    assert juego.main(args(tmp_path))==0
    assert len(datos(tmp_path))==1 and datos(tmp_path)[0]['nombre']=='José'
    assert datos(tmp_path)[0]['resultado']=='en_curso'
    antes=(tmp_path/'puntajes.json').read_bytes()
    log=next((tmp_path/'bitacoras').glob('*.log'))
    assert juego.main(args(tmp_path)+['--replay',str(log),'--silencioso'])==0
    assert (tmp_path/'puntajes.json').read_bytes()==antes

def test_carga_registra_estado_vigente(tmp_path,monkeypatch):
    monkeypatch.setattr('sys.stdin',io.StringIO('Ana\nG\nW\nL\nW\nW\nQ\n'))
    assert juego.main(args(tmp_path))==0
    assert len(datos(tmp_path))==1
    assert datos(tmp_path)[0]['tiempo_final']==200
    assert datos(tmp_path)[0]['acciones_jugador']==2

def test_archivo_roto_conservado(tmp_path,monkeypatch,capsys):
    p=tmp_path/'puntajes.json';p.write_text('roto',encoding='utf-8')
    monkeypatch.setattr('sys.stdin',io.StringIO('Ana\nQ\n'))
    assert juego.main(args(tmp_path))==1
    assert p.read_text()=='roto'
    assert 'No se pudo guardar el puntaje' in capsys.readouterr().out

def test_eof_nombre_anonimo(tmp_path,monkeypatch):
    monkeypatch.setattr('sys.stdin',io.StringIO(''))
    assert juego.main(args(tmp_path))==0
    assert datos(tmp_path)[0]['nombre']=='Jugador'

def test_derrota(tmp_path,monkeypatch):
    monkeypatch.setattr('sys.stdin',io.StringIO('Ana\nN\nW\nW\nW\nW\nW\n'))
    assert juego.main(args(tmp_path))==0
    assert datos(tmp_path)[0]['resultado']=='derrota'

def test_victoria(tmp_path,monkeypatch):
    class Resistente(DatosOffline):
        def datos_cripta(self,id):
            d=super().datos_cripta(id);d['jugador']['vida_max']=300;return d
    monkeypatch.setattr(juego,'crear_fuente',lambda _:Resistente())
    monkeypatch.setattr('controlador.semilla.generar_semilla',lambda:3)
    monkeypatch.setattr('sys.stdin',io.StringIO('Ana\n'+'\n'.join(RUTA_VICTORIA)+'\n'))
    assert juego.main(args(tmp_path))==0
    assert datos(tmp_path)[0]['resultado']=='victoria'

def test_bench_no_registra(tmp_path,monkeypatch):
    import bench.runner
    monkeypatch.setattr(bench.runner,'main_bench',lambda:[])
    assert juego.main(args(tmp_path)+['--bench'])==0
    assert not (tmp_path/'puntajes.json').exists()

def test_fallo_escritura_controlado(tmp_path,monkeypatch,capsys):
    import utilidades.puntajes as puntos
    def falla(*args):raise OSError('Disco lleno')
    monkeypatch.setattr(puntos,'registrar_puntaje',falla)
    monkeypatch.setattr('sys.stdin',io.StringIO('Ana\nQ\n'))
    assert juego.main(args(tmp_path))==1
    assert 'Disco lleno' in capsys.readouterr().out
