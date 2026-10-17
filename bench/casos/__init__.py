"""Menú de casos del --bench. Para agregar uno: crea casos/mi_caso.py con una
función `correr()` que devuelva una lista de Fila, e impórtalo aquí."""
from bench.casos import (heap, lru, recuperacion, inventario,
                         historial, ordenamiento, binario_json, mensajes)

CASOS = [
    mensajes.correr,       # buffer circular frente a desplazamientos
    heap.correr,           # agenda de eventos
    lru.correr,            # búsquedas de caché
    recuperacion.correr,   # recuperación de fichas liberadas
    inventario.correr,     # inventario
    historial.correr,      # historial de retroceso
    ordenamiento.correr,   # ordenamientos
    binario_json.correr,   # guardado/carga
]
