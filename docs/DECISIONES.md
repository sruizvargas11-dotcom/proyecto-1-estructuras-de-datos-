# Documento de decisiones técnicas
## CRIPTA


**Curso:** Estructuras de datos

**Tipo de documento:** Registro de decisiones tomadas en el proyecto.

**Fecha:** 18 de octubre de 2026.

## Autores

- Jose Daniel Morales Moreno
- Sebastián Ruiz Vargas
- Daniel Centeno Gutiérrez
- Jose Fabio Barrantes Ramírez

## Repositorio

https://github.com/sruizvargas11-dotcom/proyecto-1-estructuras-de-datos-

## Resumen

Este documento reúne las decisiones técnicas que tomamos para resolver los problemas de la sección 4 del enunciado. Para cada problema se explica qué operaciones ejecuta realmente el juego y con qué frecuencia, qué alternativas consideramos y por qué se descartaron, qué estructura y estrategia implementamos, su complejidad, la evidencia que la respalda (mediciones con --bench y pruebas) y los límites en los que la decisión deja de ser apropiada, según la sección 8 del enunciado. Cada entrada la redacta un rol y la revisa otro, y sirve como base para explicar y defender cualquier decisión durante la revisión del proyecto.

### Problemas a resolver

- **4.1 Agenda de eventos:** el juego avanza por tiempo virtual, no por turnos; las acciones del jugador, de los enemigos y de los efectos tienen que ejecutarse en orden de tiempo, y poder cancelarse o reprogramarse sin recorrer toda la agenda.
- **4.2 Precarga de contenido:** el jugador nunca puede entrar a una sala cuyo contenido no se conoce; cada solicitud al API tarda unos 400 ms y gasta presupuesto, y el orden en que llegan las respuestas no debe cambiar la partida.
- **4.3 Resolución de referencias del catálogo:** cada tipo_id del contenido de una sala debe convertirse en su ficha reutilizando las que ya están en memoria, sin descargarlas otra vez y sin retirar las que siguen en uso.
- **4.4 Reutilización y caché persistente:** el contenido y las fichas ya descargados deben reutilizarse entre ejecuciones, detectando archivos viejos, dañados o de otra versión.
- **4.5 Inventario:** el jugador recoge, equipa, suelta y recorre objetos con un cursor, respetando la capacidad de la cripta y sin dejar el inventario incoherente cuando una acción se rechaza o se revierte.
- **4.6 Retroceso e historial reversible:** el pergamino deshace hasta cinco acciones del jugador, incluidos los eventos de enemigos y efectos ocurridos entre ellas, sin guardar copias completas del estado.
- **4.7 Rastro del jugador:** cada sala recuerda la última visita del jugador para que los enemigos rastreadores lo sigan eligiendo solo entre salas vecinas.
- **4.8 Bitácora en pantalla:** la interfaz muestra solo los últimos 20 mensajes, con memoria constante y sin desplazar los 19 anteriores al agregar uno.
- **4.9 Ordenamiento:** el juego ordena vistas del inventario, la tabla de puntajes y listas auxiliares, eligiendo el algoritmo según propiedades medidas de los datos y sin alterar el orden real.
- **4.10 Guardado binario:** la partida se guarda en un formato binario propio que permite continuarla exactamente, recuperar una sala sin leer todo el archivo y detectar versiones incompatibles.
- **4.11 Bitácora de partida y reproducción:** cada acción del jugador se registra para reproducir la partida con --replay, el mecanismo principal para reportar y repetir errores durante la evaluación.
- **4.12 Efectos temporales:** veneno, modificadores de velocidad, antorcha y regeneración deben funcionar con el tiempo virtual, poder cancelarse y deshacerse con el historial.

---

## 4.1 Agenda de eventos

*Redacta: Rol 3 · Revisa: Rol 2*

### Problema

El juego no avanza por turnos fijos sino por tiempo virtual entero. La agenda decide quién actúa y cuándo, y tiene que:

- Ejecutar las acciones de los actores (jugador y enemigos) y de los efectos en orden de tiempo y, ante un empate, en orden de secuencia.
- Cancelar un evento sin recorrer toda la agenda, por ejemplo cuando un actor muere.
- Reprogramar la acción pendiente de un actor cuando cambia su velocidad.
- Restaurar eventos cuando el jugador deshace una acción con el pergamino.

El momento de la siguiente acción se calcula como `tiempo = ahora + max(1, costo · 100 // velocidad)`.

Frecuencia medida: en `bench.ciclo` (escala 1: 200 salas, 200 enemigos activos y 200 efectos recurrentes), cada repetición de 200 decisiones del jugador ejecuta 40 000 turnos de enemigos y 20 000 efectos.

### Alternativas consideradas

| Alternativa | Insertar | Obtener el siguiente evento | Resultado |
| --- | --- | --- | --- |
| Vector sin ordenar | Barato | O(n): hay que recorrer todo | Descartada |
| Vector ordenado | O(n) por desplazamientos | O(1) | Descartada |
| Heap propio | O(log n) | O(log n) | **Elegida**: equilibra inserción y extracción; se conserva la implementación del compañero |

### Decisión

- `HeapMinimo` sobre `Vector`, ordenado por la clave `(tiempo, secuencia)`.
- **Cancelación diferida:** cancelar solo marca la entrada como inválida. Las entradas canceladas se limpian explícitamente antes de consultar el mínimo, que es una consulta O(1).
- El `Reloj` usa un único `random.Random(semilla)` compartido por todo el juego.
- **Reprogramar** cancela la entrada y crea otra con una secuencia nueva. **Deshacer** reintegra el mismo handle con su misma secuencia, incluso si ya había salido del heap.
- Cada actor guarda sus propios efectos pendientes, así su muerte los cancela sin buscar en la agenda.
- Los eventos son objetos `EjecutorEvento` (`modelo/ejecutor_evento.py`) con datos explícitos (tipo, dueño y parámetro), no funciones de Python. Por eso la agenda se puede guardar y reconstruir al cargar una partida (4.10).

### Análisis de complejidad

| Operación | Costo |
| --- | --- |
| Consultar la raíz | O(1) |
| Insertar | O(log n) amortizado (por el redimensionamiento del Vector) |
| Extraer sin cancelados | O(log n) |
| Limpiar k cancelados | O(k log n) |
| Cancelar | O(1) |
| Muerte de un actor | O(e), con e = efectos del propio actor |

Las comparaciones y operaciones quedan contadas, y las restauraciones se cuentan aparte de las inserciones nuevas.

### Evidencia empírica

**Pruebas.** `tests/test_rol3_bloque3.py` (39 pruebas) verifica el ejemplo de la sección 2.13 del enunciado (jugador 0, rata 66, jugador 100, jugador 125, rata 132, jugador 175), empates, reprogramación, límites, azar y cancelación. Las pruebas del historial comprueban que se reintegran eventos que ya habían salido del heap.

**Bench (`--bench`, caso `agenda_eventos`).** Se hacen 20 001 extracciones del mínimo, cada una seguida de una inserción, con el heap propio y con una lista que busca el mínimo recorriéndola completa.

| Eventos en la agenda | HeapMinimo (usado) | Lista lineal (descartada) |
| --- | --- | --- |
| 100 | 141.922 ms | 74.367 ms |
| 500 | 149.095 ms | 358.933 ms |
| 1 000 | 153.437 ms | 832.593 ms |
| 5 000 | 179.814 ms | 4 000.270 ms |

- Con 100 eventos la lista lineal es más rápida, pero desde 500 gana el heap. Con 5 000 el heap es 22 veces más rápido.
- El tiempo del heap casi no cambia con el tamaño (de 142 a 180 ms), mientras que el de la lista crece con cada evento agregado.

**Bench (`--bench`, caso `proximos_turnos`).** El panel de próximos turnos consulta los 5 siguientes eventos 200 veces. `vista_ordenada(5)` los obtiene sin modificar el heap; la alternativa copia todas las entradas válidas y las ordena.

| Eventos en la agenda | vista_ordenada(5) (usada) | Copiar y ordenar (descartada) |
| --- | --- | --- |
| 100 | 6.120 ms | 231.377 ms |
| 500 | 6.114 ms | 1 471.675 ms |
| 1 000 | 6.297 ms | 3 222.474 ms |
| 5 000 | 5.772 ms | 21 472.598 ms |

**Ciclo de 20 ms (sección 5.2 del enunciado).** `bench.ciclo` con escala 1 y 1 000 ciclos dio: mínimo 4.171 ms, mediana 8.706 ms, percentil 95 13.196 ms y máximo 35.496 ms. El ciclo típico usa menos de la mitad del límite, pero al menos un ciclo superó los 20 ms.

Equipo: Windows 10 (10.0.19045), Intel Core i7-8750H @ 2.20 GHz (12 núcleos lógicos), 8 GB de RAM, Python 3.14.6. Fecha: 18-10-2026. Cada medición del `--bench` es la mediana de 5 repeticiones, más 1 de calentamiento que no se cuenta.

**Comandos para verificar** (PowerShell, desde la raíz del repositorio):

```powershell
.\venv\Scripts\python.exe -m pytest tests\test_rol3_bloque3.py tests\test_historial_bloque3.py -v
.\venv\Scripts\python.exe main.py --bench
.\venv\Scripts\python.exe -m bench.ciclo --escalas 1 --ciclos 1000 --salida $env:TEMP\ciclos.json
```

### Límites conocidos

- Las entradas canceladas siguen dentro del heap hasta que llegan a la raíz. Con muchas reprogramaciones pueden acumularse, y no se midió cuánto.
- Con agendas pequeñas (100 eventos) una lista lineal es más rápida que el heap.
- No se deben modificar directamente las claves ni la validez de los handles del reloj: hay que usar su API.
- Un callback recurrente no debe reprogramarse indefinidamente en el mismo instante.
- El máximo del ciclo superó los 20 ms en la medición de escala 1, aunque la mediana y el percentil 95 quedaron por debajo.

---

## 4.2 Precarga de contenido

*Redacta: Rol 4 · Revisa: Rol 1*

### Problema

El juego tiene que tener en memoria el contenido de una sala (enemigos, objetos y trampas) antes de que el jugador entre en ella. También decide qué salas pedir y cuándo, con estas restricciones:

- Cada solicitud tarda unos 400 ms y gasta `presupuesto_solicitudes`, pero pedir 1 sala cuesta casi lo mismo que pedir 10.
- No se puede pedir dos veces la misma sala.
- Las respuestas tienen que entrar al modelo en un orden que no dependa de cuándo llegan, para que la partida dependa solo de la versión de la cripta, la semilla y las acciones.

Operaciones que ejecuta el programa (todas en `controlador/controlador_red.py`, clase `ControladorRed`):

| Operación | Cuándo | Qué hace |
| --- | --- | --- |
| `asegurar_entrada` → `garantizar_contenido` | En cada movimiento | Si la sala destino ya está cargada no pide nada; si no, espera en tiempo real sin mover el reloj virtual. |
| `planificar_precarga` | Después de cada movimiento | Encola las vecinas directas y las vecinas de esas vecinas que todavía no se han pedido. |
| `procesar_cola` | Después de cada movimiento | Envía un lote de hasta 10 salas. |
| `incorporar_listas` | Al inicio de cada turno del jugador | Incorpora las respuestas que ya llegaron, en orden de número de solicitud. |
| Consulta de pertenencia | Dentro de las anteriores | Revisa en un `Vector` si una sala ya está encolada, pedida o cargada. |

Frecuencia medida (partida simulada con la estrategia elegida, grillas de n salas y camino aleatorio con semilla 42):

