"""Contratos de la vista Pygame.

Interfaces que las escenas, el cargador de assets, el gestor de audio y la cola de
animaciones deben cumplir para conectarse con app.py y controlador_pygame.py. Las
firmas están fijadas de antemano (ver CONTRATOS.md) para que mi compañero pueda
implementar sus archivos (componentes, animaciones, escenas de menú/inventario/pausa/
fin de partida) en paralelo, contra stubs_temporales.py, sin esperar a la escena de
partida real.

No depende de pygame: solo son formas (ABC), así que se puede importar y probar sin
una pantalla inicializada.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


class EscenaBase(ABC):
    """Una pantalla del juego (menú, partida, inventario, pausa, fin de partida).

    contexto expone: controlador, assets, audio, cambiar_escena(id_escena, datos=None).
    Ver CONTRATOS.md para la forma exacta de 'contexto' y qué trae 'datos' en cada
    transición entre escenas.
    """

    def __init__(self, contexto):
        self.contexto = contexto

    def al_entrar(self, datos=None):
        """Se llama al activar la escena; 'datos' es lo que envió la escena anterior."""

    def al_salir(self):
        """Se llama justo antes de cambiar a otra escena."""

    @abstractmethod
    def manejar_evento(self, evento):
        """Procesa un evento de pygame (teclado, mouse, etc.)."""
        raise NotImplementedError

    @abstractmethod
    def actualizar(self, dt_ms):
        """Avanza temporizadores/animaciones propios de la escena.

        dt_ms es el tiempo real transcurrido desde el frame anterior. Nunca debe
        tocar el reloj virtual de la partida (ese solo avanza en el modelo).
        """
        raise NotImplementedError

    @abstractmethod
    def dibujar(self, pantalla):
        """Dibuja la escena completa sobre la superficie 'pantalla'."""
        raise NotImplementedError


class CargadorAssets(ABC):
    """Fuente de superficies y fuentes ya convertidas (convert()/convert_alpha()),
    lista para blitear sin coste adicional en el bucle de dibujo."""

    @abstractmethod
    def sprite_jugador(self, estado, direccion):
        """estado: p. ej. 'parado'|'caminando'|'atacando'|'herido'. direccion: N/S/E/O."""
        raise NotImplementedError

    @abstractmethod
    def sprite_enemigo(self, id_tipo, comportamiento):
        """id_tipo: tipo_id del catálogo (p. ej. 'ent_rata_gigante'). comportamiento:
        'guardián'|'errante'|'rastreador', por si el arte varía según el rol."""
        raise NotImplementedError

    @abstractmethod
    def sprite_objeto(self, id_tipo, clase):
        """clase: 'arma'|'armadura'|'pocion'|'antidoto'|'antorcha'|'llave'|
        'pergamino_retroceso' (mismos valores que Objeto.clase en el modelo)."""
        raise NotImplementedError

    @abstractmethod
    def sprite_entorno(self, nombre):
        """Piso, paredes, puertas (abierta/cerrada/con llave), trampas, decorado."""
        raise NotImplementedError

    @abstractmethod
    def sprite_efecto(self, nombre):
        """Overlay visual: veneno, antorcha encendida, impacto, curación, etc."""
        raise NotImplementedError

    @abstractmethod
    def icono(self, nombre):
        """Icono pequeño de HUD: vida, ataque, defensa, velocidad, salida, etc."""
        raise NotImplementedError

    @abstractmethod
    def fuente(self, tamano):
        """pygame.font.Font ya cargada en el tamaño pedido (reutilizable, sin recargar
        el archivo cada vez)."""
        raise NotImplementedError


class GestorAudio(ABC):
    """disponible es False cuando el mezclador de audio no se pudo inicializar
    (por ejemplo, SDL_AUDIODRIVER=dummy en pruebas): en ese caso las llamadas no
    deben lanzar, solo no sonar."""

    @property
    @abstractmethod
    def disponible(self):
        raise NotImplementedError

    @abstractmethod
    def reproducir_musica(self, estado):
        """estado identifica la pista: p. ej. 'menu'|'partida'|'combate'|'victoria'|
        'derrota'. Hace loop y evita reiniciar la pista si ya está sonando."""
        raise NotImplementedError

    @abstractmethod
    def reproducir_sfx(self, tipo_evento):
        """tipo_evento: la misma clave de evento que usa ColaAnimaciones
        (ver agregar_desde_eventos) — un golpe, una puerta, recoger un objeto..."""
        raise NotImplementedError

    @abstractmethod
    def set_volumen(self, musica, sfx):
        """musica y sfx: floats en [0.0, 1.0]."""
        raise NotImplementedError

    @abstractmethod
    def alternar_mute(self):
        """Alterna silencio general; devuelve el nuevo estado (True = silenciado)."""
        raise NotImplementedError


class ColaAnimaciones(ABC):
    """ocupada es True mientras haya una animación en curso que la escena de
    partida deba esperar antes de, por ejemplo, confirmar una nueva acción."""

    @property
    @abstractmethod
    def ocupada(self):
        raise NotImplementedError

    @abstractmethod
    def agregar_desde_eventos(self, eventos):
        """eventos: lo que entregó ControladorPygame para el ciclo recién procesado
        (ver CONTRATOS.md para su forma). No bloquea: encola y vuelve."""
        raise NotImplementedError

    @abstractmethod
    def actualizar(self, dt_ms):
        raise NotImplementedError

    @abstractmethod
    def dibujar(self, pantalla):
        raise NotImplementedError


@dataclass
class ResumenPartida:
    """Lo que necesita la escena de fin de partida.

    Todos los campos salen ya calculados del modelo o los adaptadores
    (Partida.resumen_puntaje(), ControladorRed.estadisticas_cache(), la fuente de
    datos); esta clase no recalcula nada, solo empaqueta.
    """
    resultado: str                   # "victoria" | "derrota"
    nombre_jugador: str
    id_cripta: str
    version_cripta: str
    acciones_jugador: int
    enemigos_derrotados: int
    tiempo_final: int
    solicitudes_realizadas: int
    presupuesto_solicitudes: int
    aciertos_cache: int
    fallos_cache: int
