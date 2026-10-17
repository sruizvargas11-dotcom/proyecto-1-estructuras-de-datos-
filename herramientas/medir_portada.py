"""Mide, una sola vez, los rectángulos de las placas pintadas en portada.png
(título, subtítulo y 4 filas de ejemplo) y los imprime como proporciones del
tamaño de la imagen (x, y, ancho, alto, cada uno entre 0 y 1) — listas para
pegar a mano en vista_pygame/config_vista.py.

Uso:
    python -m herramientas.medir_portada [ruta_imagen]

Herramienta de desarrollo: se corre una sola vez, a mano. El juego y los
tests nunca la importan ni dependen de ella en tiempo de ejecución; solo usa
pygame (ya es dependencia del proyecto), sin agregar numpy/Pillow.

Método: portada.png es una escena nocturna de bajo contraste donde el fondo
(cielo, montañas) puede ser tan oscuro como el interior de una placa — un
umbral de luminancia absoluto no separa placa de fondo de forma confiable,
y la posición vertical de cada fila no varía con el texto (es una cuadrícula
regular por diseño), así que no vale la pena perseguirla por imagen: el
TOP_FILA_0/ESPACIO_FILA/ALTO_FILA de abajo están calibrados una sola vez con
una cuadrícula superpuesta a la imagen.

Lo que sí varía con el texto, y por eso sí se mide automáticamente, es el
ANCHO de cada fila: dentro de la franja vertical ya calibrada de cada fila,
se busca el tramo horizontal "plano" (poca diferencia entre píxeles
vecinos) más largo sin tocar los bordes de la franja — eso es el interior
de madera, acotado por el fondo más irregular a los lados.

Título y subtítulo no se miden así: sus esquinas llevan un remate metálico
ornamentado (no madera plana), así que el detector de planitud las excluye
y subestima el ancho. Sus cuatro valores están calibrados a mano, con el
mismo método de cuadrícula superpuesta que las posiciones de las filas.
"""
import os
import sys

import pygame

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_POR_DEFECTO = os.path.join(RAIZ, "portada.png")

DELTA_PLANO_MAXIMO = 6      # diferencia máxima entre píxeles vecinos para seguir "plano"
MUESTREO_X = 2               # cada cuántos píxeles se muestrea una fila (velocidad)
X_BUSQUEDA_MIN, X_BUSQUEDA_MAX = 180, 650   # recorte horizontal razonable para las 4 filas

# Posición vertical de las 4 filas: calibrada a mano (cuadrícula superpuesta
# a portada.png), no detectada por fila — el espaciado y el alto son
# prácticamente constantes por diseño (es una cuadrícula de lista).
TOP_FILA_0 = 102
ESPACIO_FILA = 44
ALTO_FILA = 32

# Título y subtítulo: calibrados a mano por completo (ver docstring).
RECTANGULOS_FIJOS = (
    ("TITULO", 236, 16, 332, 54),
    ("SUBTITULO", 315, 65, 188, 28),
)

# Margen de seguridad aplicado a TODOS los rectángulos medidos antes de
# convertir a proporción: la validación visual (dibujar los rectángulos
# medidos sobre portada.png) muestra que quedan 2-5 px justos en varios
# bordes — mejor que la medición ya venga con margen a que cada placa real
# tenga que adivinarlo por separado.
MARGEN_SEGURIDAD = 3


def _luminancia(color):
    return (color[0] + color[1] + color[2]) / 3


def _tramo_plano_mas_largo(valores, delta_max):
    """(inicio, fin, largo) del tramo contiguo más largo donde cada par de
    vecinos difiere como mucho delta_max."""
    mejor = (0, 0, 1)
    inicio = 0
    for i in range(1, len(valores)):
        if abs(valores[i] - valores[i - 1]) > delta_max:
            largo = i - inicio
            if largo > mejor[2]:
                mejor = (inicio, i, largo)
            inicio = i
    largo = len(valores) - inicio
    if largo > mejor[2]:
        mejor = (inicio, len(valores), largo)
    return mejor


def _medir_ancho_fila(superficie, y_top, alto):
    """Dentro de la franja [y_top, y_top + alto), la fila de píxeles con el
    tramo horizontal plano más largo sin tocar los bordes de la ventana de
    búsqueda en x (eso descarta el fondo, que suele ocupar la ventana de
    punta a punta). Devuelve (izquierda, derecha)."""
    xs = list(range(X_BUSQUEDA_MIN, X_BUSQUEDA_MAX, MUESTREO_X))
    n = len(xs)
    mejor_largo = 0
    izquierda, derecha = X_BUSQUEDA_MIN, X_BUSQUEDA_MAX
    for y in range(y_top, y_top + alto):
        valores = [_luminancia(superficie.get_at((x, y))) for x in xs]
        inicio, fin, largo = _tramo_plano_mas_largo(valores, DELTA_PLANO_MAXIMO)
        if inicio == 0 or fin >= n:
            continue   # toca el borde de la ventana: probablemente fondo, no placa
        if largo > mejor_largo:
            mejor_largo, izquierda, derecha = largo, xs[inicio], xs[min(fin, n - 1)]
    return izquierda, derecha


def medir(ruta):
    pygame.init()
    pygame.display.set_mode((1, 1))   # convert() exige un modo de video activo
    try:
        superficie = pygame.image.load(ruta).convert()
    finally:
        pygame.quit()
    ancho_img, alto_img = superficie.get_size()

    rectangulos = list(RECTANGULOS_FIJOS)
    for indice in range(4):
        y_top = TOP_FILA_0 + indice * ESPACIO_FILA
        izquierda, derecha = _medir_ancho_fila(superficie, y_top, ALTO_FILA)
        rectangulos.append((f"FILA_{indice}", izquierda, y_top, derecha - izquierda, ALTO_FILA))

    m = MARGEN_SEGURIDAD
    rectangulos = [(nombre, x - m, y - m, w + 2 * m, h + 2 * m)
                  for nombre, x, y, w, h in rectangulos]
    return rectangulos, (ancho_img, alto_img)


def main():
    ruta = sys.argv[1] if len(sys.argv) > 1 else RUTA_POR_DEFECTO
    rectangulos, (ancho_img, alto_img) = medir(ruta)

    print(f"Imagen: {ruta} ({ancho_img}x{alto_img})\n")
    for nombre, x, y, w, h in rectangulos:
        fx, fy, fw, fh = x / ancho_img, y / alto_img, w / ancho_img, h / alto_img
        print(f"{nombre}: px=({x}, {y}, {w}, {h})  "
             f"proporcion=({fx:.4f}, {fy:.4f}, {fw:.4f}, {fh:.4f})")


if __name__ == "__main__":
    main()
