# Contratos de la vista Pygame

Documenta las interfaces de `vista_pygame/contratos.py`, la forma de `contexto`, los
datos que viajan entre escenas y los métodos públicos de `controlador_pygame.py` que
usarán las escenas de menú, inventario, pausa y fin de partida (de mi compañero). Es
el documento de referencia para que ambos implementemos en paralelo contra la misma
forma, sin esperarnos.

## 1. `EscenaBase`

```python
class EscenaBase:
    def __init__(self, contexto): ...
    def al_entrar(self, datos=None): ...   # opcional, no-op por defecto
    def al_salir(self): ...                # opcional, no-op por defecto
    def manejar_evento(self, evento): ...  # obligatorio
    def actualizar(self, dt_ms): ...       # obligatorio
    def dibujar(self, pantalla): ...       # obligatorio
```

- `app.py` mantiene una sola escena activa. En cada frame: procesa los eventos de
  pygame (`manejar_evento` por cada uno), llama `actualizar(dt_ms)` una vez y
  `dibujar(pantalla)` una vez. `dt_ms` es tiempo real (milisegundos desde el frame
  anterior), **nunca** el tiempo virtual de la partida.
- Cambiar de escena es responsabilidad de `contexto.cambiar_escena(id_escena,
  datos=None)`: `app.py` llama `al_salir()` de la escena actual, construye o reutiliza
  la escena destino, y llama `al_entrar(datos)` en ella antes del siguiente frame.
- Las escenas se registran por índice en una lista (no un dict), usando las
  constantes de `config_vista.py` (p. ej. `ESCENA_MENU = 0`, `ESCENA_PARTIDA = 1`,
  `ESCENA_INVENTARIO = 2`, `ESCENA_PAUSA = 3`, `ESCENA_FIN_PARTIDA = 4`). Esas
  constantes las fijo yo en `config_vista.py` porque las usan ambos lados; avísame si
  necesitas una más.

### Forma de `contexto`

No es una clase de `contratos.py` (es un objeto simple de `app.py`), pero su forma es
parte del contrato:

```python
contexto.controlador       # instancia de ControladorPygame (ver sección 4)
contexto.assets            # instancia de CargadorAssets
contexto.audio              # instancia de GestorAudio
contexto.cambiar_escena(id_escena, datos=None)
```

## 2. Datos que viajan entre escenas (vía `al_entrar(datos)`)

| Transición | `datos` | Quién lo arma |
| --- | --- | --- |
| `menu_criptas` → `partida` | `None`. `EscenaMenuCriptas` ya llamó `controlador.iniciar_partida(id_cripta, nombre_jugador, semilla=None)` ella misma (es dueña de esa llamada, incluida la guarda contra Enter repetido mientras arranca) antes de cambiar de escena; `EscenaPartida.al_entrar` solo vuelve a llamar `iniciar_partida` si recibe la tupla `(id_cripta, nombre_jugador, semilla)` en vez de `None` (compatibilidad con cualquier otro llamador que arme la tupla en vez de iniciar la partida él mismo). `semilla` es `int` o `None`; si viene `None`, `ControladorPygame.iniciar_partida` genera una con `controlador.semilla.generar_semilla()` (igual que la consola). | escena de menú (`vista_pygame/escenas/menu_criptas.py`, implementada) |
| `partida` → `fin_partida` | una instancia de `ResumenPartida` (sección 3) | escena de partida (yo) |
| cualquier escena → `pausa` | ninguno (`None`); pausa lee lo que necesita de `contexto.controlador` | quien pausa |
| `pausa`/`fin_partida` → `menu_criptas` | ninguno | mi compañero |

### Estado: `menu_criptas` implementada