| Salas | Movimientos | Consultas por movimiento | Elementos revisados por consulta | Comparaciones por movimiento | Cola máxima | Lotes | Salas por lote |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 25 | 60 | 28.2 | 5.7 | 160 | 3 | 3 | 8.3 |
| 100 | 200 | 35.7 | 20.9 | 748 | 3 | 10 | 10.0 |
| 400 | 600 | 36.9 | 68.7 | 2 532 | 4 | 35 | 10.0 |

Las consultas por movimiento casi no cambian (28 a 37), pero cada consulta revisa más elementos a medida que hay más salas pedidas. La cola nunca pasa de 4 salas y, desde 100 salas, todos los lotes salen llenos.

### Alternativas consideradas

**Estrategia de precarga**

| Estrategia | Ventaja | Por qué se descarta |
| --- | --- | --- |
| Sin precarga (pedir cada sala al entrar) | La más simple; nunca pide salas que no se visitan | Cada sala nueva implica unos 400 ms de espera en la puerta, y el enunciado pide que la estrategia normal evite esa espera. |
| Solo vecinas directas (1 nivel) | Evita la espera del siguiente movimiento | Si el jugador se mueve dos veces antes de que llegue el lote (por ejemplo, con `--hilos`), la sala a dos pasos puede no estar lista. Además genera más lotes pequeños. |
| Mapa completo al inicio | Es la que menos solicitudes de contenido hace | Todas las solicitudes ocurren antes de la primera acción, carga salas que nunca se visitan y en una cripta grande puede gastar el presupuesto antes de empezar a jugar. El costo crece con la cripta, no con lo que el jugador recorre. |
| Solo relleno BFS (llenar un lote con las salas más cercanas cuando alguna vecina directa no se ha pedido) | Hace casi las mismas solicitudes que la elegida y carga un poco menos | No adelanta la sala a dos pasos cuando las vecinas directas ya fueron pedidas: tiene el mismo problema que 1 nivel. Esa ventaja depende de la latencia y el bench no la mide. |
| **Vecinas directas + vecinas de vecinas (2 niveles), con lote lleno** | Adelanta todo lo alcanzable en dos movimientos sin pedir salas lejanas | **Elegida** |

**Estructuras**

- **Cola de pendientes:** `Cola` propia sobre nodos enlazados contra `list` con `pop(0)`. `pop(0)` desplaza todos los elementos (O(n)); la `Cola` desencola en O(1) con punteros al frente y al final. Además, la sección 7 del enunciado exige implementar las estructuras propias.
- **Pertenencia ("¿ya fue pedida?"):** `Vector` con búsqueda lineal contra `ArrayOrdenado` con búsqueda binaria. El `ArrayOrdenado` busca en O(log n) pero inserta en O(n) por desplazamientos; el `Vector` agrega en O(1) amortizado y busca en O(n). La diferencia se midió (ver evidencia).

### Decisión

**Estrategia: dos niveles con lote lleno.** Se envía un lote de hasta 10 salas por turno y, si le sobra espacio, se completa con salas cercanas todavía no pedidas, porque el costo es el mismo con 1 que con 10 (sección 3.4 del enunciado).

- `planificar_precarga` encola las vecinas directas y las vecinas de esas vecinas que todavía no se han pedido. No envía nada.
- `procesar_cola` (con `_completar_lote`) saca de la cola hasta 10 salas no pedidas. Si el lote queda con entre 1 y 9 salas, `_rellenar_cercanas` lo completa hasta 10 con un recorrido en anchura (BFS) desde las salas del lote. Si la cola no aporta ninguna sala, no se envía solicitud.
- Si el jugador intenta entrar a una sala que no está lista, `garantizar_contenido` arma un lote que empieza con esa sala y lo completa igual: primero con la cola y después con salas cercanas.
- El BFS recorre las salidas en el orden del esqueleto, así que las salas agregadas dependen solo del estado del juego, no del orden de las respuestas HTTP.
- El relleno se activa con `completar_lotes=True`: `inicio_partida.py` lo activa al crear la partida y `guardado.py` lo conserva al cargar. Desactivado (valor por defecto de `ControladorRed`), el controlador solo hace la precarga de dos niveles; el bench usa esa opción para comparar.

**Estructuras en `ControladorRed`**

| Campo | Estructura | Para qué sirve |
| --- | --- | --- |
| `_pendientes` | `Cola`, sin límite | Salas por pedir, en orden de prioridad. Las vecinas directas se encolan primero y salen en el primer lote. |
| `_encoladas` | `Vector` | Salas que están en la cola; evita encolar dos veces la misma. |
| `_solicitadas` | `Vector` | Salas pedidas o en camino; evita pedirlas dos veces. Si una solicitud falla, sus salas vuelven a la cola. |
| `_incorporadas` | `Vector` | Salas cuyo contenido ya está en el modelo. |
| `_buffer` | `BufferReordenamiento` (Vector de ranuras numeradas) | Guarda cada respuesta hasta que llegaron todas las de número menor. |
| `_registro` | `Vector` | `(número, sub, clase, ids, en_red)` de cada solicitud, para verificar que el mismo juego genera la misma secuencia. |
| `frontera` / `vistas` | `Cola` / `ArrayOrdenado`, temporales | Las usa `_rellenar_cercanas` en cada lote incompleto: salas por expandir del BFS y salas ya visitadas. |

**Ciclo de una solicitud**

1. **Decidir:** en el hilo principal y solo con el estado del juego (posición, esqueleto y lo ya pedido), nunca con respuestas ya llegadas. Antes de pedir a la red se lee del disco lo vigente.
2. **Numerar:** el lote recibe el siguiente número del buffer, aunque todo venga del disco, para que el orden de incorporación no dependa de la caché.
3. **Enviar:** con `DespachoInmediato` la solicitud se hace en el acto; con `DespachoEnHilos` (`--hilos`) viaja en otro hilo y la respuesta se entrega al buffer.
4. **Incorporar:** en puntos fijos y en orden estricto de número. Las fichas del lote se resuelven juntas (subsolicitudes de catálogo n.1, n.2…), se construyen todas las entidades y se publican todas o ninguna. Los enemigos quedan dormidos: incorporar no activa enemigos ni programa eventos (sección 2.4 del enunciado).

**Integración con el juego**

- `inicio_partida.py` planifica la precarga de la sala inicial antes de garantizarla, así la sala inicial y sus vecinas viajan en una sola solicitud.
- `controlador_juego.py` llama a `incorporar_listas()` al inicio de cada turno; a `asegurar_entrada()` al intentar moverse (si falla, el movimiento se rechaza con un mensaje y no se registra); y a `planificar_precarga(destino)` + `procesar_cola()` después de moverse.

**Fallos y presupuesto**

- Una precarga que falla no detiene el juego: sus salas vuelven a la cola y el error queda en `ultimo_error`.
- `garantizar_contenido` reintenta una vez solo si el error no es de datos inválidos y la fuente sigue dentro del presupuesto. Espera como máximo 120 s de tiempo real; si aun así falla, el movimiento se rechaza.
- No se reservan solicitudes para `garantizar_contenido`: la precarga puede gastar el presupuesto que después necesite un movimiento.

### Análisis de complejidad

Notación: S = salas pedidas, I = salas incorporadas, E = tamaño de la cola, p = solicitudes en vuelo.

| Operación | Costo |
| --- | --- |
| Consulta de pertenencia en `Vector` (la más frecuente) | O(n) sobre el Vector consultado (S, I o E) |
| `garantizar_contenido` con la sala ya cargada | O(I) |
| `planificar_precarga` | O(16 · (E + S)): hasta 4 vecinas directas y 12 de segundo nivel, cada una con su consulta |
| `procesar_cola` | O(10 · (E + S)), más O(10) para enviar el lote y las lecturas de disco |
| `incorporar_listas` sin respuestas pendientes | O(1) |
| `tomar_siguiente` del buffer | O(1) amortizado (compacta las ranuras cada 32 consumidas) |
| `entregar` / buscar la solicitud de una sala en vuelo | O(p) / O(10 · p); p suele ser 0 o 1 |
| Espacio | O(S + número de solicitudes) |

### Evidencia empírica

Medido con `bench/bench_precarga.py`; resultados en `docs/evidencia/2026-10-18-precarga.json`.

- **Equipo:** Windows 10 (10.0.19045), Intel Core i7-8750H @ 2.20 GHz (12 núcleos lógicos), 8 GB de RAM, Python 3.14.6. Fecha: 18-10-2026.
- **Repeticiones:** 5 por medición, más 1 de calentamiento que no se cuenta; se reporta la mediana.
- **Condiciones:** grillas sintéticas de n salas (1 enemigo, 1 objeto y 1 trampa por sala) y un camino aleatorio con semilla 42 de 60, 200 y 600 movimientos (en ese camino se visitan 21, 69 y 211 salas). La fuente responde con latencia 0: la mediana mide el trabajo local de toda la partida simulada, no la red. El costo de red se estima como solicitudes × 0.4 s (sección 3.4 del enunciado).
- **Esperas:** veces que el jugador entra a una sala cuyo contenido todavía no está cargado.

**Estrategias de precarga** (la elegida está en negrita)

| Salas | Estrategia | Mediana | Solicitudes | Esperas | Salas cargadas |
| --- | --- | --- | --- | --- | --- |
| 25 | **2 niveles con lote lleno** | **49.76 ms** | **3** | **0** | **25** |
| 25 | Sin precarga | 82.12 ms | 21 | 20 | 21 |
| 25 | Solo vecinas directas | 46.94 ms | 14 | 0 | 24 |
| 25 | 2 niveles sin relleno | 50.45 ms | 11 | 0 | 25 |
| 25 | Mapa completo | 45.24 ms | 3 | 0 | 25 |
| 25 | Solo relleno BFS | 44.46 ms | 4 | 0 | 25 |
| 100 | **2 niveles con lote lleno** | **183.83 ms** | **10** | **0** | **100** |
| 100 | Sin precarga | 133.45 ms | 69 | 68 | 69 |
| 100 | Solo vecinas directas | 161.64 ms | 53 | 0 | 89 |
| 100 | 2 niveles sin relleno | 175.08 ms | 47 | 0 | 96 |
| 100 | Mapa completo | 173.26 ms | 10 | 0 | 100 |
| 100 | Solo relleno BFS | 176.85 ms | 11 | 0 | 100 |
| 400 | **2 niveles con lote lleno** | **689.01 ms** | **35** | **0** | **350** |
| 400 | Sin precarga | 375.88 ms | 211 | 210 | 211 |
| 400 | Solo vecinas directas | 508.12 ms | 166 | 0 | 289 |
| 400 | 2 niveles sin relleno | 640.30 ms | 142 | 0 | 322 |
| 400 | Mapa completo | 648.71 ms | 40 | 0 | 400 |
| 400 | Solo relleno BFS | 612.21 ms | 35 | 0 | 341 |

En cripta-01 (6 salas, camino 1-2-3-4-3-2-5), la estrategia elegida, mapa completo y solo relleno BFS hacen 1 solicitud; 2 niveles sin relleno, 3; solo vecinas directas, 4; y sin precarga, 5 solicitudes con 4 esperas.

**Estructuras**

| n | Cola propia (usada) | `list.pop(0)` (descartada) |
| --- | --- | --- |
| 10 | 0.0056 ms | 0.0011 ms |
| 100 | 0.0859 ms | 0.0090 ms |
| 1 000 | 0.5521 ms | 0.1205 ms |
| 10 000 | 5.5519 ms | 6.0953 ms |
| 100 000 | 65.3217 ms | 913.7763 ms |

| n | Vector lineal (usado) | ArrayOrdenado binario (descartado) |
| --- | --- | --- |
| 25 | 0.078 ms | 0.183 ms |
| 100 | 1.000 ms | 1.887 ms |
| 400 | 17.544 ms | 20.267 ms |
| 1 600 | 269.498 ms | 281.868 ms |

