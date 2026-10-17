# Perfilado del ciclo de 20 ms

Fecha: 16-10-2026. Datos completos: [2026-10-16-ciclo-20ms.json](2026-10-16-ciclo-20ms.json).

## Qué se mide

Un ciclo va desde que el jugador confirma una acción hasta que el modelo queda listo para la siguiente decisión. Incluye los turnos de enemigos y los efectos que vencen en ese intervalo, y también la escritura del log. Red y render quedan fuera:

- `FuenteSintetica` sirve una cripta en memoria con el mismo contrato que el API (páginas de 50, lotes de 10 como máximo).
- `GuionPerfil` es una vista muda que toma el tiempo entre un comando y el siguiente con `time.perf_counter_ns`.

La semilla es fija (11). Cada escala corre 1000 ciclos, y se reportan mínimo, mediana, p95 y máximo, ordenados con `estructuras.ordenamientos.ordenar`.

```console
python -m herramientas.perfilar_ciclo                     # x1, x10, x50
python -m herramientas.perfilar_ciclo --escala 1 --perfil # agrega cProfile
python -m herramientas.perfilar_ciclo --sospechosos       # un escenario por sospechoso
```

Las escalas cargan la cripta completa y activan a todos los enemigos desde el inicio. Es el peor caso posible: en una partida real, un enemigo solo se activa cuando el jugador entra en su sala.

Máquina: contenedor Linux con 2 CPU y Python 3.13.16. Como referencia del ruido, un trabajo fijo de CPU repetido 1000 veces dio un máximo de 1.93 veces la mediana. Por eso conviene repetir la medición en la computadora del equipo con el mismo comando.

## Resultado por escala

Las cifras están en ms.

| Escala | Salas / enemigos | Antes: mín / mediana / p95 / máx | Después: mín / mediana / p95 / máx |
|---|---|---|---|
| x1 | 200 / 300 | 0.43 / 7.32 / 15.69 / **31.17** | 0.25 / 3.87 / 7.29 / **12.89** |
| x10 | 2000 / 3000 | 28.8 / 192.6 / 295.0 / 372.7 | 12.4 / 88.5 / 122.7 / 271.2 |
| x50 | 10000 / 15000 | 9.6 / 1516.6 / 2066.1 / 2358.9 * | 10.1 / 592.4 / 800.1 / 950.3 |

\* El "antes" de x50 se midió con 200 ciclos, porque 1000 ciclos tomaban más de 25 minutos. El "después" usa 1000.

x1 pasó de superar la meta a quedar con margen. x10 y x50 siguen por encima por diseño: tienen 3000 y 15000 enemigos activos a la vez, y el costo crece linealmente con esa cantidad (ver Límites).

## Sospechosos del plan y los no enlistados

Cada escenario corre 300 ciclos (`--sospechosos`). Las cifras son mediana / p95 / máximo, en ms.

| Escenario | Qué fuerza | Antes | Después |
|---|---|---|---|
| base | x1: 200 salas, 300 enemigos activos | 12.23 / 18.46 / **22.69** | 6.35 / 10.49 / 18.93 |
| sala_por_id | 10000 salas cargadas; el jugador siempre se mueve | 14.74 / 21.12 / **68.18** | 7.53 / 11.14 / 15.61 |
| lru | 600 tipos de objeto, `--cache-size 600`, inventario rotando | 3.17 / 14.95 / **20.82** | 2.15 / 8.12 / 11.01 |
| rastreadores | 300 rastreadores persiguiendo al jugador | **21.39** / **31.91** / **46.49** | 9.64 / 12.55 / 16.33 |
| multitud | 300 dormidos en una sala; el jugador entra y pelea | 11.09 / 18.68 / **24.07** | 6.20 / 9.12 / 12.00 |
| log | x1 sin bitácora (aísla la escritura del log) | 11.78 / 18.27 / **26.44** | 6.12 / 9.71 / 12.32 |
| pergamino | alterna esperar y pergamino (revertir un intervalo) | 8.21 / 12.01 / **37.03** | 3.92 / 5.04 / 7.13 |

