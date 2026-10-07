
"""Algoritmos de ordenamiento propios."""

def merge_sort(datos, clave):
    """Devuelve una lista ordenada sin modificar la recibida."""
    if len(datos) <= 1:
        return datos[:]

    medio = len(datos) // 2
    izquierda = merge_sort(datos[:medio], clave)
    derecha = merge_sort(datos[medio:], clave)

    resultado = []
    i = 0
    j = 0

    while i < len(izquierda) and j < len(derecha):
        if clave(izquierda[i]) <= clave(derecha[j]):
            resultado.append(izquierda[i])
            i += 1
        else:
            resultado.append(derecha[j])
            j += 1

    while i < len(izquierda):
        resultado.append(izquierda[i])
        i += 1

    while j < len(derecha):
        resultado.append(derecha[j])
        j += 1

    return resultado