(Cola: n encolar + n desencolar. Pertenencia: n inserciones sin duplicados + n consultas, la mitad presentes.)

**Qué muestran los datos**

- Frente a 2 niveles sin relleno, la estrategia elegida baja las solicitudes de 47 a 10 con 100 salas (−79 %) y de 142 a 35 con 400 salas (−75 %): la red estimada pasa de 56.8 s a 14.0 s. El costo local sube unos 0.08 ms por movimiento, mucho menos que una sola solicitud de red.
- Sin precarga, con 400 salas el jugador espera en 210 de los 600 movimientos (unos 84 s estimados). Con precarga las esperas son 0 porque la fuente responde sin latencia: este bench no distingue 1 nivel de 2 niveles en esperas.
- Mapa completo hace las 40 solicitudes antes de la primera acción (unos 16 s de espera inicial) y carga 189 salas que el jugador no visita.
- Con los tamaños reales de cola (3 a 4), `list.pop(0)` es más rápida, aunque por microsegundos. La `Cola` propia gana desde 10 000 elementos y con 100 000 es 14 veces más rápida.
- El `Vector` gana en todos los tamaños medidos, pero su ventaja baja de 2.4 veces (25 salas) a 1.05 veces (1 600 salas).

**Comandos para verificar** (PowerShell, desde la raíz del repositorio):

```powershell
.\venv\Scripts\python.exe bench\bench_precarga.py --salida docs\evidencia\2026-10-18-precarga.json
```

### Límites conocidos

- **Si pedir 10 salas deja de costar lo mismo que pedir 1.** Con 400 salas se cargan 350 y el jugador visita 211: 139 salas (40 % de lo cargado) nunca se usan; con 100 salas son 31 de 100. Si el API cobrara por sala, si la latencia creciera con el tamaño del lote o si cada sala ocupara mucha memoria, convendría volver a 2 niveles sin relleno o a pedir cada sala al entrar.
- **Si el presupuesto es más ajustado.** En cripta-01 el presupuesto es 9 y el recorrido 1-2-3-4-6 gasta 7 con caché vacía, 8 si antes se listan las criptas y 2 con caché caliente. Una falla con reintento puede agotarlo, y como no se reservan solicitudes para `garantizar_contenido`, la precarga puede gastar la que después necesita un movimiento. Con un presupuesto menor que 7 (8 si se listan criptas), alguna solicitud del recorrido se rechaza.
- **Si una partida pide muchas más salas.** Las comparaciones por movimiento crecen de 160 a 748 y 2 532 (25, 100 y 400 salas), y el costo local por movimiento pasa de 0.83 a 0.92 y 1.15 ms. Por la tendencia de la prueba aislada, con más de ~1 600 salas pedidas convendría cambiar a `ArrayOrdenado` o, como los `sala_id` son enteros de 1 a N, a un arreglo de banderas indexado por id (consulta O(1)).
- **Si la cripta tiene 10 salas o menos.** Un solo lote la cubre completa: pedir el mapa al inicio es igual de bueno y más simple.
- **Si el jugador avanza más rápido de lo que llegan los lotes (no medido).** La estrategia adelanta lo alcanzable en dos movimientos; con `--hilos`, si el jugador hace más de dos movimientos mientras un lote sigue en camino, `garantizar_contenido` tiene que esperar.
- **Cola de pendientes.** Con colas de 3 a 4 salas la `Cola` propia no da ventaja de tiempo; se usa por la exigencia de la sección 7 del enunciado y porque escala, no por rendimiento en los tamaños reales.

---

## 4.3 Resolución de referencias del catálogo

*Redacta: Rol 2 · Revisa: Rol 4*

### Problema

Cuando llega el contenido de una sala, el juego tiene que convertir cada `tipo_id` en la ficha que describe al enemigo, objeto o trampa. Esa consulta debe:

- Aprovechar las fichas que ya están cargadas, para no descargarlas otra vez.
- Mantener en memoria una ficha mientras alguna instancia la esté usando.

Frecuencia medida (partida de ensayo de cripta-01 con semilla 3, `docs/evidencia/2026-10-16-determinismo.json`):

| Búsquedas | Aciertos | Fallos | Inserciones | Desalojos | Comparaciones | Referencias adquiridas | Referencias liberadas |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 161 | 150 | 11 | 11 | 0 | 1 559 | 138 | 133 |

En total se cargaron 11 fichas con 3 solicitudes al catálogo.

### Alternativas consideradas

| Alternativa | Ventaja | Por qué se descarta |
| --- | --- | --- |
| Array ordenado | Busca en O(log n) | Necesita mecanismos adicionales para proteger las fichas en uso y para decidir cuáles retirar al llegar al límite de memoria. |
| Lista plana | Sencilla y rápida con pocas claves | Conserva todo lo que recibe si no se le agrega una política de expulsión. |
| **ListaLRU** | Prioriza las fichas consultadas hace poco, controla la capacidad y protege las que siguen en uso | **Elegida**, aunque no sea la opción más rápida en todos los escenarios |

### Decisión

- `ControladorRed` usa una `ListaLRU` construida sobre la `ListaDoble` propia.
- Cuando `buscar` encuentra una ficha, mueve su nodo al frente para marcarla como la más reciente.
- Las fichas con contador `en_uso` mayor que cero quedan protegidas: no se desalojan.
- Al morir un enemigo, el modelo avisa al controlador para que libere su referencia.
- `ControladorJuego._sincronizar_protegidas` mantiene protegidas las fichas del inventario, de los objetos del suelo y de las trampas de la sala actual. Cuando cambia la situación del jugador, actualiza esas referencias y libera las que ya no hacen falta.

### Análisis de complejidad

- Buscar una ficha, protegerla o liberar su referencia obliga a localizarla en la caché: **O(k)**, con k = fichas recorridas.
- Una vez encontrado el nodo, moverlo al frente cuesta **O(1)** adicional.
- Con una capacidad pequeña el recorrido es corto, pero al subir `--cache-size` también crece el trabajo de búsqueda: no conviene tratar ese costo como constante al comparar cachés de distintos tamaños.

### Evidencia empírica

**Bench (caso `cache`, `docs/evidencia/2026-10-16-catalogo-inventario.json`).** 1 000 búsquedas sobre 40 claves distintas, secuencia generada con semilla 42 y LRU con capacidad para 25 fichas. Mediana de 5 repeticiones después de un calentamiento, en Windows 11 con Python 3.12.14 (procesador AMD64 Family 25 Model 33 Stepping 2).

| Estrategia | Mediana | Aciertos |
| --- | --- | --- |
| ListaLRU, 25 espacios (usada) | 3.454900 ms | 617 |
| Lista plana sin límite (descartada) | 0.420300 ms | 960 |

La diferencia de aciertos se explica porque la lista plana puede conservar las 40 claves y la LRU solo tiene 25 espacios. Las dos filas muestran estrategias de memoria distintas, no la misma política con distinto rendimiento.

**Pruebas.**

- La protección de fichas se verifica en `tests/test_bloque3_catalogoLRU.py` y en `test_fichas_de_la_sala_actual_quedan_protegidas`.
- Las pruebas del bloque 4 comparan el estado y los mensajes de las partidas y de sus replays con 10 patrones de latencia, y comprueban la incorporación de lotes concurrentes.

**Comandos para verificar** (PowerShell, desde la raíz del repositorio):

```powershell
.\venv\Scripts\python.exe main.py --bench
.\venv\Scripts\python.exe -m herramientas.verificar_determinismo --cripta cripta-01 --guion docs\evidencia\guion-rol2.json --ensayo --salida docs\evidencia\determinismo-local.json
.\venv\Scripts\python.exe -m pytest tests\test_bloque3_catalogoLRU.py tests\test_controlador_juego.py::test_fichas_de_la_sala_actual_quedan_protegidas -v
.\venv\Scripts\python.exe -m pytest tests\test_rol2_bloque4.py -k "latencias or patrones" -v
```

### Límites conocidos

- La búsqueda lineal puede volverse costosa si se aumenta mucho la capacidad de la caché.
- Si todas las fichas están protegidas, ninguna se puede retirar para abrir espacio sin incumplir la regla de conservar las fichas en uso.
- Los ensayos de latencia cubren los datos de prueba y una grilla de 25 salas: no garantizan el comportamiento ante cualquier contenido del API ni con escalas x10 o x50.
- El bench mide búsquedas e inserciones con datos sintéticos; sus tiempos no incluyen la latencia de Internet.

---

## 4.4 Reutilización y caché persistente

*Redacta: Rol 1 · Revisa: Rol 2*

### Problema

- Evitar descargar otra vez contenido y fichas que siguen vigentes, también entre una ejecución y otra.
- Distinguir un fallo de memoria (la ficha ya no está en la LRU) de un fallo de disco (tampoco está guardada).
- Que una versión global actualizada no se tome como prueba de que todos los archivos son actuales: cada archivo tiene que demostrar su propia versión.

### Alternativas consideradas

| Alternativa | Por qué se descarta |
| --- | --- |
| Solo memoria | Pierde los datos entre ejecuciones. |
| JSON sin versión por archivo | Puede aceptar archivos antiguos después de que cambie el marcador global. |
| **Memoria + disco, con identidad y versión en cada archivo** | **Elegida** |

### Decisión

- **Memoria:** `ControladorRed` guarda las fichas en una `ListaLRU` sobre `ListaDoble` propia (`controlador/controlador_red.py`), con capacidad `--cache-size` (25 por defecto) y referencias `en_uso` que impiden desalojar fichas en uso (ver 4.3).
- **Disco:** `PersistenciaContenido` y `PersistenciaCatalogo` guardan cada sala y cada ficha en un "sobre" JSON con `formato_cache`, `version`, `identificador` y `datos`. Solo se acepta la versión esperada por la instancia de persistencia; los archivos antiguos sin sobre cuentan como caché ausente.
- **Escritura segura:** primero se serializa, luego se escribe un temporal único en el mismo directorio y se reemplaza con `os.replace`. Si el reemplazo falla, se conserva la copia anterior y se propaga el error.
- **Lecturas inválidas:** una copia corrupta, antigua o incompatible devuelve `None` y se vuelve a pedir a la fuente; un error de permisos se propaga. Una copia con datos imposibles (por ejemplo, vida incompatible con la ficha) se invalida para permitir el siguiente intento.
- **Rutas:** un validador compartido rechaza rutas, caracteres no portables y nombres reservados de Windows antes de tocar el archivo.

### Análisis de complejidad

| Operación | Costo |
| --- | --- |
| Localizar una ficha en la LRU (sin dict) | O(k), con k = capacidad |
| Mover un nodo conocido al frente | O(1) |
| Buscar la víctima de desalojo | O(k) |
| Espacio en memoria | O(k) |
| Leer o serializar un archivo | O(b), con b = bytes del archivo |

La búsqueda completa en la LRU no es O(1): solo lo es mover un nodo ya localizado.

### Evidencia empírica

**Pruebas (`tests/test_cierre_bloque2.py`, 56 pruebas).** Comprueban, entre otros casos:

- Una segunda carga sin descargas de contenido ni de fichas.
- Versión por archivo aunque el marcador global sea nuevo.
- JSON corrupto con marcador vigente y caché con codificación inválida.
- Ficha desalojada de la LRU y recuperada del disco; protección con capacidad 1.
- Fallo de reemplazo, temporales distintos para dos escritores y fallos que no publican salas a medias.

Estas pruebas miden corrección, no rendimiento.

**Bench (`--bench`, caso `recuperacion`).** Se buscan 25 fichas que ya están guardadas en disco. En una variante caben todas en la LRU; en la otra la LRU tiene 10 espacios y las fichas desalojadas se recuperan del disco.