Después de los cambios, ningún escenario supera 20 ms. El máximo de base (18.9 ms) está cerca de la meta, y con el ruido de esta máquina puede variar entre corridas (entre 10.8 y 18.9 ms en siete repeticiones).

### Conclusión por sospechoso

- **Búsqueda lineal de sala por id.** No era la causa. Con 10000 salas cuesta alrededor de 1.3 ms por movimiento. El máximo de 68 ms era una recolección completa del recolector de basura de Python, que recorre todos los objetos vivos. Se resolvió con el recolector (abajo) y el máximo bajó a 15.6 ms. La búsqueda sigue siendo O(n).
- **Búsqueda en el LRU.** No apareció entre las funciones más costosas en cProfile. Su mejora viene de los cambios generales al heap y al recolector.
- **Rastreadores.** Era el sospechoso real y el peor caso que queda. 300 rastreadores generan unos 600 turnos de enemigo por cada movimiento del jugador. Además, una multitud de alrededor de 155 lo sigue de sala en sala, y cada movimiento recorría completas las dos listas de la sala, así que el costo era O(k²) por ciclo. Se resolvió con el heap, la decisión en una pasada y el movimiento de enemigos en O(1) amortizado. El máximo pasó de 46.5 a 16.3 ms.
- **Eventos cancelados acumulados en el heap.** No es un problema. Hubo 94 cancelaciones y ninguna se acumuló: la limpieza diferida las saca cuando llegan a la raíz.
- **Escritura del log.** Es despreciable: la mediana con bitácora es 6.35 ms y sin bitácora 6.12 ms.

### Causas no enlistadas que aparecieron

- **El propio heap.** Era lo que más consumía en cProfile: la validación de índice de `Vector.obtenerValor` en cada comparación y la construcción de tuplas clave.
- **El recolector de basura.** Causaba los picos aislados de `sala_por_id` (68 ms) y de `pergamino` (37 ms).
- **Activación de una sala llena.** `activar_enemigos` agregaba cada enemigo al final de una lista simple, que no tenía cola, y registraba un delta por lista. Eso era O(k²) al activar y al revertir.
- **Multitud que cambia de sala.** Cada movimiento recorría la sala de origen dos veces y la de destino dos veces. Al revertir, también se recorrían ambas.
- **Costo fijo por evento en reloj e historial.** Cada turno de enemigo registraba 5 deltas.

## Cambios aplicados y su efecto medido

1. **Heap (`estructuras/heap_minimo.py`).**
   - La clave `(tiempo, secuencia)` se calcula una sola vez por entrada.
   - `_flotar` y `_hundir` mueven un "hueco" sobre el arreglo interno (`Vector.almacenamiento()`) en lugar de intercambiar con validación en cada paso.
   - Sigue contando comparaciones.
   - Una extracción más una inserción toman: n=300, 16.2 → 4.7 µs; n=3600, 21.1 → 5.5 µs; n=18000, 27.1 → 6.3 µs.
2. **Reloj (`modelo/reloj.py`).**
   - `programar` guarda el handle y `tiempo_siguiente` en un solo delta, así que cada turno registra 4 deltas en vez de 5.
   - Las validaciones del camino frecuente evitan llamadas repetidas.
3. **Historial (`modelo/historial.py`, `modelo/deltas.py`).**
   - `registrar` comprueba la exclusión una sola vez.
   - `DeltaAtributos` tiene un camino directo cuando hay un solo campo.
   - `revertir_todo` recorre el almacenamiento sin validar cada índice.
4. **Decisión de enemigos (`modelo/entidades/enemigo.py`).**
   - Una sola pasada por las salidas en lugar de cuatro búsquedas.
   - El errante consume el generador de la misma manera que antes. Las pruebas comparan contra la versión original con las salidas desordenadas.
5. **Recolector (`controlador/controlador_juego.py`).**
   - `gc.freeze()` al empezar y en cada decisión del jugador, y `gc.unfreeze()` al terminar.
   - El juego no deja basura con ciclos de referencias: `gc.collect()` devuelve 0 al terminar 300 ciclos en 6 escenarios. Lo que deja de usarse se sigue liberando por conteo de referencias.
   - Con esto, el máximo de `sala_por_id` pasó de 68.2 a 15.6 ms y el de `pergamino` de 37.0 a 7.1 ms.
