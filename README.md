# CRIPTA

CRIPTA es un juego de exploración por consola desarrollado para el curso de Estructuras de Datos II. El jugador recorre salas, combate enemigos, recoge objetos y busca la salida de una cripta. Cada acción tiene un costo de tiempo, y un reloj virtual organiza los turnos de los actores y los efectos del entorno.

El proyecto utiliza estructuras de datos propias para resolver problemas del juego: una agenda de eventos con heap mínimo, un inventario con lista doble, una caché LRU para el catálogo y un historial de cambios que permite deshacer acciones. Puede obtener los datos desde un servicio HTTP o trabajar con los archivos locales incluidos en el repositorio.

## Contenido

- [Instalación](#instalación)
- [Primera partida](#primera-partida)
- [Comandos del juego](#comandos-del-juego)
- [Opciones de ejecución](#opciones-de-ejecución)
- [Guardado y reproducción](#guardado-y-reproducción)
- [Datos, caché y solicitudes](#datos-caché-y-solicitudes)
- [Arquitectura](#arquitectura)
- [Pruebas y mediciones](#pruebas-y-mediciones)
- [Evidencias](#evidencias)
- [Problemas frecuentes](#problemas-frecuentes)
- [Estado del proyecto](#estado-del-proyecto)
- [Trabajo en el repositorio](#trabajo-en-el-repositorio)

## Instalación

El entorno de referencia es **Python 3.12**. La última validación local se realizó con Python 3.12.14 en Windows 11. Las dependencias están en [requirements.txt](requirements.txt): `requests` para el acceso HTTP y `pytest` para las pruebas. No hace falta configurar una base de datos.

Clona el repositorio y entra en su carpeta:

```console
git clone https://github.com/sruizvargas11-dotcom/proyecto-1-estructuras-de-datos-.git
cd proyecto-1-estructuras-de-datos-
```

En Windows, desde PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py --offline
```

Puedes usar el intérprete del entorno directamente, como en el ejemplo, sin activar scripts de PowerShell. Si ya tienes el entorno activado, los comandos siguientes funcionan con `python`.

En Linux o macOS, con Python 3.12 instalado:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py --offline
```

Ejecuta los comandos desde la raíz del repositorio. En PyCharm u otro editor, selecciona el intérprete de `.venv` y utiliza esa misma carpeta como directorio de trabajo.

## Primera partida

Para empezar con la cripta incluida y sin conexión:

```console
python main.py --offline --cripta cripta-01
```

Si omites `--cripta`, el programa muestra las disponibles. Puedes elegir una por número o identificador; Enter selecciona la primera. En modo offline solo se ofrecen criptas que tengan sus datos descargados.

La pantalla muestra la sala actual, las salidas, los enemigos, los objetos del suelo, las trampas, el inventario y el estado del jugador. También conserva los últimos 20 mensajes. Escribe `H` para consultar la ayuda o `Q` para terminar la sesión.

Se gana al llegar a la sala de salida y se pierde cuando la vida del jugador llega a cero. Para atravesar una puerta cerrada primero hay que abrirla con la llave adecuada. Los enemigos se activan al entrar en su sala, y su comportamiento puede ser de guardián, errante o rastreador.

### Cómo avanza el tiempo

El tiempo del juego es virtual: pensar un comando o esperar una descarga no consume turnos. Una acción válida programa la siguiente intervención del actor con este intervalo:

```text
intervalo = max(1, costo × 100 // velocidad)
```

Con velocidad 100, una acción de costo 100 tarda 100 unidades. Con velocidad 150, tarda 66. Los enemigos y los efectos que vencen durante ese intervalo se procesan antes de la próxima decisión del jugador. Si dos eventos coinciden en el tiempo, se respeta su secuencia de inserción.

Los comandos rechazados, como recoger con el inventario lleno o intentar abrir una puerta sin llave, no consumen tiempo virtual.

## Comandos del juego

Los comandos aceptan mayúsculas y minúsculas. Los índices empiezan en 1; si un comando admite `[n]` y no lo indicas, utiliza el primer elemento.

| Comando | Acción | Costo base |
| --- | --- | --- |
| `N`, `S`, `E`, `O` | Moverse en la dirección indicada | 100 |
| `A [n]` | Atacar al enemigo número n | 100 |
| `W` | Esperar | 100 |
| `R [n]` | Recoger el objeto número n del suelo | 25 |
| `T [n]` | Soltar el objeto número n del inventario | 25 |
| `U [n]` | Usar un objeto del inventario | 50 |
| `EQ [n]` | Equipar un arma o una armadura | 50 |
| `AB <dirección>` | Abrir una puerta con la llave correspondiente | 50 |
| `P` | Consumir un pergamino para deshacer el último intervalo | Sin costo adicional |
| `I` | Consultar el inventario en su orden real | Sin costo |
| `I peso`, `I valor`, `I nombre` | Mostrar una vista ordenada del inventario | Sin costo |
| `IS`, `IA`, `IC` | Avanzar, retroceder o consultar la selección del inventario | Sin costo |
| `G [ruta]` | Guardar la partida | Sin costo |
| `L [ruta]` | Cargar una partida compatible | Sin costo |
| `H` o `?` | Mostrar la ayuda | Sin costo |
| `Q` | Salir de la sesión | Sin costo |

`E` significa **este**; para equipar se utiliza `EQ`. Las vistas ordenadas conservan los números del inventario real, que son los que reciben `U`, `EQ` y `T`.

El pergamino puede revertir los cambios del jugador, enemigos y efectos incluidos en el último intervalo registrado. El historial conserva hasta cinco intervalos. El propio pergamino se consume de forma irreversible y no genera una nueva acción que pueda deshacerse.

## Opciones de ejecución

La ayuda disponible en el programa se consulta con:

```console
python main.py --help
```

| Opción | Uso |
| --- | --- |
| `--offline` | Leer los datos locales. Sin esta opción se usa HTTP. |
| `--offline-dir CARPETA` | Elegir otra carpeta de datos; requiere `--offline`. |
| `--cripta ID` | Elegir una cripta sin pasar por el menú. |
| `--solo-mapa` | Cargar y verificar el mapa sin iniciar una partida. Sin ID explícito usa la primera cripta. |
| `--cache-size N` | Fijar la capacidad de la LRU del catálogo; el valor predeterminado es 25. |
| `--cache-dir CARPETA` | Elegir dónde guardar la caché persistente. |
| `--hilos` | Precargar salas en segundo plano durante una partida nueva. |
| `--partidas-dir CARPETA` | Cambiar la carpeta de bitácoras y la ruta predeterminada del guardado. |
| `--replay LOG` | Reproducir las acciones de una bitácora sin pedir comandos. |
| `--silencioso` | Omitir el detalle de acciones durante el replay. |
| `--reportes ARCHIVO` | Cambiar el archivo del historial de reportes de red. |
| `--bench` | Ejecutar las mediciones de estructuras y persistencia. |

`--bench` y `--replay` son modos excluyentes. El benchmark utiliza sus propios datos y tamaños; las opciones de partida, como `--cache-size`, no configuran sus casos. La opción `--hilos` de `main.py` se aplica a partidas nuevas; los ensayos de replay con latencias se ejecutan mediante la herramienta de determinismo.

Ejemplos:

```console
python main.py --offline --cripta cripta-01 --hilos
python main.py --offline --solo-mapa
python main.py --offline --cache-size 50 --cache-dir partidas/cache-prueba
python main.py --offline --partidas-dir partidas/ensayo --reportes partidas/ensayo/reportes.txt
```

## Guardado y reproducción

### Guardar y cargar

Durante una partida, `G` guarda en `partidas/partida.sav` y `L` carga esa ruta. Puedes indicar otra, incluso entre comillas si contiene espacios:

```text
G partidas/mi_partida.sav
L partidas/mi_partida.sav
```

La carga exige que coincidan la cripta y las versiones de cripta y catálogo. Primero se reconstruye y valida una sesión independiente; después se sustituye la actual. Se conserva el historial reversible y se abre una nueva bitácora para continuar, sin truncar la anterior.

El formato de [PartidaBinaria](persistencia/PartidaBinaria.py) contiene un encabezado, un índice por identificador de sala, el estado global y los bloques de cada sala. Los bloques usan JSON dentro del contenedor binario. El índice permite localizar una sala mediante búsqueda binaria en disco, sin leer los demás bloques. La sesión completa conserva las referencias entre entidades, eventos y deltas.

### Reproducir una bitácora

Cada partida nueva genera automáticamente una semilla y escribe un log en:

```text
partidas/bitacoras/<cripta>_<semilla>.log
```

El log contiene las versiones, la semilla y las acciones aceptadas con su tiempo virtual. Al terminar de forma controlada, agrega el resultado y las líneas del estado observable que utiliza el replay para comparar la partida.

Para reproducirlo, sustituye `ARCHIVO.log` por una bitácora que exista:

```console
python main.py --offline --replay partidas/bitacoras/ARCHIVO.log
python main.py --offline --replay partidas/bitacoras/ARCHIVO.log --silencioso
```

La reproducción comprueba las versiones antes de ejecutar acciones. Luego valida sus tiempos, detecta rechazos inesperados y compara el estado final con el registrado.

| Código de salida | Significado |
| --- | --- |
| `0` | Ejecución terminada sin errores. En replay, el estado final se verifica solo si el log tiene cierre. |
| `1` | Error al cargar los datos o ejecutar la sesión. |
| `2` | Versiones incompatibles durante el replay; argparse también usa este código para argumentos inválidos. |
| `3` | El replay difiere de las acciones, tiempos o estado registrados. |

Si el log no tiene cierre, el programa informa que reprodujo las acciones pero no pudo verificar el estado final. El estado comparado es el que expone [estado_final.py](controlador/estado_final.py), no una serialización de todos los detalles internos del motor.

## Datos, caché y solicitudes

[FuenteDeDatos](adaptadores/fuente_datos.py) define las consultas comunes a las fuentes: listado de criptas, datos generales, mapa paginado, contenido de salas, catálogo y versiones.

- **DatosHTTP** consulta el servicio configurado en `adaptadores/datos_http.py`. Identifica al cliente mediante `X-Cripta-Client-Id`, cuenta los intentos y respeta el presupuesto de solicitudes recibido para la cripta. También limita los reintentos ante respuestas 429.
- **DatosOffline** responde a las mismas consultas leyendo archivos JSON. La ruta predeterminada es `datos_offline/`.
- **DatosSimulado** envuelve una fuente y añade demoras reproducibles para las pruebas. No altera el reloj virtual ni el generador aleatorio de la partida.

La carga distingue el mapa de las salas de su contenido. El contenido y las fichas se solicitan en lotes de hasta 10. La precarga anticipa salas vecinas y vecinas de vecinas; un buffer conserva el orden de incorporación aunque las respuestas lleguen en otro orden.

### Archivos de datos y caché

Los datos offline se organizan de esta forma:

```text
datos_offline/
├── criptas.json
├── catalogo_version.json
├── catalogo/                    # Una ficha JSON por tipo
└── cripta-01/
    ├── general.json
    ├── version.json
    ├── salas_p1.json            # Más páginas cuando la cripta las necesite
    └── contenido/              # Un JSON por sala
```

La caché persistente se guarda por defecto en `partidas/cache/`. Las versiones de cripta y catálogo determinan si se puede reutilizar. En memoria, la LRU conserva las fichas consultadas recientemente y protege las que están en uso. Si todas las entradas están protegidas, no se puede liberar espacio retirando una de ellas.

`--partidas-dir` cambia la ubicación de guardados y bitácoras. Para mover también la caché y los reportes, usa explícitamente `--cache-dir` y `--reportes`.

### Descargar y comparar datos

Estas herramientas consultan el servicio real y consumen solicitudes:

```console
python -m herramientas.descargar_offline cripta-01
python -m herramientas.comparar_online_offline cripta-01
```

La descarga escribe o actualiza los archivos correspondientes en `datos_offline/`. La comparación revisa los datos locales frente al servicio e informa de las diferencias. `verificar.py` sirve como diagnóstico manual del acceso al API; no forma parte de la suite offline.

### Reporte de red

Al terminar una partida o un replay, se muestra un reporte y se conserva en `partidas/reportes_red.txt`. Incluye solicitudes realizadas, presupuesto, uso de la caché, aciertos y fallos de la LRU y esperas de precarga. Una pila propia conserva los 50 reportes más recientes, con el último al principio.

Actualmente `--bench` imprime sus tablas de rendimiento y termina sin emitir este reporte de red.

## Arquitectura

La consola recibe los comandos; el controlador los valida y coordina el trabajo del modelo. El modelo mantiene el mundo, las entidades, el reloj y el historial. Los adaptadores resuelven el acceso a los datos y la persistencia se encarga de los archivos.

```text
main.py
├── vista/          Entrada por consola y presentación del estado
├── controlador/    Acciones, carga de datos, replay, guardado y reportes
├── modelo/         Mundo, entidades, reloj, efectos e historial
├── estructuras/    Implementaciones propias de los tipos de datos
├── adaptadores/    Fuentes HTTP, offline y con latencia simulada
├── persistencia/   Caché versionada y formato binario de partida
├── bench/          Casos de medición y calibración del ordenamiento
├── herramientas/   Descarga, comparación y ensayos reproducibles
├── tests/          Pruebas unitarias, de integración y de regresión
├── datos_offline/  Datos incluidos para jugar sin conexión
└── docs/           Decisiones técnicas, informes y evidencias
```

### Estructuras y dónde se usan

| Estructura | Uso principal |
| --- | --- |
| Vector dinámico | Colecciones de salas y datos; base de otras estructuras. |
| Lista simple | Salidas, objetos del suelo, enemigos y trampas de una sala. |
| Lista doble | Inventario con cursor y soporte de la LRU y la pila. |
| Pila limitada | Historial de retroceso y reportes recientes. |
| Cola | Salas pendientes de precarga. |
| Array circular | Últimos 20 mensajes de la consola. |
| Array ordenado | Índices de claves y posiciones, incluido el guardado. |
| Heap mínimo | Agenda de eventos ordenada por tiempo y secuencia. |
| Lista LRU | Fichas del catálogo con protección por referencias activas. |
| InsertionSort y MergeSort | Ordenamiento de vectores e inventario. |

Las estructuras son implementaciones propias. Las listas de Python se usan como almacenamiento cuando corresponde; los diccionarios de transporte JSON no sustituyen a los TDAs. Los ordenamientos del proyecto no delegan en `sorted()` ni `list.sort()`, y la agenda no utiliza `heapq`.

### Reloj, efectos y retroceso

El controlador consulta el evento mínimo, ejecuta la acción del jugador, del enemigo o del entorno y programa la siguiente intervención cuando corresponde. Cancelar un evento marca su entrada como inválida; el heap la retira al llegar a la raíz.

Los efectos incluyen veneno, regeneración, cambios temporales de velocidad, antorchas, rearme de trampas y cierre de puertas. El historial registra cambios puntuales mediante deltas, en lugar de copiar el estado completo en cada acción. El reloj y las entidades comparten el mismo historial, y las decisiones aleatorias utilizan el generador de la partida.

El detalle del ciclo y de las reglas reversibles está en [ROL3_BLOQUE3.md](docs/ROL3_BLOQUE3.md).

## Pruebas y mediciones

### Suite automatizada

```console
python -m pytest -q
```

La suite bloquea las solicitudes HTTP reales y usa datos locales, fuentes simuladas y carpetas temporales. Incluye pruebas de estructuras, validación de datos, persistencia, combate, efectos, inventario, retroceso, comandos, caché, replay y determinismo.

Para ejecutar solo las pruebas del cierre del rol 2:

```console
python -m pytest tests/test_rol2_bloque4.py -q
```

La validación local del 16 de octubre de 2026 completó **665 pruebas**. Ese resultado corresponde al código y al entorno de esa revisión, no sustituye la ejecución de las pruebas después de hacer cambios.

### Benchmarks

```console
python main.py --bench
```

Se comparan la agenda con heap y búsqueda lineal, la LRU y una lista plana, la recuperación de fichas desde memoria y disco, las operaciones de inventario, el retroceso con deltas y copias, los ordenamientos y el guardado binario frente a JSON.

Las alternativas pueden tener condiciones distintas: por ejemplo, la lista plana del ensayo de caché conserva todas las claves, mientras que la LRU tiene capacidad limitada. Hay que leer los resultados junto con la configuración del caso, especialmente antes de comparar aciertos o concluir que una estructura es más rápida.

Para medir los algoritmos reales de ordenamiento y guardar el resultado:

```console
python -m bench.calibrar_ordenamiento --salida docs/evidencia/ordenamiento-local.json
```

Esta calibración utiliza datos aleatorios y casi ordenados, semillas fijas, calentamiento y siete repeticiones. El umbral actual es **50**. Su justificación y sus límites están en [la decisión de ordenamiento](docs/decisiones/4.09.txt).

### Determinismo con latencias

```console
python -m herramientas.verificar_determinismo --cripta cripta-01 --guion docs/evidencia/guion-rol2.json --ensayo --salida docs/evidencia/determinismo-local.json
```

La herramienta ejecuta el mismo guion en modo offline y con diez patrones de latencia, cada uno con una caché vacía. Después reproduce cada log con otro patrón. Compara los bytes del estado, los mensajes y los logs entre ejecuciones equivalentes, y guarda sumas FNV-1a de 64 bits para facilitar su revisión.

`--ensayo` fija la vida máxima en 300 únicamente en memoria, tanto en la partida como en el replay, para completar la ruta de prueba. No modifica los JSON oficiales. Para probar otros datos, usa `--offline-dir CARPETA`, el identificador correspondiente y un guion adecuado; omite `--ensayo` si quieres conservar sus estadísticas originales.

Los mensajes de la partida y del replay se comparan con sus respectivas referencias. Pueden diferir entre esos dos grupos porque la bitácora solo registra las acciones aceptadas y omite los comandos rechazados.

### Cripta de práctica

Para probar comandos con estadísticas reforzadas y objetos adicionales:

```console
python -m herramientas.generar_cripta_prueba datos_ensayo
python main.py --offline --offline-dir datos_ensayo --cripta cripta-prueba
```

El generador exige una carpeta nueva. Copia los datos a esa ubicación y prepara la cripta de ensayo sin modificar `datos_offline/`.

## Evidencias

[docs/evidencia](docs/evidencia/) conserva resultados de mediciones y el guion que permite repetir una partida. Los JSON son archivos de datos; las explicaciones y conclusiones están en [docs/decisiones](docs/decisiones/).

| Archivo | Qué contiene y de dónde sale |
| --- | --- |
| `2026-10-16-ordenamiento.json` | Primera medición de InsertionSort y MergeSort sobre Vector, generada por `bench.calibrar_ordenamiento`. |
| `2026-10-16-ordenamiento-confirmacion.json` | Segunda medición, que agrega los tamaños 60 y 75 para precisar el cruce entre algoritmos. |
| `2026-10-16-determinismo.json` | Resultados, contadores y sumas de verificación de las once partidas y sus replays, generados por `herramientas.verificar_determinismo`. |
| `2026-10-16-catalogo-inventario.json` | Resultados de `bench.casos.lru.correr()` y `bench.casos.inventario.correr()`, guardados mediante un script puntual durante la revisión. `--bench` vuelve a medir esos casos, pero no exporta este JSON automáticamente. |
| `guion-rol2.json` | Entrada del ensayo: lista de comandos. No es un resultado de rendimiento. |

Por ejemplo, un registro de ordenamiento con `n: 50` y `ms: 0.299` indica una mediana de aproximadamente 0.299 milisegundos por ordenamiento de 50 elementos. Las semillas permiten repetir las entradas, pero los tiempos pueden cambiar según la máquina y su carga.

El informe [ROL2_BLOQUE4.md](docs/ROL2_BLOQUE4.md) relaciona las pruebas con los casos borde del plan. Las decisiones [4.3](docs/decisiones/4.03.txt), [4.5](docs/decisiones/4.05.txt) y [4.9](docs/decisiones/4.09.txt) explican el catálogo, el inventario y el ordenamiento. [DECISIONES.md](docs/DECISIONES.md) identifica el documento y sus autores; las secciones detalladas se mantienen por separado.

## Problemas frecuentes

| Situación | Qué revisar |
| --- | --- |
| Python no encuentra `requests` o `pytest` | Instala `requirements.txt` con el mismo intérprete que ejecuta el proyecto. |
| No aparece una cripta en modo offline | Comprueba que exista su carpeta y `general.json`, o utiliza `--offline-dir` con los datos correctos. |
| Falta una sala o una ficha local | Revisa el archivo indicado por el error. Si vas a descargar de nuevo, la herramienta actualizará los datos locales. |
| El servicio está ocupado o no responde | Revisa la conexión y el mensaje HTTP. Para trabajar sin depender del servicio, usa `--offline`. |
| Se agotó el presupuesto | Consulta el reporte de solicitudes. Revisa la reutilización de caché y las versiones antes de repetir la partida. |
| El guardado o replay tiene otra versión | Usa los datos de cripta y catálogo con los que se creó; modificar el encabezado no restaura la compatibilidad. |
| Una ficha no cabe en la LRU | Revisa si todas las entradas están protegidas y si la capacidad elegida es suficiente. |
| Las tildes se ven mal al redirigir la salida en PowerShell | Ejecuta `$env:PYTHONIOENCODING='utf-8'` antes del comando. |

## Estado del proyecto

La versión actual permite jugar por consola, guardar y cargar una sesión, reproducir bitácoras y ejecutar los benchmarks. También incluye pruebas de los ocho casos borde del rol 2 y ensayos de determinismo con latencias.

Quedan aspectos del cierre del plan que deben validarse o integrarse con el equipo:

- Probar una partida completa y los casos borde con una cripta desconocida del servicio. La validación local no equivale a esa prueba.
- Completar la medición integral del ciclo y del escalado x1, x10 y x50. Los benchmarks actuales no demuestran por sí solos que el máximo de cada ciclo sea menor de 20 ms.
- Integrar el reporte final de red en `--bench`.
- Completar la tabla persistente de puntajes. Actualmente se muestra el resumen de la partida, pero no hay una tabla de clasificación guardada.
- Revisar y consolidar entre los roles las secciones del Documento de Decisiones.

La calibración de ordenamiento llega hasta 500 elementos y no cubre comparadores costosos. Los tiempos publicados corresponden al equipo de la medición. El entorno probado es Windows 11 con Python 3.12.14; las instrucciones para otros sistemas no representan una validación adicional de la suite en ellos.

## Trabajo en el repositorio

Para desarrollar una función o corregir un error:

1. Crea una rama para el cambio y revisa las decisiones del módulo afectado.
2. Mantén las reglas del juego en el modelo, la coordinación en el controlador y la entrada/salida en la vista o los adaptadores.
3. Añade una prueba cuando cambie el comportamiento o se corrija un caso que pueda volver a fallar.
4. Ejecuta `python -m pytest -q` y comprueba los comandos afectados antes de integrar el cambio.
5. Si modifica el rendimiento, repite la medición y documenta sus condiciones. Si cambia el uso del programa, actualiza este README.

Los comentarios deben explicar una regla, una limitación o una decisión que no sea evidente al leer el código. Las notas históricas sobre lo que se agregó o corrigió pertenecen a la descripción del cambio, no a instrucciones permanentes dentro del módulo.

Según el [Documento de Decisiones](docs/DECISIONES.md), el equipo está formado por Jose Daniel Morales Moreno, Sebastián Ruiz Vargas, Daniel Centeno y Jose Fabio.