| Variante | Mediana |
| --- | --- |
| Fichas en memoria (LRU de 25) | 0.200 ms |
| Fichas recuperadas del disco (LRU de 10) | 3.330 ms |

Recuperar del disco cuesta unas 17 veces más que encontrar la ficha en memoria, pero evita volver a pedirla por la red.

Equipo: Windows 10 (10.0.19045), Intel Core i7-8750H @ 2.20 GHz (12 núcleos lógicos), 8 GB de RAM, Python 3.14.6. Fecha: 18-10-2026. Mediana de 5 repeticiones más 1 calentamiento.

**Comandos para verificar** (PowerShell, desde la raíz del repositorio):

```powershell
.\venv\Scripts\python.exe -m pytest tests\test_cierre_bloque2.py -v
.\venv\Scripts\python.exe main.py --bench
```

### Límites conocidos

- La caché anterior sin sobre se invalida y se vuelve a descargar.
- No es el formato binario de la partida (ver 4.10).
- El reemplazo es por archivo: no hay una transacción para todo el lote ni garantía de durabilidad ante un apagón (no se usa fsync).
- Windows puede rechazar un reemplazo simultáneo: se propaga `OSError` y se intenta limpiar el temporal.
- No se admite modificar el modelo concurrentemente.

---

## 4.5 Inventario

*Redacta: Rol 2 · Revisa: Rol 3*

### Problema

El inventario tiene que permitir recoger, seleccionar, equipar y soltar objetos sin perder la posición del cursor. También debe:

- Respetar la capacidad que indican los datos de la cripta.
- Mantener los objetos en un estado coherente cuando una acción se rechaza o se revierte.

Frecuencia medida (ruta de ensayo con semilla 3, que termina en victoria):

| Inserciones | Eliminaciones | Movimientos al frente | Recorridos desde el frente | Nodos recorridos |
| --- | --- | --- | --- | --- |
| 5 | 1 | 1 | 48 | 104 |

Estos contadores reflejan el trabajo de la estructura, incluso si después una acción se deshace; no representan la cantidad de objetos que queda al terminar.

### Alternativas consideradas

| Alternativa | Problema |
| --- | --- |
| `Vector` o `list` | Guarda los elementos contiguos: al eliminar el primero hay que desplazar los siguientes. |
| Lista simple | Evita el desplazamiento, pero retroceder desde el cursor obliga a buscar el nodo anterior. |
| **Lista doble** | **Elegida:** permite avanzar y retroceder, y eliminar un nodo directamente cuando ya se tiene su referencia. |

En los tamaños medidos `list` fue más rápida que la `ListaDoble`. Aun así se mantuvo la lista doble porque permite trabajar con referencias a nodos y con un cursor bidireccional, y porque la sección 7 del enunciado exige implementar las estructuras propias.

### Decisión

- El jugador guarda su inventario en una `ListaDoble` con cursor.
- Al equipar un objeto, su nodo se mueve al frente.
- Para mostrar el inventario ordenado por peso, valor o nombre se crea un `Vector` aparte; el orden real del inventario no cambia.
- Si el inventario está lleno, recoger se rechaza antes de retirar el objeto del suelo y sin consumir tiempo virtual. Esto también se comprobó desde `ControladorJuego`.

### Análisis de complejidad

| Operación | Costo |
| --- | --- |
| Avanzar o retroceder el cursor, eliminar un objeto o moverlo al frente (con el nodo conocido) | O(1) |
| Buscar un objeto por id | O(n), con n = objetos del inventario |
| Recoger (busca duplicados y retira del suelo) | O(n + s), con s = objetos en el suelo |
| Crear la copia para una vista ordenada | O(n), más el costo del ordenamiento elegido (4.9) |

### Evidencia empírica

**Bench (caso `inventario`, `docs/evidencia/2026-10-16-catalogo-inventario.json`).** Se agregan n objetos y después se eliminan desde el inicio (2n operaciones). Mediana de 5 repeticiones después de un calentamiento, en Windows 11 con Python 3.12.14 (AMD64 Family 25 Model 33 Stepping 2).

| n | ListaDoble (usada) | list (descartada) |
| --- | --- | --- |
| 10 | 0.005600 ms | 0.000800 ms |
| 50 | 0.023400 ms | 0.002900 ms |
| 500 | 0.251200 ms | 0.035700 ms |

**Pruebas.**

- `test_recoger_con_inventario_lleno_se_rechaza_sin_tiempo`: el rechazo cuando no hay espacio.
- `test_recorrer_ordenar_no_reordena_y_numero_sigue_siendo_real`: las vistas ordenadas conservan el orden y la numeración del inventario real.
- Las pruebas de entidades y del cursor cubren la navegación y las modificaciones.

Las frecuencias y la configuración de la ruta de ensayo están en `docs/evidencia/2026-10-16-determinismo.json`.

**Comandos para verificar** (PowerShell, desde la raíz del repositorio):

```powershell
.\venv\Scripts\python.exe main.py --bench
.\venv\Scripts\python.exe -m herramientas.verificar_determinismo --cripta cripta-01 --guion docs\evidencia\guion-rol2.json --ensayo --salida docs\evidencia\determinismo-local.json
.\venv\Scripts\python.exe -m pytest tests\test_controlador_juego.py::test_recoger_con_inventario_lleno_se_rechaza_sin_tiempo tests\test_consola_persistencia_replay.py::test_recorrer_ordenar_no_reordena_y_numero_sigue_siendo_real tests\test_bloque2_entidades.py -v
```

### Límites conocidos

- Eliminar en O(1) depende de tener la referencia al nodo; si solo se tiene el id del objeto, primero hay que recorrer la lista.
- Cada nodo guarda referencias al anterior y al siguiente, lo que agrega memoria.
- Hasta 500 objetos, el bench no muestra ventaja de tiempo frente a `list`, y no mide todas las operaciones del cursor.
- Estos resultados describen el ensayo de inventario: no permiten sacar conclusiones sobre una cripta con x10 o x50 salas.

---

## 4.6 Retroceso e historial reversible

*Redacta: Rol 3 · Revisa: Rol 4*

### Problema

El pergamino de retroceso tiene que restaurar el estado anterior a una acción del jugador, incluidos todos los eventos de enemigos y efectos que ocurrieron hasta la siguiente decisión. Hay dos excepciones:

- No se recuperan los pergaminos usados.
- No se deshace la caché.

Se pueden deshacer hasta cinco acciones.

Frecuencia medida: en `bench.ciclo` (escala 1, 200 salas), cada repetición confirma 205 intervalos y registra 186 346 deltas, unos 909 por intervalo. Se descartan 200 intervalos por el límite: la pila conserva exactamente los últimos 5.

### Alternativas consideradas

| Alternativa | Por qué se descarta |
| --- | --- |
| Copia completa del juego | Está prohibida (sección 4.6 del enunciado) y su costo es proporcional al mundo, aunque haya pocos cambios. |
| Reproducir todo el log desde el inicio | El costo de cada retroceso crece con la partida. |
| **Deltas** | **Elegida:** solo se guardan los cambios y se aplican en orden inverso. |

### Decisión

- Una `Pila` propia limitada a cinco `GrupoDeltas`; cada grupo guarda sus deltas en un `Vector`.
- Tipos de delta: `DeltaVida`, `DeltaEvento`/`DeltaEfecto`, `DeltaPuerta`, `DeltaObjeto`, `DeltaRastro`, `DeltaTrampa`, `DeltaVelocidad` y deltas de campos y de pertenencia a listas.
- `DeltaReloj` guarda el tiempo, la siguiente secuencia y el estado del generador aleatorio una vez por intervalo: datos de tamaño fijo, no una copia del juego.

**Ciclo de un intervalo**

1. El controlador valida la acción (llave, espacio, contenido del destino).
2. El historial se abre al ejecutar la acción decidida, antes de aplicarla.
3. El jugador toma su turno, se aplican los cambios y se programa su siguiente acción.
4. El reloj procesa los eventos de enemigos y efectos hasta la siguiente decisión.
5. El historial se confirma al llegar a la siguiente decisión, nunca antes de los eventos intermedios. Si la acción falla, el intervalo se aborta y no se apila.

**Qué se registra solo y qué no**

- Se registran automáticamente los cambios hechos con la API: eventos del reloj, vida de actores vinculados, recoger, soltar y equipar, rastro y entorno.
- Una asignación directa no crea deltas: quien cambie un campo a mano tiene que registrar antes su delta.

**Por qué no basta con volver a marcar un evento como válido:** un evento ejecutado o cancelado puede haber salido del heap. `DeltaEvento` restaura el mismo handle, su presencia en el heap y su enlace con el dueño, con su secuencia original.

**Pergaminos:** se usan entre intervalos, consumen uno y revierten un grupo sin avanzar el tiempo. Si no hay historia o el jugador murió, no se consume. Recoger, soltar y consumir pergaminos queda excluido de los deltas. Dos usos seguidos revierten dos acciones distintas.

### Análisis de complejidad

| Operación | Costo |
| --- | --- |
| Apilar un grupo | O(1) |
| Agregar un delta | O(1) amortizado |
| Revertir un atributo | O(1) |
| Revertir un evento (reinsertarlo en el heap) | O(log n) |
| Revertir un objeto o una lista del suelo | Puede requerir búsqueda O(n) |
| Memoria | Proporcional a los cambios de cinco intervalos, más el estado fijo del PRNG por intervalo |

No se promete O(1) para deshacer un intervalo completo: cuesta la suma de sus inversas.

### Evidencia empírica

**Pruebas.**

- `tests/test_historial_bloque3.py` (26 casos): muerte con efectos, rearme, secuencias, azar, dos pergaminos y cinco intervalos mixtos con cinco semillas.
- `tests/test_integracion_rol3_bloque3.py`: con datos offline reales, entra a la sala 2, activa enemigos y trampa, revierte y comprueba enemigos, rastro, trampa y que la caché no se deshace.

**Bench (`--bench`, caso `historial`).** Cinco cambios y cinco retrocesos con deltas, contra guardar una copia completa del estado en cada paso. Las dos variantes restauran también el PRNG.

| Valores del estado | Deltas (usada) | Copias completas (descartada) | Valores guardados: deltas / copias |
| --- | --- | --- | --- |
| 100 | 0.115 ms | 0.118 ms | 5 / 500 |
| 1 000 | 0.113 ms | 0.369 ms | 5 / 5 000 |
| 10 000 | 0.115 ms | 3.018 ms | 5 / 50 000 |

El costo de los deltas no depende del tamaño del estado; el de las copias crece con él (26 veces más lento con 10 000 valores). La copia de estado solo existe en el bench: nunca se importa en el juego.

Equipo: Windows 10 (10.0.19045), Intel Core i7-8750H @ 2.20 GHz (12 núcleos lógicos), 8 GB de RAM, Python 3.14.6. Fecha: 18-10-2026. Mediana de 5 repeticiones más 1 calentamiento.

**Comandos para verificar** (PowerShell, desde la raíz del repositorio):

```powershell
.\venv\Scripts\python.exe -m pytest tests\test_historial_bloque3.py tests\test_integracion_rol3_bloque3.py -v
.\venv\Scripts\python.exe main.py --bench
.\venv\Scripts\python.exe -m bench.ciclo --escalas 1 --ciclos 1000 --salida $env:TEMP\ciclos.json
```

### Límites conocidos

- El controlador y los efectos tienen que registrar los cambios que no se cubren automáticamente: una asignación directa no crea deltas.
- Los callbacks se reconstruyen al cargar la partida; no se serializan funciones.
- Cinco acciones pueden contener muchos deltas: en `bench.ciclo` son unos 4 500 en memoria (5 × ~909).
- Los contadores de diagnóstico no retroceden.

---

## 4.7 Rastro del jugador

