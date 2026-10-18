"""Equipo y luz reversibles, persistibles y reproducibles por comandos."""
import pytest
from adaptadores.datos_offline import DatosOffline
from controlador.inicio_partida import nueva_partida
from controlador.controlador_juego import ControladorJuego, interpretar
from controlador.controlador_replay import reproducir
from tests.test_controlador_juego import VistaGuion
from modelo import efectos
from modelo.entidades.objetos.antorcha import Antorcha
from tests.test_efectos_bloque3 import sistema


class FuenteEquipo(DatosOffline):
    def contenido_salas(self,id,salas):
        d=super().contenido_salas(id,salas)
        for sala in d['contenido']:
            if sala['sala']==1:
                sala['objetos']=['itm_antorcha','itm_daga_oxidada','itm_coraza_cuero','itm_pergamino_retroceso']
        return d


def jugar(tmp_path,comandos):
    log=str(tmp_path/'equipo.log')
    sesion=nueva_partida(FuenteEquipo(),'cripta-01',str(tmp_path/'cache'),semilla=17,ruta_bitacora=log)
    vista=VistaGuion(comandos)
    c=ControladorJuego(sesion,vista,ruta_guardado=str(tmp_path/'equipo.sav'))
    c.jugar()
    return c,vista,log


@pytest.mark.parametrize('texto,nombre',[('DEQ 2','desequipar'),('desequipar 2','desequipar'),('AP 2','apagar'),('apagar 2','apagar')])
def test_comandos_nuevos_exigen_indice_positivo(texto,nombre):
    comando,error=interpretar(texto)
    assert error is None and comando.nombre==nombre and comando.argumento==2
    assert interpretar(texto.replace('2','-2'))[0] is None


def test_equipo_completo_se_quita_sin_alterar_orden_y_replay_coincide(tmp_path):
    comandos=['R 1','U 1','R 1','EQ 2','R 1','EQ 3','DEQ 1','DEQ 2','AP 3']
    c,v,log=jugar(tmp_path,comandos)
    j=c.partida.jugador
    assert j.arma_equipada is None and j.armadura_equipada is None
    assert (j.ataque,j.defensa)==(6,2)
    assert [n.valor.clase for n in j.inventario.recorrer_desde_frente()]==['armadura','arma','antorcha']
    antorcha=list(j.inventario.recorrer_desde_frente())[-1].valor
    assert not antorcha.encendida and antorcha.usos_restantes==0
    assert c.partida.acciones_jugador==9 and c.partida.tiempo==375
    assert c.contador_rechazos==0
    resultado=reproducir(log,FuenteEquipo(),str(tmp_path/'replay'))
    assert resultado.diferencia is None


def test_desequipar_se_deshace_con_pergamino(tmp_path):
    c,v,_=jugar(tmp_path,['R 2','R 3','EQ 1','DEQ 1','P'])
    j=c.partida.jugador
    assert j.arma_equipada is not None and j.ataque==9
    assert not any(n.valor.clase=='pergamino_retroceso' for n in j.inventario.recorrer_desde_frente())


def test_apagar_se_deshace_con_pergamino_sin_recuperar_un_uso(tmp_path):
    c,v,_=jugar(tmp_path,['R 1','R 3','U 1','AP 1','P'])
    antorcha=c.partida.jugador.inventario.head().valor
    assert antorcha.encendida and antorcha.usos_restantes==0
    assert antorcha.evento_apagado is not None and antorcha.evento_apagado.valido


def test_apagar_encender_no_renueva_combustible_y_se_guarda_igual(tmp_path):
    c,v,log=jugar(tmp_path,['R 1','U 1','AP 1','G','U 1','L','U 1'])
    antorcha=c.partida.jugador.inventario.head().valor
    assert antorcha.encendida and antorcha.usos_restantes==0
    assert antorcha.evento_apagado.tiempo==25+antorcha.duracion
    assert c.contador_rechazos==0
    resultado=reproducir(log,FuenteEquipo(),str(tmp_path/'replay'))
    assert resultado.diferencia is None


def test_uso_agotado_no_da_luz_infinita_y_historial_restaura_el_combustible():
    h,r,j=sistema()
    a=Antorcha('a','a','Antorcha',1,1,200)
    h.iniciar_accion(r)
    assert efectos.encender_antorcha(r,a)
    vencimiento=a.evento_apagado.tiempo
    assert efectos.apagar_antorcha(r,a)
    assert efectos.encender_antorcha(r,a)
    assert a.evento_apagado.tiempo==vencimiento and a.usos_restantes==0
    h.confirmar_accion()
    assert h.revertir() and a.usos_restantes==1 and not a.encendida
    efectos.encender_antorcha(r,a)
    r.avanzar_y_ejecutar(200)
    assert not a.encendida and not efectos.encender_antorcha(r,a)


def test_rechazos_de_quitar_equipo_y_apagar_no_consumen_turno(tmp_path):
    c,v,_=jugar(tmp_path,['R 2','DEQ 1','AP 1'])
    assert c.partida.tiempo==25 and c.partida.acciones_jugador==1 and c.contador_rechazos==2