`vista_pygame/escenas/menu_criptas.py` reemplaza el placeholder de
`stubs_temporales.EscenaMenuCriptasTemporal` para `ESCENA_MENU` (ver
`app.py`). Fondo `assets/ui/portada.png` (boceto), escalado una sola vez
manteniendo proporción; sin el archivo, color sólido de la paleta — nunca
rompe. El título, el subtítulo y un botón por cripta (de
`controlador.listar_criptas()`, consultada en un hilo propio de la escena
para no congelar la ventana) se dibujan en las mismas coordenadas, escaladas,
donde están los paneles del boceto, sobre una placa opaca que cubre esa zona
entera — el texto de ejemplo del boceto nunca se usa como dato ni queda
visible, haya 1, 4 o 15 criptas. Scroll automático si la lista no entra.
Campo de nombre editable (máx. 20 caracteres, precargado en `"Jugador"`).
Navegación: Tab/Shift+Tab (nombre → criptas → nombre, cíclico), flechas
↑/↓ entre criptas, Enter o clic confirma, Esc pide salir
(`pygame.event.post(pygame.event.Event(pygame.QUIT))`, sin tocar `app.py`).
Con error al listar (red/offline), `R` reintenta. Pruebas en
`tests/vista/test_menu_criptas.py`.

## 3. `ResumenPartida`

```python
@dataclass
class ResumenPartida:
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
```

Origen de cada campo (ninguno se recalcula en la vista):

| Campo | Origen |
| --- | --- |
| `resultado` | `partida.estado` (ya es `"victoria"` o `"derrota"` cuando `partida.terminada`) |
| `nombre_jugador` | **(propuesta pendiente de aprobación, ver `ANALISIS_ARQUITECTURA.md` §8.2)** `sesion.nombre_jugador`, fijado por `controlador.inicio_partida.nueva_partida(..., nombre_jugador=...)` — vive en el controlador compartido, no en `Jugador` ni solo en `ControladorPygame`, porque §2.12 lo exige en la tabla de puntajes. `ControladorPygame.iniciar_partida(id_cripta, nombre_jugador, semilla)` lo recibe de la escena de menú y lo reenvía tal cual a `nueva_partida`. Hasta que se apruebe, `ControladorPygame` puede seguir usando un valor local solo para mostrarlo en el HUD, pero **no** debe considerarse la fuente final. |
| `id_cripta`, `version_cripta`, `acciones_jugador`, `enemigos_derrotados`, `tiempo_final` | `partida.resumen_puntaje()` |
| `solicitudes_realizadas` | `fuente.requests_realizados` (0 en modo offline) |
| `presupuesto_solicitudes` | `partida.cripta.presupuesto_solicitudes` |
| `aciertos_cache`, `fallos_cache` | `sesion.red.estadisticas_cache()` → `"aciertos"` / `"fallos"` |

**Decidido** (§8.1 de `ANALISIS_ARQUITECTURA.md`): no hay tabla de puntajes
persistente en esta migración. `tabla_puntajes()` devuelve una lista vacía; la tabla
real (registro en el modelo + adaptador de disco + ordenamiento propio) es una tarea
aparte, diseñada pero no implementada — ver esa sección para el diseño completo.

## 4. Métodos públicos de `ControladorPygame` (para menú, pausa y fin de partida)