*Redacta: Rol 3 · Revisa: Rol 1*

### Problema

Cada sala tiene que recordar la última vez que el jugador pasó por ella, para que un enemigo rastreador elija a qué sala vecina moverse:

- Solo considera salas vecinas.
- Una marca es "fresca" si tiene menos de 400 unidades de tiempo.
- Ante un empate, gana la sala con menor id.

### Alternativas consideradas

| Alternativa | Por qué se descarta |
| --- | --- |
| Buscar en un historial completo de visitas | Su costo crece con la partida y no hace falta guardar todas las visitas. |
| Vector reservado hasta el mayor id de sala | Acceso directo, pero usa memoria desproporcionada si los ids son dispersos. |
| **Una marca en cada `Sala` del Vector ordenado que ya existe** | **Elegida:** reutiliza la estructura del mundo, sin dict ni una segunda copia de tiempos. |

### Decisión

- `Rastro` usa `CriptaModelo.sala_por_id` y modifica `Sala.tiempo_rastro`. El valor −1 significa "nunca visitada".
- Una marca es fresca si `0 <= ahora − marca < 400`; las marcas vencidas no se borran, simplemente dejan de servir al consultarlas.
- `DeltaRastro` restaura el valor anterior cuando se usa el pergamino.
- El plan pedía literalmente un vector indexado por `sala_id`. Se adaptó para admitir ids arbitrarios: no se supone que el id sea la posición en el Vector.

### Análisis de complejidad

| Operación | Costo |
| --- | --- |
| Registrar o consultar por id | O(log n), con la búsqueda binaria que ya existe |
| Decisión del rastreador | O(grado): lee las vecinas ya enlazadas, sin importar cuántas salas tenga la cripta |
| Marca por sala | O(1) en memoria |
| Delta por visita | O(1); no se duplica el vector |

### Evidencia empírica

- `tests/test_rol3_bloque3.py` prueba las fronteras 399 y 400, una sala nunca visitada, una marca futura, la restauración y un id de 1 000 000 000.
- Las pruebas previas mantienen el empate por menor id y comprueban que la decisión no busca en todo el mapa.
- `tests/test_integracion_rol3_bloque3.py` revierte la entrada real a la sala 2 de cripta-01.

**Comandos para verificar** (PowerShell, desde la raíz del repositorio):

```powershell
.\venv\Scripts\python.exe -m pytest tests\test_rol3_bloque3.py tests\test_integracion_rol3_bloque3.py tests\test_bloque2_entidades.py::test_rastreador_empate_puertas_y_no_busca_mapa -v
```

### Límites conocidos

- No se debe tratar el `sala_id` como una posición contigua.
- El esqueleto del mapa tiene que estar completo antes de consultar.
- El controlador registra la marca inicial en t = 0 y cada movimiento completado.
- El rastro y los enemigos tienen que compartir las mismas instancias de `Sala`.

---

## 4.8 Bitácora en pantalla

*Redacta: Rol 4 · Revisa: Rol 2*

### Problema

El enunciado (secciones 4.8 y 10.2) pide que la interfaz muestre únicamente los últimos 20 mensajes del juego, junto con el estado de la sala, y además:

- Que la memoria de esta bitácora sea constante durante toda la partida.
- Que agregar un mensaje no obligue a desplazar físicamente los 19 anteriores.

Para eso, el programa ejecuta tres operaciones sobre la bitácora de pantalla:

- **Agregar** un mensaje.
- **Listar** los mensajes, del más antiguo al más reciente.
- **Restaurar** los mensajes al cargar una partida guardada.

### Alternativas consideradas

| Alternativa | Costo por mensaje | Por qué se descarta |
| --- | --- | --- |
| `Vector` o `list` que desplaza al borrar el primero | O(k): al llenarse, cada mensaje nuevo mueve los 19 anteriores | Incumple la regla de no desplazar los 19 anteriores. Es la alternativa que el plan pide comparar (ver evidencia). |
| `list` que crece y muestra los últimos 20 | O(1) amortizado | La memoria crece con cada mensaje durante toda la partida: incumple la memoria constante. |
| Cola acotada sobre nodos enlazados | O(1), sin desplazamientos | Crea un nodo nuevo por mensaje y descarta el más antiguo: la cantidad de nodos vivos es constante, pero el almacenamiento no se reutiliza. No tiene medición en el bench. |
| `collections.deque(maxlen=20)` | O(1) | Es una estructura de la biblioteca de Python, y la sección 7 del enunciado exige implementar las propias. |
| **Array circular de capacidad fija (`ArrayCircular`)** | O(1), sin desplazamientos | **Elegida:** usa el mismo arreglo de 20 posiciones toda la partida. |

### Decisión

Se usa `ArrayCircular(20)` (`estructuras/array_circular.py`) en las dos vistas:

| Vista | Dónde | Detalle |
| --- | --- | --- |
| Consola | `VistaConsola._mensajes` (`vista/vista_consola.py`) | `mostrar_estado` imprime los 20 mensajes debajo del estado de la sala. |
| Pygame | `ControladorPygame._historial_mensajes` (`vista_pygame/controlador_pygame.py`) | El modelo corre en otro hilo, así que agregar, listar y restaurar se hacen dentro de `self._lock`. La escena de partida dibuja los 8 más recientes, que son los que caben en el panel. |

**Cómo funciona `ArrayCircular`**

- `_datos` es una `list` de tamaño fijo creada una sola vez (la sección 7 del enunciado permite `list` como almacenamiento contiguo de bajo nivel). `_inicio` señala el mensaje más antiguo y `_tamano` cuántos hay.
- `agregarValor` escribe en la posición `(_inicio + _tamano) % capacidad`. Si el arreglo ya está lleno, esa posición es la del mensaje más antiguo: lo sobrescribe y avanza `_inicio`. Nunca mueve los demás elementos ni amplía el arreglo.
- `listar_en_orden` recorre desde `_inicio` y devuelve una lista nueva, del más antiguo al más reciente.
- Cuenta agregados, sobrescrituras, listados y elementos listados, para las pruebas y métricas.
- Guarda solo texto (`str`), no referencias al modelo, así que no retiene enemigos ni objetos ya eliminados.
- Al cargar una partida, `restaurar_mensajes` crea un `ArrayCircular(20)` nuevo y agrega los mensajes guardados en orden.

Esta bitácora es solo de visualización: no reemplaza la bitácora de partida que se usa para reproducir (4.11).

### Análisis de complejidad

Notación: k = capacidad (20), m = mensajes agregados en toda la partida.

| Operación | Costo |
| --- | --- |
| `agregarValor` | O(1): una escritura y aritmética de índices, sin desplazamientos |
| `listar_en_orden` | O(k): recorre hasta 20 posiciones y crea una lista nueva |
| `restaurar_mensajes` | O(k), porque se guardan como máximo 20 mensajes |
| Alternativa que desplaza | O(k) por mensaje una vez lleno; en total O(m · k), es decir (m − k) · (k − 1) movimientos: con m = 20 000 son 19 980 · 19 = 379 620 |
| Espacio | O(k), constante respecto de m |

### Evidencia empírica

**Pruebas (`tests/test_bitacora_pantalla.py`: 9 de 9 aprobadas en 3.53 s, con pytest 9.1.1 y Python 3.14.6 en Windows).** Cada requisito de la sección 4.8 tiene al menos una prueba:

| Requisito | Pruebas |
| --- | --- |
| Solo los últimos 20 | `test_la_capacidad_es_20`; `test_tras_varias_vueltas_quedan_los_ultimos_20_del_mas_antiguo_al_mas_nuevo` (47 mensajes: quedan del 27 al 46, con 27 sobrescrituras); `test_la_pantalla_muestra_solo_los_ultimos_20` (30 mensajes: se ven del 10 al 29); `test_partida_larga_solo_20_mensajes_en_cada_pantalla` (partida real con 60 esperas) |
| Orden del más antiguo al más reciente | `test_con_menos_de_20_muestra_todos_en_orden` y las anteriores |
| Sin desplazar los 19 anteriores | `test_agregar_escribe_una_sola_posicion_y_no_desplaza_las_demas` (45 mensajes con el arreglo lleno: cada uno cambia una sola posición) |
| Memoria constante | `test_el_almacenamiento_es_el_mismo_arreglo_de_20_toda_la_partida` (20 000 mensajes); `test_la_memoria_no_crece_con_la_cantidad_de_mensajes` (con tracemalloc, 100 000 mensajes ocupan menos de 4 KB más que 1 000) |
| Solo texto | `test_solo_guarda_texto_sin_referencias_al_modelo` |

**Bench (`--bench`, caso `mensajes`).** Agrega n mensajes a un buffer de 20 con cada alternativa y lista el resultado; antes de medir verifica que las dos dejen los mismos 20 mensajes.

| Mensajes | Array circular (usado) | Desplazamiento (descartado) | Desplazamientos |
| --- | --- | --- | --- |
| 20 | 0.007 ms | 0.001 ms | 0 |
| 20 000 | 5.181 ms | 15.200 ms | 379 620 |

- Con 20 mensajes el arreglo no llega a llenarse y ninguna alternativa desplaza nada. El desplazamiento es más rápido porque solo agrega al final de la lista, mientras el array circular calcula la posición con módulo; la diferencia es de microsegundos.
- Con 20 000 mensajes el array circular es 2.9 veces más rápido (unos 0.26 contra 0.76 µs por mensaje) y evita 379 620 movimientos.

Equipo: Windows 10 (10.0.19045), Intel Core i7-8750H @ 2.20 GHz (12 núcleos lógicos), 8 GB de RAM, Python 3.14.6. Fecha: 18-10-2026. Mediana de 5 repeticiones más 1 calentamiento.

**Comandos para verificar** (PowerShell, desde la raíz del repositorio):

```powershell
.\venv\Scripts\python.exe -m pytest tests\test_bitacora_pantalla.py -v
.\venv\Scripts\python.exe main.py --bench
```

### Límites conocidos

- **Ver más de 20 mensajes o volver atrás en la historia:** el arreglo descarta el más antiguo por diseño. La historia completa está en la bitácora de partida (4.11).
- **Capacidad mucho mayor:** `listar_en_orden` copia hasta k referencias en cada llamada y Pygame lo llama en cada cuadro (hasta 60 por segundo). Con k = 20 son como máximo 1 200 copias por segundo, un costo despreciable; con miles convendría dibujar sin copiar o listar solo cuando llega un mensaje nuevo.
- **Memoria constante en cantidad, no en bytes:** cada texto ocupa según su largo. En la prueba con mensajes de unos 40 caracteres, 100 000 mensajes ocupan menos de 4 KB más que 1 000.
- **Menos de 21 mensajes:** el array circular no gana en tiempo mientras el arreglo no se llena (0.007 contra 0.001 ms con 20).
- **Pygame dibuja solo 8 de los 20:** los otros 12 siguen en el arreglo pero no se ven. Si se exige ver los 20 en la interfaz gráfica, hay que cambiar el panel, no la estructura.
- **Hilos:** `ArrayCircular` no está protegido por sí mismo. En Pygame lo protege `self._lock`; cualquier acceso nuevo desde otro hilo tiene que pasar por ese candado.
- **La capacidad está en tres lugares** (`vista_consola.CAPACIDAD_MENSAJES`, `controlador_pygame.CAPACIDAD_MENSAJES` y `config_vista.CAPACIDAD_MENSAJES_HUD`): si cambiara, hay que actualizar los tres.

---

## 4.9 Ordenamiento

*Redacta: Rol 2 · Revisa: Rol 1*

### Problema

El juego necesita mostrar objetos ordenados (por peso, valor o nombre) sin cambiar su posición real en el inventario, y conservar el orden relativo de los objetos que empatan en el criterio elegido. El programa tiene que elegir el algoritmo según propiedades medibles de los datos, así que hace falta medir las implementaciones que realmente usa el juego.

