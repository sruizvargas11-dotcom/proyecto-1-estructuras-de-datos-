"""Copias de presentación: la vida baja con los impactos, sin tocar el modelo."""
from dataclasses import replace


def _poner_vida(estado,identificador,vida,tiempo=None):
    def actor(a):
        if a.instancia_id!=identificador:return a
        return replace(a,vida=max(0,min(a.vida_max,vida(a))))
    return replace(estado,jugador=actor(estado.jugador),
                   enemigos_activos=[actor(a) for a in estado.enemigos_activos],
                   enemigos_dormidos=[actor(a) for a in estado.enemigos_dormidos],
                   tiempo=estado.tiempo if tiempo is None else tiempo)


def preparar_vidas(estado,eventos):
    if estado is None:return None
    vistos=[]
    for e in eventos:
        if getattr(e,'tipo',None) not in ('ataque','trampa'):continue
        identificador=e.objetivo_id
        if identificador in vistos:continue
        vistos.append(identificador)
        antes=getattr(e,'vida_antes',None)
        if antes is not None:estado=_poner_vida(estado,identificador,lambda a:antes)
    return estado


def aplicar_impactos(estado,eventos):
    if estado is None:return None
    for e in eventos:
        despues=getattr(e,'vida_despues',None)
        estado=_poner_vida(estado,e.objetivo_id,
                          lambda a:despues if despues is not None else a.vida-e.dano,
                          getattr(e,'tiempo',None))
    return estado