```python
class ControladorPygame:
    def listar_criptas(self) -> list:
        """[{'id': str, 'nombre': str, 'salas': int, 'dificultad': int}, ...]
        Delega en fuente.listar_criptas()['criptas']. Puede lanzar OSError/ValueError
        si la fuente falla; la escena de menú decide cómo mostrarlo."""

    def iniciar_partida(self, id_cripta, nombre_jugador, semilla=None):
        """Crea la SesionPartida (nueva_partida), arranca el hilo de modelo y deja
        todo listo para que la escena de partida empiece a pedir estado. No bloquea
        más que lo que tarda nueva_partida() en garantizar el contenido de la sala
        inicial (igual que hoy en consola, antes de que exista cualquier vista)."""

    def guardar(self, ruta=None) -> None:
        """Encola el equivalente a 'G [ruta]' hacia el hilo de modelo. No toca
        el modelo desde el hilo de Pygame."""

    def cargar(self, ruta=None) -> None:
        """Encola el equivalente a 'L [ruta]'."""

    def salir(self) -> None:
        """Encola el equivalente a 'Q', espera (join) a que el hilo de modelo
        cierre bitácora/red y termine. Para usar al salir del programa o al volver
        al menú desde pausa."""

    def tabla_puntajes(self) -> list:
        """Devuelve [] por ahora (decidido, ANALISIS_ARQUITECTURA.md §8.1): no hay
        tabla de puntajes persistente en esta migración. La tarea futura la
        implementaría en modelo/puntaje.py + persistencia/tabla_puntajes.py +
        controlador/puntajes.py, compartida por consola y GUI; este método pasaría
        a delegar en controlador.puntajes.listar_puntajes()."""

    def reporte_red(self) -> list[str]:
        """Las líneas que hoy arma reporte_red.construir_reporte(...), para que
        pausa o fin_partida las muestren si quieren un detalle de red/caché."""
```

`ControladorPygame` también implementa, como clase interna o mixin, el protocolo de
`VistaConsola` (`mostrar_estado`, `agregar_mensaje`, `mensajes`, `restaurar_mensajes`,
`mostrar_inventario`, `mostrar_ayuda`, `mostrar_objeto`, `mostrar_fin`,
`leer_comando`) para poder pasarse como `vista` a `ControladorJuego` sin modificarlo.
Esa parte no la necesitan las escenas de mi compañero directamente; está documentada
en detalle en `ANALISIS_ARQUITECTURA.md` §7 y se termina de fijar en FASE 2.

## 5. Forma de los "eventos" para `ColaAnimaciones.agregar_desde_eventos`

Por fijar en FASE 2 junto con `controlador_pygame.py` (depende de cómo termine el
puente de mensajes/estado entre hilos), pero el contrato que van a cumplir es: una
lista de objetos simples, cada uno con al menos `tipo` (string: `"ataque"`,
`"movimiento"`, `"daño"`, `"muerte"`, `"recoger"`, `"puerta"`, `"veneno"`,
`"curacion"`, ...) y las referencias de entidades que necesite la animación
(instancias ya vivas de `Jugador`/`Enemigo`/`Objeto`, no copias). `GestorAudio.
reproducir_sfx(tipo_evento)` usa el mismo valor de `tipo`. Antes de que exista la
versión real, `stubs_temporales.py` ofrece una `ColaAnimaciones` que no hace nada
(dibuja rectángulos de color donde correspondería un efecto) para que ambos lados
puedan probar sin esperar al arte final.

Para que esta cola pueda recibir **todos** los eventos de un enemigo rápido (puede
actuar varias veces antes de la siguiente decisión del jugador) en el orden exacto
del modelo, y no solo texto narrado, `ControladorPygame` necesita suscribirse a dos
hooks que hoy no existen en `Partida` — propuestos en `ANALISIS_ARQUITECTURA.md`
§8.4, **pendientes de aprobación**:

- `partida.al_mover_enemigo` → `f(enemigo, sala_origen, sala_destino)`
- `partida.al_atacar` → `f(atacante, objetivo, dano)`

(`partida.al_morir_enemigo` → `f(enemigo)` ya existe hoy y no necesita cambios.)
Hasta que se aprueben, la escena de partida solo puede animar enemigos de forma
genérica a partir del texto de `agregar_mensaje`, sin saber con certeza qué sprite
ni qué dirección corresponde.

## 6. Panel "Próximos turnos" (opcional, pendiente de aprobación)

Si se aprueba la lectura de solo lectura propuesta en `ANALISIS_ARQUITECTURA.md`
§8.5 (`HeapMinimo.vista_ordenada(n)` + `Reloj.proximos_eventos(n)`), la escena de
partida podría mostrar los próximos 5 eventos de la agenda (actor + tiempo virtual)
sin mutar el modelo. Sin esa aprobación, el panel no se implementa.