Frecuencia: la ruta de victoria que se usó para contar operaciones no consulta el inventario ordenado, así que en esa partida la frecuencia fue cero. Un jugador que use `I peso`, `I valor` o `I nombre` sí ejecuta estos ordenamientos.

### Alternativas consideradas

| Algoritmo | Costo | Ventaja | Desventaja |
| --- | --- | --- | --- |
| InsertionSort | O(n + I), con I = inversiones de la entrada | Poco trabajo si los datos ya están ordenados o casi | Cuadrático en el peor caso |
| MergeSort | O(n log n), sin importar el orden inicial | Costo predecible | Usa memoria auxiliar |

Para que la comparación sirviera para elegir el umbral del juego, el bench llama directamente a `insertion_sort` y `merge_sort` de `estructuras/ordenamientos.py`, sobre el `Vector` propio, con los mismos contadores y el mismo comparador. El bench anterior medía otras implementaciones sobre `list`, y eso no permitía justificar el umbral de estas funciones.

### Decisión

- `UMBRAL_TAMANO_PEQUENO = 50`.
- Hasta 50 elementos, si la comparación no está marcada como costosa, `ordenar` elige InsertionSort.
- Con más de 50, solo elige InsertionSort si los datos ya están completamente ordenados; si no, usa MergeSort.
- Si la comparación está marcada como costosa, se mantiene MergeSort.
- Los dos algoritmos son estables.

**Cómo se fijó el umbral:** se conservó el último tamaño medido antes de que MergeSort redujera el tiempo de InsertionSort en al menos 10 % con datos aleatorios y mantuviera esa ventaja en los tamaños mayores.

- En n = 50 la diferencia fue menor que 10 %; en 60, 75, 100, 200 y 500 la ventaja de MergeSort superó ese margen.
- Con 5 a 30 elementos no hubo cruce, por eso se ampliaron los tamaños de la prueba.
- 50 es una elección prudente cuando no se conoce el desorden de la entrada, aunque no sea el mejor valor para todas las distribuciones.
- Pocos descensos entre elementos vecinos no se toman como garantía de pocas inversiones: una entrada puede tener pocos descensos y aun así exigir muchos desplazamientos a InsertionSort.

### Análisis de complejidad

| Algoritmo / operación | Tiempo | Memoria auxiliar |
| --- | --- | --- |
| InsertionSort | O(n + I); O(n²) en el peor caso | O(1) |
| MergeSort | O(n log n) | O(n), con profundidad de recursión O(log n) |
| Selector, entrada pequeña | O(1) | — |
| Selector, entrada grande (comprobar si ya está ordenada) | O(n) | — |

### Evidencia empírica

Mediciones en `docs/evidencia/2026-10-16-ordenamiento.json` y `docs/evidencia/2026-10-16-ordenamiento-confirmacion.json`, en Windows 11 con Python 3.12.14 (AMD64 Family 25 Model 33 Stepping 2).

- Mediana de 7 repeticiones, cada una con 20 entradas distintas (semillas 42 a 61), después de 20 ordenamientos de calentamiento.
- Se alternó el orden de ejecución de los algoritmos para no favorecer siempre al segundo.
- El tiempo excluye construir los vectores, la red, la pantalla y las impresiones.
- "Casi ordenado": datos ordenados con `max(1, n // 20)` intercambios aleatorios.

Corrida de confirmación, en milisegundos por ordenamiento:

| n | Insertion, aleatorio | Merge, aleatorio | Insertion, casi ordenado | Merge, casi ordenado |
| --- | --- | --- | --- | --- |
| 5 | 0.004 | 0.015 | 0.003 | 0.013 |
| 10 | 0.014 | 0.037 | 0.007 | 0.036 |
| 15 | 0.031 | 0.062 | 0.011 | 0.060 |
| 20 | 0.051 | 0.092 | 0.014 | 0.088 |
| 25 | 0.081 | 0.128 | 0.019 | 0.116 |
| 30 | 0.112 | 0.151 | 0.021 | 0.143 |
| 50 | 0.299 | 0.290 | 0.051 | 0.276 |
| 60 | 0.425 | 0.367 | 0.074 | 0.335 |
| 75 | 0.648 | 0.490 | 0.101 | 0.456 |
| 100 | 1.157 | 0.681 | 0.171 | 0.649 |
| 200 | 4.608 | 1.578 | 0.668 | 1.483 |
| 500 | 28.785 | 4.639 | 3.656 | 4.351 |

**Comandos para verificar** (PowerShell, desde la raíz del repositorio):

```powershell
.\venv\Scripts\python.exe -m bench.calibrar_ordenamiento --salida docs\evidencia\ordenamiento-local.json
.\venv\Scripts\python.exe main.py --bench
.\venv\Scripts\python.exe -m pytest tests\test_rol2_bloque4.py -k "algoritmos or selector" -v
```

### Límites conocidos

- Con datos casi ordenados, InsertionSort siguió siendo más rápido hasta 500 elementos. El selector puede perder esa ventaja en entradas grandes casi ordenadas; se acepta para no elegir un algoritmo cuadrático solo por ver pocos descensos entre vecinos.
- La forma de construir los datos "casi ordenados" no garantiza una proporción fija de inversiones.
- La calibración no cubre comparaciones costosas ni tamaños mayores de 500: no se afirma que el umbral sea óptimo ahí.
- Conviene repetir las mediciones si cambia la máquina, el intérprete, el `Vector`, el comparador o los algoritmos.

---

## 4.10 Guardado binario

*Redacta: Rol 1 · Revisa: Rol 3*

### Problema

El enunciado pide guardar la partida en un archivo binario de formato propio y, además:

- Poder recuperar una sala sin leer el archivo completo.
- Detectar un archivo de otra versión del formato.
- Comparar tamaño y tiempo de carga contra guardar el mismo estado en JSON.

El archivo tiene que permitir continuar la partida exactamente donde quedó: agenda de eventos, historial de retroceso, estado del generador aleatorio, efectos activos y nombre del jugador.

Operaciones (todas a pedido del jugador con G y L en consola, `controlador/controlador_juego.py:521` y `:524`; no hay guardado automático):

| Operación | Qué hace |
| --- | --- |
| Guardar | Convierte el estado en registros (`persistencia/estado_partida.py:49`) y escribe el archivo (`persistencia/PartidaBinaria.py:54`). |
| Cargar | Lee el bloque global (`PartidaBinaria.py:139`), lee cada sala por el índice (`controlador/guardado.py:116-120`) y reconstruye el estado (`estado_partida.py:87`). |
| Recuperar una sala | La busca en el índice del archivo (`PartidaBinaria.py:147`). |

Frecuencia medida: cargar lee las S salas una por una (6 lecturas en cripta-01, 400 en una grilla de 400 salas). Un guardado de cripta-01 después de 20 acciones codifica 324 registros; una grilla de 400 salas con todo su contenido, 9 091.

### Alternativas consideradas

| Alternativa | Ventaja | Por qué se descarta |
| --- | --- | --- |
| Un solo archivo JSON | Legible y, con bloques pequeños, lee todo más rápido | No permite llegar a una sala sin leer y decodificar todo el archivo, que es lo que exige la sección 4.10 del enunciado. Con 5 000 salas, leer una sala cuesta 12.120 ms en JSON contra 0.174 ms con el índice. |
| `pickle` | Guarda el estado sin escribir un codificador | Cargar un pickle puede ejecutar código del archivo y el formato depende de las clases de Python. `estado_partida.py:4` lo excluye y solo reconstruye tipos de una lista permitida (`estado_partida.py:19-33`). |
| **Formato propio CRPT** | Encabezado, índice ordenado y un bloque por sala | **Elegida** |

### Decisión

**Formato CRPT** (`persistencia/PartidaBinaria.py:38-47`):

| Parte | Contenido | Referencia |
| --- | --- | --- |
| Encabezado (12 bytes) | Marca "CRPT", versión de formato 1, cantidad de salas (2 bytes) y posición donde empiezan los bloques | `:8-9`, `:96-99` |
| Índice | Un par `(sala_id, offset)` de 8 bytes por sala, ordenado por `sala_id` con el ordenamiento propio | `:67`, `:101-105` |
| Bloque global | Longitud + JSON | `:107-109` |
| Bloques de sala | `sala_id` + longitud + JSON, uno por sala | `:111-117` |

**Recuperar una sala:** búsqueda binaria directamente sobre el índice en disco, leyendo una entrada de 8 bytes por paso (`:167-186`). Luego salta al bloque y comprueba que su `sala_id` coincida (`:159-163`).

**Detección de archivos inválidos**

- **Otra versión:** marca distinta (`:123-127`), versión de formato distinta (`:128-133`), esquema de estado distinto de 2 (`guardado.py:20`, `:106-110`) o cripta, versión de cripta o versión de catálogo distintas (`guardado.py:111-114`).
- **Truncado o dañado:** lectura incompleta (`PartidaBinaria.py:19-20`), longitud o índice fuera del archivo (`:25-26`, `:134-136`, `:159-160`), sala faltante (`guardado.py:116-119`), tipos, referencias, listas o heap inconsistentes (`estado_partida.py:87-178`) y estado que no está en una decisión del jugador (`guardado.py:130-134`).
- Todo se reporta como "Guardado dañado o incompatible" (`guardado.py:160-162`) y la sesión en curso no se reemplaza.
- **Escritura atómica:** se escribe un temporal en la misma carpeta y se reemplaza con `os.replace` (`guardado.py:89-98`).

**Qué se guarda y qué no**

- Se guarda todo lo alcanzable desde la partida, el estado de red, las acciones, las fichas protegidas y los mensajes (`guardado.py:60-67`), conservando identidades y ciclos (`estado_partida.py:53-64`): agenda con sus handles, historial de deltas, generador aleatorio (`:74-75`), efectos y fichas en memoria (`ListaLRU`, `guardado.py:15-16`).
- El bloque global agrega el esquema 2 y el nombre del jugador (`guardado.py:68-70`). Los registros alcanzables desde una sala van al bloque de esa sala (`estado_partida.py:63`, `guardado.py:71-88`).
- **No se guardan** los callbacks de la partida (`estado_partida.py:34-36`, `:80-81`), que se reconstruyen al cargar (`guardado.py:145-147`), ni la caché en disco: la sesión cargada reutiliza la carpeta de caché actual (`guardado.py:135-136`).

**Ajuste F4B-01.** Un pergamino restaura la secuencia de la agenda, pero los eventos cancelados del intervalo revertido siguen físicamente en el heap con una secuencia mayor. La validación rechazaba ese guardado al cargarlo; ahora la regla de rango solo se aplica a las entradas válidas (`estado_partida.py:169-176`). Sin el ajuste, un guardado hecho después de P no se podía cargar ("Entrada de agenda inconsistente").

### Análisis de complejidad

Notación: S = salas, R = registros codificados, B = bytes del archivo, b = bytes de un bloque.

| Operación | Costo |
| --- | --- |
| Recuperar una sala | O(log S) lecturas de 8 bytes, más O(b) para leer su bloque (medido: 0.151 a 0.174 ms entre 50 y 5 000 salas) |
| Escribir el archivo | O(S log S) para ordenar el índice, más O(B) para escribir |
| Guardar completo | O(R²): codificar busca cada objeto en un `ArrayOrdenado` de referencias (O(log R)) y lo inserta desplazando elementos (O(R)) (`estado_partida.py:59-62`) |
| Cargar completo | O(S log S) por las lecturas del índice, O(R log R) para ordenar los registros (`guardado.py:121-125`) y O(R) para reconstruirlos |

### Evidencia empírica

