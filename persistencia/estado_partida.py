"""Codec de referencias del estado lógico sobre PartidaBinaria.

Los dict/list de este módulo son representación de transporte JSON, no TDAs
del juego. No usa pickle, eval, imports indicados por el archivo ni código
serializado. Conserva identidades y ciclos (nodos, handles y deltas).
"""
import importlib
import random

from estructuras.vector_dinamico import Vector
from estructuras.array_ordenado import ArrayOrdenado
from estructuras.lista_simple import ListaSimple, NodoSimple
from estructuras.lista_doble import ListaDoble, NodoDoble
from estructuras.heap_minimo import HeapMinimo, _EntradaHeap
from modelo.ejecutor_evento import EjecutorEvento
from modelo.partida import Partida
from modelo.mundo.sala import Sala

MODULOS = (
    'estructuras.vector_dinamico', 'estructuras.lista_simple',
    'estructuras.lista_doble', 'estructuras.pila', 'estructuras.heap_minimo',
    'estructuras.cola', 'estructuras.listalru', 'estructuras.array_ordenado',
    'modelo.partida', 'modelo.reloj', 'modelo.rastro', 'modelo.historial',
    'modelo.deltas', 'modelo.entorno', 'modelo.efectos', 'modelo.ejecutor_evento',
    'modelo.mundo.cripta_modelo', 'modelo.mundo.sala', 'modelo.mundo.salida',
    'modelo.entidades.actor', 'modelo.entidades.jugador', 'modelo.entidades.enemigo',
    'modelo.entidades.trampa', 'modelo.entidades.objetos.objeto',
    'modelo.entidades.objetos.arma', 'modelo.entidades.objetos.armadura',
    'modelo.entidades.objetos.pocion', 'modelo.entidades.objetos.antorcha',
    'modelo.entidades.objetos.antidoto', 'modelo.entidades.objetos.llave',
    'modelo.entidades.objetos.pergamino_retroceso',
    'modelo.entidades.objetos.fabrica_objetos',
)
OMITIDOS_PARTIDA = ('al_mensaje', 'al_morir_enemigo', 'al_entrar_sala',
                    'al_mover_enemigo', 'al_atacar',
                    '_resolver_ficha', 'aplicar_efecto')


def _clases():
    clases = ArrayOrdenado()
    for nombre in MODULOS:
        modulo = importlib.import_module(nombre)
        for nombre_clase, clase in vars(modulo).items():
            if isinstance(clase, type) and clase.__module__ == nombre:
                clases.insertar(nombre + '.' + nombre_clase, clase)
    return clases


def codificar(raiz):
    clases = _clases()
    referencias, pendientes, registros = ArrayOrdenado(), [], []

    def valor(objeto, grupo):
        if objeto is None or type(objeto) in (str, bool, int, float):
            return objeto
        if type(objeto) is tuple:
            return {'tupla': [valor(x, grupo) for x in objeto]}
        identidad = id(objeto)
        numero = referencias.busqueda_binaria(identidad)
        if numero is None:
            numero = len(pendientes)
            referencias.insertar(identidad, numero)
            pendientes.append((objeto, objeto.id if type(objeto) is Sala else grupo))
        return {'ref': numero}

    referencia = valor(raiz, None)
    indice = 0
    while indice < len(pendientes):
        objeto, grupo = pendientes[indice]
        if type(objeto) in (list, dict):
            tipo = 'lista' if type(objeto) is list else 'diccionario'
            datos = ([valor(x, grupo) for x in objeto] if tipo == 'lista'
                     else [[valor(k, grupo), valor(v, grupo)] for k, v in objeto.items()])
        elif type(objeto) is random.Random:
            tipo, datos = 'azar', valor(objeto.getstate(), grupo)
        else:
            tipo = type(objeto).__module__ + '.' + type(objeto).__name__
            if clases.busqueda_binaria(tipo) is None:
                raise ValueError(f'No se puede guardar el tipo {tipo}.')
            datos = {k: valor(v, grupo) for k, v in vars(objeto).items()
                     if not (type(objeto) is Partida and k in OMITIDOS_PARTIDA)}
        registros.append({'id': indice, 'grupo': grupo, 'tipo': tipo, 'datos': datos})
        indice += 1
    return referencia, registros


