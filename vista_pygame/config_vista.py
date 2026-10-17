"""Configuración fija de la vista Pygame: resolución, FPS, ids de escena y
paleta. No depende de pygame (solo números y strings) para poder importarse
desde pruebas sin inicializar una pantalla.
"""

# -- Ventana / resolución lógica -------------------------------------------

ANCHO_LOGICO = 1280
ALTO_LOGICO = 720
FPS_OBJETIVO = 60
TITULO_VENTANA = "CRIPTA"

# -- Ids de escena: índices en la lista de escenas de app.py, nunca un dict --

ESCENA_MENU = 0
ESCENA_PARTIDA = 1
ESCENA_INVENTARIO = 2
ESCENA_PAUSA = 3
ESCENA_FIN_PARTIDA = 4
CANTIDAD_ESCENAS = 5

# -- Paleta (tomada del boceto: fantasía oscura, fría con acentos cálidos) --
# Noche azulada/gris para fondo y paredes de piedra, dorado/fuego para
# resaltados y vida, placas de madera con marco metálico para los paneles.

COLOR_FONDO = (18, 22, 32)
COLOR_CIELO_NOCHE = (30, 38, 56)
COLOR_PIEDRA = (54, 58, 68)
COLOR_PIEDRA_CLARA = (82, 86, 98)
COLOR_MADERA = (58, 40, 28)
COLOR_MADERA_CLARA = (92, 64, 42)
COLOR_METAL = (120, 126, 138)
COLOR_METAL_OSCURO = (40, 42, 50)
COLOR_ORO = (198, 158, 74)
COLOR_FUEGO = (224, 120, 48)
COLOR_TEXTO = (224, 220, 206)
COLOR_TEXTO_TENUE = (150, 148, 140)
COLOR_VIDA = (168, 44, 44)
COLOR_VIDA_FONDO = (48, 24, 24)
COLOR_VENENO = (96, 150, 64)
COLOR_SELECCION = (224, 180, 90)
COLOR_PELIGRO = (196, 64, 64)
COLOR_AVISO = (224, 196, 96)

# -- Sala / HUD --------------------------------------------------------

ANCHO_PANEL_HUD = 320
ALTO_PANEL_MENSAJES = 170
CAPACIDAD_MENSAJES_HUD = 20  # igual que la consola (ArrayCircular)

# -- Layout fijo de enemigos (no hay cuadrícula en el juego: son posiciones
# visuales de presentación, en orden de instancia_id) --

MAX_ENEMIGOS_VISIBLES = 6
SLOTS_ENEMIGOS = (
    (560, 260), (720, 260), (880, 260),
    (560, 420), (720, 420), (880, 420),
)

# -- Minimapa: offset en celdas por dirección (el modelo no tiene
# coordenadas; el layout se calcula una vez por cripta con un BFS). Tupla de
# pares, no dict (regla del curso): se recorre linealmente con offset_direccion().

OFFSETS_DIRECCION = (("N", 0, -1), ("S", 0, 1), ("E", 1, 0), ("O", -1, 0))
DIRECCIONES = ("N", "S", "E", "O")
CELDA_MINIMAPA = 14


def offset_direccion(direccion):
    """(dx, dy) de una celda del minimapa al moverse hacia 'direccion'."""
    for nombre, dx, dy in OFFSETS_DIRECCION:
        if nombre == direccion:
            return dx, dy
    raise ValueError(f"Dirección desconocida: {direccion}")

# -- Panel opcional "próximos turnos" --

CANTIDAD_PROXIMOS_TURNOS = 5

# -- Teclas (ver entrada/mapeo_teclas.py para el mapeo completo) --

TECLA_AYUDA = "F1"

# -- Portada: layout de las placas pintadas en portada.png, medido una sola
# vez con herramientas/medir_portada.py (es layout, no datos de cripta: no
# cambia entre partidas ni depende de qué criptas devuelva la API). Cada
# tupla es una proporción (x, y, ancho, alto, todos entre 0 y 1) del lienzo
# de referencia PORTADA_REF_ANCHO x PORTADA_REF_ALTO -- el tamaño real de
# portada.png -- que la escena escala y centra en la ventana real (ver
# escenas/menu_criptas.py), nunca en píxeles fijos de una sola resolución.

PORTADA_REF_ANCHO = 804
PORTADA_REF_ALTO = 529

PORTADA_TITULO_PROP = (0.2898, 0.0246, 0.4204, 0.1134)
PORTADA_SUBTITULO_PROP = (0.3881, 0.1172, 0.2413, 0.0643)
PORTADA_FILAS_PROP = (
    (0.3246, 0.1871, 0.3557, 0.0718),
    (0.2998, 0.2703, 0.4104, 0.0718),
    (0.3097, 0.3535, 0.4005, 0.0718),
    (0.2948, 0.4367, 0.4254, 0.0718),
)
# Separación vertical entre el tope de una fila y la siguiente (promedio
# medido, ~constante por diseño): para la 5ta cripta en adelante, que ya no
# tiene fila pintada de referencia.
PORTADA_ESPACIO_FILA_PROP = 0.0832
# Eje horizontal común en el que están centradas título/subtítulo/filas en
# el boceto (promedio de los 6 centros medidos).
PORTADA_CENTRO_X_PROP = 0.5056