- **Equipo:** Windows 10 (10.0.19045), Intel Core i7-8750H @ 2.20 GHz (12 núcleos lógicos), 8 GB de RAM, Python 3.14.6. Fecha: 18-10-2026.
- **Repeticiones:** 5 por medición, más 1 de calentamiento que no se cuenta; se reporta la mediana.
- **Código medido:** copia local anterior a los últimos commits de `feature/vista-pygame` (7946b1a); lo medido no cambia en esos commits, salvo una condición de la validación al cargar (F4B-01).

**`--bench`, casos `guardado`, `carga_total` y `carga_1_sala`** (estado sintético, el mismo para los dos formatos; JSON no tiene índice, así que leer una sala equivale a leer todo):

| Salas | Formato | Guardar | Tamaño | Leer todo | Leer 1 sala |
| --- | --- | --- | --- | --- | --- |
| 50 | **Binario (usado)** | 0.954 ms | 11 978 B | 1.496 ms | 0.151 ms |
| 50 | JSON (descartado) | 0.869 ms | 11 964 B | 0.217 ms | 0.217 ms |
| 500 | **Binario (usado)** | 6.671 ms | 118 609 B | 11.397 ms | 0.164 ms |
| 500 | JSON (descartado) | 7.959 ms | 118 996 B | 1.020 ms | 1.020 ms |
| 5 000 | **Binario (usado)** | 52.391 ms | 1 186 399 B | 110.025 ms | 0.174 ms |
| 5 000 | JSON (descartado) | 58.259 ms | 1 195 115 B | 12.120 ms | 12.120 ms |

**Estado real del juego** (script de medición; los mismos datos codificados en los dos formatos). cripta-01: datos offline, semilla 3, después de N y 19 esperas. Grillas: datos sintéticos de `bench/bench_precarga.py` con todas las salas cargadas (1 enemigo, 1 objeto y 1 trampa por sala).

| Caso | Salas | Registros | Tamaño binario / JSON | Escribir binario / JSON | Leer todo binario / JSON | Leer 1 sala | Guardar completo (G) | Cargar completo (L) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cripta-01 | 6 | 324 | 122 140 / 122 079 B | 2.609 / 20.640 ms | 3.573 / 4.262 ms | 0.382 ms | 26.067 ms | 31.425 ms |
| Grilla | 25 | 586 | 181 451 / 181 220 B | 4.302 / 19.438 ms | 4.322 / 3.241 ms | 0.322 ms | 59.870 ms | 19.218 ms |
| Grilla | 100 | 2 271 | 691 297 / 690 392 B | 11.074 / 52.688 ms | 9.948 / 9.121 ms | 0.241 ms | 635.078 ms | 80.103 ms |
| Grilla | 400 | 9 091 | 2 767 950 / 2 764 645 B | 34.673 / 216.253 ms | 55.742 / 55.941 ms | 0.383 ms | 10 061.487 ms | 366.996 ms |

**Qué muestran los datos**

- **Tamaño:** prácticamente igual en los dos formatos (menos de 0.8 % de diferencia), porque el contenedor binario guarda JSON dentro de cada bloque.
- **Leer una sala:** con el índice cuesta lo mismo con 6 que con 5 000 salas (0.151 a 0.383 ms); en JSON crece con el archivo (0.217 a 12.120 ms).
- **Leer todo:** con bloques sintéticos pequeños JSON es hasta 11 veces más rápido (11.397 contra 1.020 ms con 500 salas), porque el binario hace dos lecturas y un `json.loads` por bloque. Con bloques del juego real los dos quedan parejos (55.742 contra 55.941 ms con 400 salas). Se eligió el binario porque la sección 4.10 del enunciado exige recuperar una sala sin leer todo, y ese costo no crece con la cripta.
- **Guardar:** lo domina `codificar`, no el formato. Con 400 salas escribir el archivo toma 35 ms y el guardado completo 10 061 ms. En un perfil con cProfile del guardado de 100 salas, el 94 % del tiempo está en `ArrayOrdenado.insertar`.

**Pruebas:** `tests/test_bloque3.py` (21), `tests/test_persistencia.py` (13), `tests/test_consola_persistencia_replay.py` (31) y `tests/test_regresion_guardado_retroceso.py` (8, F4B-01): 73 aprobadas.

**Comandos para verificar** (PowerShell, desde la raíz del repositorio):

```powershell
.\venv\Scripts\python.exe main.py --bench
# Scripts de medición (están fuera del repositorio, en la carpeta mediciones):
.\venv\Scripts\python.exe ..\mediciones\medir_guardado_bitacora.py --salida ..\mediciones\2026-10-18-guardado-bitacora.json
.\venv\Scripts\python.exe ..\mediciones\perfil_guardar.py
# Pruebas:
.\venv\Scripts\python.exe -m pytest tests\test_bloque3.py tests\test_persistencia.py tests\test_consola_persistencia_replay.py tests\test_regresion_guardado_retroceso.py -v
```

### Límites conocidos

- **Partidas con muchos objetos:** guardar crece como O(R²) por el `ArrayOrdenado` de referencias de `codificar` (`estado_partida.py:59-62`). Con 2 271 registros tarda 0.6 s y con 9 091, 10.1 s. En una cripta más grande que las de desarrollo (sección 9 del enunciado), G puede congelar el juego varios segundos.
- **El juego no aprovecha el índice al cargar:** L lee todas las salas, una por una, abriendo el archivo cada vez (`guardado.py:116-120`). Con 400 salas, leer el archivo toma unos 56 ms y la carga completa 367 ms; la ventaja del índice aparece al consultar una sala, no en L.
- **Bloques muy pequeños:** leer todo es más lento que un JSON único (110.025 contra 12.120 ms con 5 000 salas sintéticas).
- **Tamaño máximo:** la cantidad de salas se guarda en 2 bytes (`PartidaBinaria.py:98`), así que el máximo es 65 535 salas por archivo; offsets y longitudes usan 4 bytes, así que el archivo no puede pasar de 4 GiB.
- **Sin suma de verificación:** un cambio dentro de un bloque que siga siendo JSON válido y pase las validaciones de tipos no se detecta.
- **Sin migración:** un guardado de otro esquema, cripta o catálogo se rechaza y no se puede abrir.

---

## 4.11 Bitácora de partida y reproducción

*Redacta: Rol 1 · Revisa: Rol 4*

### Problema

El enunciado (sección 4.11) pide:

- Registrar cada acción del jugador en un archivo de texto de solo anexado, con un encabezado que tenga al menos id de cripta, versión de cripta, versión de catálogo y semilla.
- Que `--replay partida.log` reproduzca la partida completa sin interacción.
- Que, si la versión del log ya no está disponible, el programa avise que no puede garantizar una reproducción fiel en vez de reproducir contra datos distintos.

La reproducción es el mecanismo principal para reportar y repetir errores durante la evaluación.

Operaciones que ejecuta el programa:

| Operación | Dónde |
| --- | --- |
| Crear la bitácora con el encabezado al iniciar una partida | `controlador/inicio_partida.py:120-123` |
| Agregar una línea por cada acción aceptada y por cada pergamino usado | `controlador/controlador_juego.py:382`, `:473-474` |
| Registrar el cierre con el estado final al terminar la sesión | `controlador_juego.py:552-554` |
| Abrir una bitácora nueva al cargar una partida guardada | `controlador_juego.py:525-532` |
| Reproducir: leer las acciones y ejecutarlas sin vista | `controlador/controlador_replay.py:119-179` |

Frecuencia medida: una escritura por acción aceptada. En la partida de ensayo de cripta-01 (`docs/evidencia/guion-rol2.json`) se enviaron 32 comandos: la bitácora registró 25 acciones y los 7 comandos rechazados no se registraron.

### Alternativas consideradas

| Alternativa | Por qué se descarta |
| --- | --- |
| Snapshots periódicos del estado | Un guardado real de cripta-01 ocupa 122 140 B y tarda 26.067 ms (4.10), contra unos 18 B y 8.5 µs por acción en la bitácora. Además, un snapshot no permite repetir la partida paso a paso ni detectar en qué acción se separa una reproducción. |
| Registrar todos los eventos, no solo las acciones | En la partida de ensayo hubo 25 acciones y 39 ciclos, con 11 turnos de enemigos y 4 efectos. En `bench.ciclo` (escala 1), 200 decisiones producen 40 000 turnos de enemigos y 20 000 efectos: 300 eventos por decisión. Con la misma semilla y el orden determinista de la red, esos eventos se vuelven a calcular, así que registrarlos agrandaría el archivo sin agregar información. |
| Escribir con buffer, sin flush por línea | Es más barato (1.2 contra 8.5 µs por acción), pero si el programa se cae se pierden las últimas acciones, justo las que hacen falta para repetir un error. |
| **Solo acciones del jugador, una línea por acción, con flush inmediato** | **Elegida** |

### Decisión

**Archivo de texto append-only** (`bitacora_partida.py`, clase `BitacoraPartida`):

- **Encabezado:** marca "CRIPTA_LOG v1", `cripta_id`, `version_cripta`, `version_catalogo`, `semilla` y un separador (`bitacora_partida.py:5-9`, `:27-41`). Se crea en `nueva_partida` cuando hay ruta de bitácora (`inicio_partida.py:120-123`).
- **Acciones:** una línea `t=<tiempo> <comando>` por acción. `registrar` abre el archivo en modo "a" y hace `write` y `flush` por línea (`bitacora_partida.py:75-79`).
- **Cierre:** al terminar se escriben `fin <estado>` y las líneas del estado final que compara el replay (`bitacora_partida.py:81-86`).

**Qué se registra y qué no**

- **Se registra:** la acción, después de ejecutarla con éxito (`controlador_juego.py:375-382`), y el pergamino, porque cambia el estado (`:473-474`).
- **No se registran:** los comandos rechazados (`controlador_juego.py:241-243`, `:268-271`), guardar y cargar (`:261-263`), ni ayuda, inventario o consultar, porque no cambian el estado.

**Rama nueva al cargar.** Una carga nunca trunca el log anterior: crea `carga_<uuid>.log` con el encabezado de la partida cargada y copia las acciones que venían en el guardado, así esa rama se puede reproducir desde el inicio (`controlador_juego.py:525-532`).

**Reproducción con `--replay`** (`main.py:71-72`, `:168-209`; `controlador/controlador_replay.py:119-179`)

1. Lee las acciones, rechaza un log con acciones no reproducibles (`controlador_replay.py:127-131`) y crea la partida con la semilla del log, sin bitácora (`:135-137`).
2. Verifica la versión de cripta y de catálogo antes de ejecutar cualquier acción (`controlador_replay.py:149-153`, `bitacora_partida.py:140-149`). Si no coinciden, se detiene con código 2 (`main.py:182-187`).
3. `GuionReplay` hace de vista: entrega cada acción y comprueba que el turno llegue en el mismo t y que la acción anterior no haya sido rechazada (`controlador_replay.py:60-81`).
4. Al final compara las acciones, el cierre y el estado final (`:162-178`). Una divergencia termina con código 3 (`main.py:188-192`).

El replay no usa vista ni pygame: pygame solo se importa en `jugar_gui`, y `--gui` no se puede combinar con `--replay` (`main.py:50-51`, `:158-161`).

**Orden determinista de la red.** Las respuestas se incorporan al modelo en orden de número de solicitud (`controlador/buffer_reordenamiento.py:19-104`), en un punto fijo al inicio de cada turno del jugador (`controlador_juego.py:231`). Así la partida depende solo de la versión de la cripta, la semilla y las acciones, no del momento en que llega cada respuesta (4.2).

### Análisis de complejidad

Notación: A = acciones registradas, L = largo de una línea.