6. **Activación en bloque (`modelo/partida.py`, `DeltaActivacion`, `ListaSimple.insertar_varios_al_final` / `conservar_primeros`).**
   - Un solo delta guarda el orden de los dormidos y cuántos activos había.
   - Las listas se cambian con un recorrido cada una.

   | k enemigos | Activar | Revertir |
   |---|---|---|
   | 300 | 11.1 → 4.2 ms | 8.4 → 0.7 ms |
   | 1000 | 80.2 → 13.8 ms | 80.2 → 2.1 ms |
   | 3000 | 585.5 → 41.3 ms | 663.9 → 6.6 ms |

7. **Movimiento de enemigos (`ListaSimple` con referencia a la cola, `eliminar_valor_y_posicion`, `DeltaRetiro`, `DeltaAgregadoAlFinal`).**
   - Agregar al final ahora es O(1).
   - La sala de origen se recorre una sola vez, hasta el enemigo.
   - Al revertir, el enemigo se quita del destino en O(1) usando el nodo previo guardado. Si la lista cambió sin delta, se vuelve a buscar el valor.
   - Medido con el recolector congelado en ambos casos:

   | k enemigos | Mover la multitud | Revertir |
   |---|---|---|
   | 150 | 2.0 → 0.7 ms | 2.0 → 0.4 ms |
   | 300 | 6.8 → 0.9 ms | 7.6 → 0.6 ms |
   | 1000 | 59.6 → 3.3 ms | 74.0 → 5.2 ms |

## Determinismo

Ningún cambio altera el orden de los eventos ni el uso del generador:

- El estado final (`controlador.estado_final.lineas_estado`) es idéntico al del código original en 6 escenarios de 250 ciclos: base, lru, rastreadores, multitud, log y pergamino. Se comparó después de cada cambio, la última vez con todo aplicado.
- `tests/test_perfilado.py` compara el heap contra una lista de control, compara errante y rastreador contra su versión original, y revisa los deltas nuevos, la cola de la lista, el activar/mover con su reversión y el recolector.
- Suite completa: 811 pruebas aprobadas. Falla 1, `test_con_portada_limpia_cada_placa_ajusta_su_ancho_al_texto`, porque falta `assets/ui/portada_limpia.png` en la copia donde se midió. No tiene relación con estos cambios.

## Límites

- **Lo que primero se degrada es la agenda de turnos de enemigos.** Cada turno cuesta entre 25 y 37 µs, y cada enemigo activo juega cerca de 2 turnos por movimiento del jugador. El costo es lineal en la cantidad de enemigos activos. Barrido con 200 salas (mediana / p95 / máximo, en ms):

  | Enemigos activos | Mediana | p95 | Máximo |
  |---|---|---|---|
  | 300 | 3.78 | 7.10 | 9.57 |
  | 450 | 6.44 | 11.34 | 19.12 |
  | 600 | 10.33 | 17.12 | 32.52 |
  | 900 | 16.05 | 26.76 | 39.86 |

  La meta se cumple hasta unos 450 enemigos activos a la vez.
- **Una opción no se aplicó:** programar de forma diferida a los guardianes inactivos. Cambiaría la asignación de secuencias y, con ella, el desempate (§2.13), así que una misma semilla ya no daría el mismo resultado que el código actual.
- **`gc.freeze()` depende de que no haya basura cíclica.** Si en el futuro se crean ciclos de referencias durante la partida, se acumularían hasta `gc.unfreeze()` al terminar. Para comprobarlo, se puede contar lo que devuelve `gc.collect()` al terminar una partida.
- **Revertir con el pergamino cuesta O(deltas del intervalo).** En el escenario pergamino el máximo es 7.1 ms.
- **La búsqueda de sala por id y `_contiene` del controlador de red siguen siendo lineales.** Preparar 10000 salas toma unos 15 s, pero ocurre fuera del ciclo, durante la carga y la red.