def decodificar(referencia, registros):
    clases = _clases()
    objetos = [None] * len(registros)
    # Primera pasada: todas las identidades existen antes de enlazarlas.
    for i, registro in enumerate(registros):
        if registro['id'] != i:
            raise ValueError('Referencias de guardado incompletas o repetidas.')
        tipo = registro['tipo']
        clase = clases.busqueda_binaria(tipo)
        if tipo == 'lista':
            objetos[i] = []
        elif tipo == 'diccionario':
            objetos[i] = {}
        elif tipo == 'azar':
            objetos[i] = random.Random(0)
        elif clase is not None:
            objetos[i] = clase.__new__(clase)
        else:
            raise ValueError(f'Tipo no permitido en el guardado: {tipo}.')

    def valor(dato):
        if not isinstance(dato, dict):
            if dato is not None and type(dato) not in (str, bool, int, float):
                raise ValueError('Valor de guardado inválido.')
            return dato
        if set(dato) == {'ref'}:
            i = dato['ref']
            if type(i) is not int or not 0 <= i < len(objetos):
                raise ValueError('Referencia de guardado fuera de rango.')
            return objetos[i]
        if set(dato) == {'tupla'}:
            return tuple(valor(x) for x in dato['tupla'])
        raise ValueError('Referencia de guardado inválida.')

    for objeto, registro in zip(objetos, registros):
        tipo, datos = registro['tipo'], registro['datos']
        if tipo == 'lista':
            objeto.extend(valor(x) for x in datos)
        elif tipo == 'diccionario':
            objeto.update((valor(k), valor(v)) for k, v in datos)
        elif tipo == 'azar':
            objeto.setstate(valor(datos))
        else:
            for campo, dato in datos.items():
                if not isinstance(campo, str) or campo.startswith('__'):
                    raise ValueError('Campo inválido en el guardado.')
                setattr(objeto, campo, valor(dato))
            if type(objeto) is Partida:
                for campo in OMITIDOS_PARTIDA:
                    setattr(objeto, campo, Vector() if campo.startswith('al_') else None)
    _validar_estructuras(objetos)
    return valor(referencia)


def _validar_estructuras(objetos):
    """Rechaza enlaces cíclicos/longitudes falsas antes de recorrer la partida."""
    for objeto in objetos:
        if type(objeto) is Vector:
            if (type(objeto._datos) is not list or type(objeto._tamano) is not int
                    or not 0 <= objeto._tamano <= objeto._capacidad == len(objeto._datos)):
                raise ValueError('Vector inconsistente en el guardado.')
        elif type(objeto) in (ListaSimple, ListaDoble):
            if type(objeto._tamano) is not int or not 0 <= objeto._tamano <= len(objetos):
                raise ValueError('Longitud de lista inválida.')
            nodo, anterior = objeto._head, None
            for _ in range(objeto._tamano):
                tipo_nodo = NodoDoble if type(objeto) is ListaDoble else NodoSimple
                if type(nodo) is not tipo_nodo:
                    raise ValueError('Lista truncada en el guardado.')
                if tipo_nodo is NodoDoble and (nodo.anterior is not anterior
                                             or nodo._propietario is not objeto):
                    raise ValueError('Enlaces de lista doble inconsistentes.')
                anterior, nodo = nodo, nodo.siguiente
            if nodo is not None or (type(objeto) is ListaDoble and objeto._cola is not anterior):
                raise ValueError('Lista cíclica o longitud incorrecta.')
        elif type(objeto) is EjecutorEvento:
            if objeto.tipo not in ('decision', 'enemigo', 'rearme', 'cierre',
                                   'veneno', 'velocidad', 'antorcha', 'regeneracion'):
                raise ValueError('Ejecutor de evento desconocido.')
    for objeto in objetos:
        if type(objeto) is HeapMinimo:
            for i, entrada in enumerate(objeto._datos):
                if (type(entrada) is not _EntradaHeap or entrada._propietario is not objeto
                        or not entrada._en_heap or type(entrada.tiempo) is not int
                        or entrada.tiempo < 0 or type(entrada.secuencia) is not int
                        or not 0 <= entrada.secuencia < objeto.siguiente_secuencia):
                    raise ValueError('Entrada de agenda inconsistente.')
                if i and objeto._datos.obtenerValor((i-1)//2).clave() > entrada.clave():
                    raise ValueError('Orden del heap inválido.')