| Operación | Costo |
| --- | --- |
| Registrar una acción (la más frecuente) | O(L): una escritura y un flush (`bitacora_partida.py:75-79`); medido: 8.5 µs |
| Leer las acciones al reproducir | O(A) líneas (`bitacora_partida.py:93-113`) |
| Reproducir | O(A) acciones; cada una cuesta lo mismo que jugarla (medido: casi lo mismo que la partida original) |
| Rama nueva al cargar | O(A): copia las acciones guardadas |
| Espacio | O(A): unos 18 B por acción, más encabezado y cierre |

### Evidencia empírica

- **Equipo:** Windows 10 (10.0.19045), Intel Core i7-8750H @ 2.20 GHz (12 núcleos lógicos), 8 GB de RAM, Python 3.14.6. Fecha: 18-10-2026.
- **Repeticiones:** 5 por medición (3 en el replay), más 1 de calentamiento que no se cuenta; se reporta la mediana.
- **Código medido:** copia local anterior a los últimos commits de `feature/vista-pygame` (7946b1a); lo medido no cambia en esos commits, salvo una condición de la validación al cargar (F4B-01).

**Costo de escribir la bitácora (1 000 acciones)**

| Alternativa | Total | Por acción |
| --- | --- | --- |
| **`write` + `flush` por línea (usada)** | 8.511 ms | 8.5 µs |
| `write` con buffer (descartada) | 1.179 ms | 1.2 µs |
| Snapshot del estado (descartada) | 26.067 ms por guardado | 122 140 B por guardado (cripta-01, 4.10) |

**Partidas largas y reproducción** (cripta de laboratorio de `herramientas/generar_cripta_prueba.py`, semilla 3, solo esperas en la sala inicial)

| Acciones | Tamaño del log | Partida | Replay | Replay verificado |
| --- | --- | --- | --- | --- |
| 100 | 2 503 B | 13.203 ms | 15.904 ms | Sí |
| 1 000 | 17 808 B | 128.514 ms | 111.937 ms | Sí |
| 5 000 | 89 809 B | 623.190 ms | 577.231 ms | Sí |

El tamaño crece unos 18 B por acción (en Windows cada línea termina en `\r\n`) y el replay crece de forma lineal, con un costo parecido al de jugar.

**Reproducción con latencias.** `herramientas/verificar_determinismo.py` juega la ruta de ensayo de cripta-01 en modo offline y con 10 patrones de latencia, cada una con caché vacía. Las 11 partidas y sus replays dieron el mismo resultado (victoria, 25 acciones).

**Pruebas:** `tests/test_controlador_replay.py` (15), `tests/test_consola_persistencia_replay.py` (31, incluye replay sin vista ni input y versión incompatible) y `tests/vista/test_sin_pygame_en_replay_bench.py` (2): 48 aprobadas.

**Comandos para verificar** (PowerShell, desde la raíz del repositorio):

```powershell
# Scripts de medición (están fuera del repositorio, en la carpeta mediciones):
.\venv\Scripts\python.exe ..\mediciones\medir_guardado_bitacora.py --salida ..\mediciones\2026-10-18-guardado-bitacora.json
# Determinismo, eventos por decisión y pruebas:
.\venv\Scripts\python.exe -m herramientas.verificar_determinismo --cripta cripta-01 --guion docs\evidencia\guion-rol2.json --ensayo --salida docs\evidencia\determinismo-local.json
.\venv\Scripts\python.exe -m bench.ciclo --escalas 1 --ciclos 1000 --salida $env:TEMP\ciclos.json
.\venv\Scripts\python.exe -m pytest tests\test_controlador_replay.py tests\test_consola_persistencia_replay.py tests\vista\test_sin_pygame_en_replay_bench.py -v
# Para reproducir una bitácora propia:
.\venv\Scripts\python.exe main.py --offline --replay partidas\bitacoras\ARCHIVO.log
```

### Límites conocidos

- **`flush` no es `fsync`** (`bitacora_partida.py:79`): los datos llegan al sistema operativo, pero ante un corte de energía se pueden perder las últimas líneas.
- **Versiones exactas:** la reproducción exige las mismas versiones de cripta y catálogo. Si cambian y no hay copia local compatible, el replay se detiene por diseño (sección 4.11 del enunciado).
- **Partida sin cierre:** si no terminó de forma controlada, el replay ejecuta todas las acciones pero no puede comparar el estado final (`controlador_replay.py:107-116`).
- **Varias cargas, varios archivos:** una sesión con varias cargas queda repartida en varias bitácoras. Cada una se puede reproducir desde el inicio, porque copia las acciones guardadas.
- **El replay cuesta casi lo mismo que jugar:** si una partida tiene muchos eventos por acción, reproducirla tarda tanto como esos eventos.

---

## 4.12 Efectos temporales (veneno, velocidad, antorcha, regeneración)

*Redacta: Rol 2 · Revisa: Rol 3*

### Problema

El enunciado (sección 2.10 y Apéndice B) define cuatro efectos que funcionan con el tiempo del reloj virtual, no con los turnos:

| Efecto | Comportamiento pedido |
| --- | --- |
| Veneno | Daña cada 80 unidades de tiempo hasta completar 400 desde que se aplica; se puede cancelar con un antídoto. |
| Modificador de velocidad | Cambia la velocidad del actor y reajusta su próxima acción al aplicarse y al terminar (sección 2.3 del enunciado). |
| Antorcha | Queda encendida durante su duración y se apaga sola al terminar. |
| Regeneración | Recupera vida periódicamente en los enemigos, sin pasar nunca de `vida_max`. |

El trabajo previo (ROL3_BLOQUE3.md) ya dejaba listos los mecanismos para programar, cancelar y reprogramar eventos según la velocidad, y los deltas. Faltaba decidir tres reglas para que no las interpretara distinto cada implementación: qué pasa al volver a aplicar un efecto, de dónde salen el origen y el daño del veneno, y si el pulso de veneno en t + 400 ocurre o no.

### Alternativas consideradas

| Decisión | Alternativas | Elegida y por qué |
| --- | --- | --- |
| Dónde guardar el estado de un efecto | Un `dict` en el actor; un campo nuevo con el estado como JSON | Un objeto propio (`EstadoVeneno`). El `dict` está prohibido como índice o caché (sección 7 del enunciado), y el campo JSON no hace falta: el objeto representa el estado y se serializa como cualquier otro atributo al guardar. |
| Volver a aplicar veneno | Acumular con el efecto anterior; reiniciarlo | **Reiniciar.** Acumular aplicaciones de distintas fuentes (por ejemplo, una trampa y un ataque) haría difícil saber cuántos pulsos quedan y cómo combinar el daño, y el enunciado no da una fórmula para acumular. |
| Pulso en t + 400 | Exclusivo (no ocurre); inclusivo (ocurre) | **Inclusivo:** los pulsos caen en 80, 160, 240, 320 y 400, cinco en total. Si t + 400 fuera exclusivo habría solo cuatro, lo que no coincide con "daño cada 80 durante 400". |

### Decisión

`modelo/efectos.py` implementa cuatro efectos reutilizables:

| Función | Evento que mantiene |
| --- | --- |
| `aplicar_veneno` / `cancelar_veneno` | `evento_veneno` |
| `aplicar_modificador_velocidad` | `evento_mod_velocidad` |
| `encender_antorcha` | `evento_apagado` |
| `iniciar_regeneracion` | `evento_regeneracion` |

- Todos usan `Reloj.programar_en`, así trabajan directamente con el tiempo virtual.
- Reutilizan `DeltaAtributos` y `DeltaEfecto` para aplicar, cancelar y programar cambios sin perder el historial.
- `aplicar_veneno` no decide quién aplica el veneno ni cuánto daño hace: eso viene de la ficha concreta (trampa, ataque u otra fuente).
- `aplicar_efecto_objeto(partida, objeto)` implementa el hook `Partida.aplicar_efecto`: las pociones con `modificador_velocidad` usan `aplicar_modificador_velocidad`, los antídotos `cancelar_veneno` y las antorchas `encender_antorcha`.
- `Partida.activar_enemigos` inicia la regeneración de cada enemigo que la tenga, después de programar su primera acción.

**Reglas finales**

- Volver a aplicar veneno reinicia el conteo de pulsos con el nuevo daño.
- El pulso de t + 400 ocurre y es el quinto y último.
- No se puede aplicar un segundo modificador de velocidad mientras otro está activo; primero tiene que terminar el anterior (la misma protección que `programar_en` usa para eventos con un único handle).
- La regeneración no tiene duración propia: sigue mientras el enemigo esté vivo.
- Cuando un enemigo muere, su regeneración se cancela sola: el evento está en `enemigo.eventos_efectos` con `efecto=True`, y `Actor.morir` cancela esos eventos.

### Análisis de complejidad

| Operación | Costo |
| --- | --- |
| Programar un pulso de veneno o regeneración | O(log n) amortizado, como cualquier evento del reloj |
| Cancelar un efecto | O(1): se usa directamente el handle, sin recorrer la agenda |
| Estado de un efecto (`EstadoVeneno`) | Tamaño constante, sin listas ni diccionarios de pulsos |
| Reaplicar o avanzar un pulso | O(1): se reemplaza la referencia y el delta registra el cambio |

### Evidencia empírica

**`tests/test_efectos_bloque3.py` (19 pruebas)** verifica, entre otras cosas:

- Que el veneno pulse cada 80 unidades hasta t + 400, incluido el último pulso.
- Que un antídoto antes del siguiente pulso evite ese daño, y que reaplicar veneno reinicie el conteo.
- Que un veneno letal no deje un pulso pendiente después de la muerte.
- Que los efectos se integren con `Entorno.activar_trampa` mediante `aplicar_efecto`.
- Que el modificador de velocidad reajuste la acción pendiente (por ejemplo, costo 100 con velocidad de 100 a 50 se reprograma para t = 200) y que no se pueda aplicar un segundo modificador activo.
- Que la antorcha se apague sola y que encender una antorcha ya encendida no reinicie su duración.
- Que la regeneración nunca pase de `vida_max` y se cancele al morir el enemigo.

Las pruebas de reversión usan el `Historial` real (`iniciar_accion`, `confirmar_accion` y `revertir`), no un mecanismo aparte.

**`tests/test_integracion_efectos_partida.py` (4 pruebas)** ejecuta el flujo completo con una `nueva_partida` real y comprueba que:

- `partida.aplicar_efecto` esté conectado con `aplicar_efecto_objeto`.
- Una antorcha real del catálogo offline se pueda encender.
- Un veneno se pueda cancelar con un antídoto real del catálogo (`itm_antidoto`).
- Una poción de velocidad se pueda aplicar y luego restaurar (con una ficha de prueba, porque el catálogo offline no tiene una).

**Comandos para verificar** (PowerShell, desde la raíz del repositorio):

```powershell
.\venv\Scripts\python.exe -m pytest tests\test_efectos_bloque3.py tests\test_integracion_efectos_partida.py -v
```

### Límites conocidos

- El catálogo offline no tiene enemigos con `regeneracion > 0` ni pociones con `modificador_velocidad`: esos casos se probaron con fichas de prueba construidas a mano, no con datos reales de una cripta.
- No existe `cancelar_modificador_velocidad`: el enunciado solo pide que el efecto termine solo. Si hiciera falta, se puede agregar con el mismo patrón que `cancelar_veneno`.
- Falta definir cómo una trampa o un enemigo aplicaría veneno directamente. `aplicar_veneno` ya recibe esos datos, pero ninguna ficha del catálogo actual (por ejemplo, `trp_dardos`) tiene un campo de daño por veneno, así que no se inventó la regla.
- Al usar un objeto, `Partida.usar_objeto` consume las pociones y los antídotos; la antorcha no se consume al encenderse (`modelo/partida.py:344-361`).
