# Cierre técnico del bloque 2

Fecha: 11 de octubre de 2026. Base: `origin/main` en `fde0d77` (merge del PR #8 de Daniel Centeno). Rama de revisión: `cierre/bloque2-verificado`.

Se trabaja sobre el proyecto original de PyCharm. Se incorporó main por avance rápido desde `ca56d12`. No se reutilizó el PR #9 cerrado ni se migraron carpetas. El merge del nuevo PR y la revisión humana de los borradores quedan a cargo del equipo.

## Verificación por rol

| Rol | Componentes presentes y revisados | Evidencia |
| --- | --- | --- |
| 2 | ListaDoble, Pila de cinco elementos, Cola, ListaLRU con protección, ordenamientos estables, contadores | `test_bloque2_entidades.py`, `test_contadores_estructuras.py`, `test_regresiones_bloque1.py` |
| 3 | Actor, objetos/fábrica compartida, Trampa con rearme 300 si null, Enemigo, Jugador con cursor y vista ordenada | `test_bloque2_entidades.py`, integración del controlador |
| 1 | Contador HTTP, presupuesto y 429; persistencia de contenido y catálogo con versión individual | `test_datos_http.py`, `test_persistencia.py`, `test_cierre_bloque2.py` |
| 4 | Vecinas y vecinas de vecinas, lotes de hasta diez, fichas sin repetir, entidades dormidas | `test_controlador_red.py`, `test_cierre_bloque2.py` |

## Problemas y correcciones

1. **Reintentos:** la extracción de la cola podía perder un lote ante errores distintos de RuntimeError. Se mantiene el índice de pertenencia a la cola al desencolar y se restaura el lote desde la entrada común, incluso para llamadas directas. Una precarga fallida deja un mensaje y permite reintentar.
2. **Publicación parcial:** se construyen todas las entidades en listas temporales antes de asignarlas a las salas. Si falla la construcción o la persistencia, no se publican salas y se restaura la secuencia de la fábrica. Las fichas válidas y archivos individuales ya guardados pueden reutilizarse en el siguiente intento.
3. **Orden de IDs:** mezclar disco y fuente podía cambiar el orden de creación. Ahora se conserva el orden del lote solicitado, independientemente de dónde se obtiene cada sala.
4. **Versión:** los marcadores globales no prueban la versión de cada archivo. Cada contenido/ficha incluye `formato_cache`, `version`, `identificador` y `datos`. Solo se acepta la versión esperada por la instancia de persistencia. Los archivos antiguos sin sobre se consideran caché ausente.
5. **Datos inválidos:** se verifican listas, identidad, duplicación de salas/fichas solicitadas, tipos e instancias de cada sala, vida y fichas construibles. Una copia local mal formada se recupera desde la fuente; una copia con vida incompatible con la ficha se invalida para permitir el siguiente reintento.
6. **Rutas:** un validador compartido rechaza rutas, caracteres no portables y nombres reservados de Windows antes de acceder al archivo.
7. **Escritura:** se serializa primero, se usa un temporal único y cerrado en el mismo directorio, y luego `os.replace`. Se intenta retirar el temporal en `finally`. Un fallo de reemplazo conserva la copia anterior y se propaga.
8. **HTTP:** los errores de presupuesto y fin de reintentos incluyen la ruta GET. Se conserva el contador único del adaptador; los contadores del controlador no sustituyen el número real de intentos HTTP.

## Archivos de producción modificados

- `controlador/controlador_red.py`: validación, preparación del lote, reencolado y recuperación.
- `persistencia/cache_json.py`: nuevo helper para sobre, rutas y escritura individual.
- `persistencia/contenido.py`: sobre por sala e invalidación.
- `persistencia/catalogo.py`: sobre por ficha.
- `persistencia/esqueleto.py`, `persistencia/version.py`: reutilización del validador de identificadores.
- `adaptadores/datos_http.py`: contexto de ruta en errores.

Las estructuras, entidades y organización de carpetas se conservaron. `tests/test_persistencia.py` adapta una comprobación de cambio de versión: construye la persistencia con v2; cambiar un marcador no cambia el contrato v1 de un objeto ya creado. No se retiraron pruebas previas.

## Pruebas y reproducción

Base original: **289 aprobadas**. Se añadieron **56 casos**, total **345 aprobadas** en la ejecución final (3,15 s; tiempo de suite, no benchmark del juego). Antes de las correcciones, la primera tanda de 34 regresiones dio 29 fallos y 5 aprobadas, confirmando varios defectos reproducibles.

Desde la raíz del proyecto, con el intérprete virtual de PyCharm:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe main.py --offline --cache-dir "$env:TEMP\cripta-prueba-b2"
```

Ejecutar el segundo comando dos veces muestra primero fuente y después caché si la carpeta está vacía inicialmente. `main.py` continúa siendo el arranque del mapa de B1; la integración de B2 se prueba en pytest. No se presenta como un juego completo.

Cobertura nueva: reintentos por tres entradas y tres errores; mezcla de caché y fuente; versiones individuales; JSON corrupto y codificación inválida; nombres Windows; errores de serialización/reemplazo; temporales de dos escritores; contenido y catálogo incompletos/duplicados; fallo tardío sin consumir IDs; fallo en segundo guardado; recuperación LRU/disco; límite HTTP después de 429.

La prueba de escritores permite OSError en uno de los reemplazos simultáneos de Windows y exige al menos una escritura válida, documento final íntegro y temporales limpios. No garantiza que ambos escritores tengan éxito ni vuelve concurrente al modelo.

El entorno de ejecución emitió un aviso del intérprete sobre la ubicación de Python, pero los procesos terminaron con código 0. No se probó el servidor de juego en vivo: HTTP se verifica con respuestas simuladas. Las pruebas no demuestran ausencia absoluta de errores.

## Alcance pendiente explícito

- B3: servicio Catálogo con `_memoria: ListaLRU`, referencias activas y pendientes; reloj, efectos, historial, bitácora de partida, guardado binario y bucle. `ControladorRed._fichas` sigue siendo un índice `ArrayOrdenado` provisional sin límite de capacidad. Se prueba la composición LRU/disco, no se declara implementado el servicio completo.
- B3: determinismo de solicitudes/respuestas y costos de acciones con reloj. Las entidades cargadas por B2 permanecen dormidas.
- B4: benchmarks, umbral de ordenamiento medido, ciclo de 20 ms y reproducción final.
- Borradores 4.04, 4.05, 4.08 y 4.09: completos como propuesta técnica, pendientes de revisión humana por autores/revisores del plan. No contienen tiempos inventados.
- Escritura atómica por archivo; sin transacción entre archivos ni fsync/durabilidad garantizada. La limpieza de temporales es de mejor esfuerzo si el sistema impide borrar.

## Arquitectura e imágenes: después del bloque 3

No se crean carpetas en este PR. Tras terminar B3, migrar en una rama separada conservando pruebas: `src/cripta/data` para adaptadores/persistencia, `src/cripta/logic` para entidades/motor/servicios/TDAs, y `src/cripta/presentation/<pantalla>` para el MVC de cada ventana. Los modelos de pantalla observan o consultan la misma partida, sin duplicar el estado del juego.

Propuesta de recursos: `src/cripta/resources/images` con `salas`, `personajes`, `objetos` e `interfaz`. Son archivos gráficos estáticos; la vista los carga por rutas resueltas desde el paquete, no desde el directorio de ejecución de PyCharm. Partidas, caché y logs van en una ubicación escribible separada. No hacen falta base de datos ni backend/frontend separados para esta adaptación. La biblioteca gráfica y los formatos se decidirán con el equipo.

## Fuentes y revisión externa

Plan CRIPTA v4, páginas 7-9 (B2), 10-12 (B3) y 14-15 (mediciones); enunciado del proyecto; propuesta MVC previa; revisión de Claude `CRIPTA_revision_PR9_cierre_bloque2.pdf` como insumo de revisión, no como código ni autorización para reabrir PR9. Se contrastaron sus observaciones de reencolado, rutas Windows, pruebas de caché y temporales con el main actual.
