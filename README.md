# Proyecto de Estructuras de Datos

## Rol 3 del bloque 3

Reloj, rastro, historial y eventos de entorno: [explicación y contrato de integración](docs/ROL3_BLOQUE3.md).

Pruebas desde la raíz con el intérprete de PyCharm: `python -m pytest -q`.

## Cómo jugar (bloque 3)

Requisitos: Python 3.10+ y `pip install -r requirements.txt`.

```
python main.py --offline                  # datos locales (datos_offline/)
python main.py                            # servicio HTTP
python main.py --offline --hilos          # precarga de salas en segundo plano
python main.py --offline --cache-size 10  # fichas de catálogo en memoria (LRU)
python main.py --offline --solo-mapa      # solo carga y verifica el mapa (bloque 1)
```

Cada partida nueva genera su semilla y escribe su bitácora en
`partidas/bitacoras/<cripta>_<semilla>.log`. Al terminar (victoria, derrota o `Q`)
se agrega la línea `t=<t> fin <estado>` y, debajo, el estado final completo (jugador,
inventario, cada sala, y el siguiente valor del azar) en líneas que empiezan con `= `.

| Comando | Acción | Costo |
| --- | --- | --- |
| `N` `S` `E` `O` | moverse | 100 |
| `A [n]` | atacar al enemigo n | 100 |
| `W` | esperar | 100 |
| `U [n]` | usar objeto n del inventario | 50 |
| `EQ [n]` | equipar arma o armadura n | 50 |
| `AB <dir>` | abrir una puerta con la llave correcta | 50 |
| `R [n]` | recoger objeto n del suelo | 25 |
| `T [n]` | soltar objeto n del inventario | 25 |
| `P` | pergamino de retroceso | sin tiempo |
| `I [peso\|valor\|nombre]` | ver inventario (orden real u ordenado) | sin tiempo |
| `IS` / `IA` / `IC` | siguiente / anterior / consultar objeto | sin tiempo |
| `G [ruta]` / `L [ruta]` | guardar / cargar (por defecto `partidas/partida.sav`) | sin tiempo |
| `H` / `Q` | ayuda / salir | sin tiempo |

Sin `--cripta`, el juego lista las criptas disponibles y pide elegir una (Enter = la primera).

El controlador y el bucle de 4 pasos están en `controlador/controlador_juego.py`;
la vista de consola en `vista/vista_consola.py`. `G` y `L` conectan el estado
con `PartidaBinaria`; la carga exige la misma cripta y versiones. Se conserva
el historial y se abre una nueva bitácora tras cargar, sin truncar la anterior.

En Windows, para pipes o archivos UTF-8, usar `$env:PYTHONIOENCODING='utf-8'`
en PowerShell antes de ejecutar Python.

```
python main.py --offline --replay partidas/bitacoras/ARCHIVO.log
python main.py --bench
python main.py --offline --partidas-dir CARPETA --cache-dir CARPETA_CACHE
python -m herramientas.generar_cripta_prueba CARPETA_NUEVA
python main.py --offline --offline-dir CARPETA_NUEVA
```

La cripta de ensayo tiene estadísticas reforzadas y objetos de prueba para
recorrer todos los comandos. No modifica el balance ni los datos oficiales.
Las vistas `I peso/valor/nombre` muestran el número del orden real que usan
`U`, `EQ` y `T`; ordenar no reorganiza el inventario.
La pantalla muestra sala, salidas
(con llave y cierre automático), enemigos con su `instancia_id`, suelo, trampas,
vida y estadísticas, efectos activos (veneno, velocidad, antorcha), inventario y
los últimos 20 mensajes. Los efectos del entorno (pulsos de veneno, rearme de
trampas, cierre de puertas, antorcha que se apaga) se narran con
`controlador/narrador_eventos.py`. Guardar y cargar (`G`/`L`) usan el guardado binario.

## Reproducir una partida

```
python main.py --offline --replay partidas/bitacoras/cripta-01_123.log
python main.py --replay partidas/bitacoras/cripta-01_123.log --silencioso
```

No pide ningún comando ni abre la vista de consola. Antes de ejecutar compara las
versiones de cripta y catálogo del log con las actuales y se detiene si no
coinciden (salida 2). Durante la reproducción verifica que cada acción llegue en
el mismo `t` y no sea rechazada, y al final compara línea por línea el estado
final con el del log, indicando la primera línea distinta
(salida 3 si algo difiere). Sin cierre registrado se informa que el estado final
no puede verificarse; salida 0 solo indica que las acciones se reprodujeron sin errores.

## Reporte final de red

Al terminar una partida (victoria, derrota, `Q` o error) y al terminar un `--replay`,
el programa muestra el reporte de red y lo agrega a `partidas/reportes_red.txt`
(`--reportes ARCHIVO` para otra ruta). Cada reporte indica cripta, versiones,
semilla, bitácora, motivo de fin, solicitudes realizadas contra
`presupuesto_solicitudes` (con desglose contenido / catálogo / otras), uso de la
caché (esqueleto, salas y fichas desde disco o desde la fuente, aciertos y fallos
de la LRU) y esperas de precarga.

El historial se maneja como una `Pila` propia: el reporte más reciente queda
arriba y, al superar 50, se descartan automáticamente los más viejos.
