"""Inventario: ListaDoble propia vs list de Python (agregar al final y quitar al inicio)."""
from bench.medicion import Fila, medir

TAMANOS = (10, 50, 500)


def _con_lista_doble(n):
    """Agrega n objetos al final y los quita todos por el inicio con la ListaDoble propia."""
    from estructuras.lista_doble import ListaDoble
    inventario = ListaDoble()
    for i in range(n):
        inventario.insertar_al_final(i)
    for _ in range(n):
        inventario.eliminar_nodo(inventario.head())


def _con_list(n):
    """Alternativa: list de Python (quitar al inicio desplaza todo)."""
    inventario = []
    for i in range(n):
        inventario.append(i)
    for _ in range(n):
        inventario.pop(0)


def correr():
    filas = []
    for n in TAMANOS:
        for nombre, funcion in (("ListaDoble", _con_lista_doble), ("list", _con_list)):
            filas.append(Fila("inventario", nombre, n, medir(funcion, n)))
    return filas
