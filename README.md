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
`partidas/bitacoras/<cripta>_<semilla>.log`.

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
| `H` / `Q` | ayuda / salir | sin tiempo |

Sin `--cripta`, el juego lista las criptas disponibles y pide elegir una (Enter = la primera).

El controlador y el bucle de 4 pasos están en `controlador/controlador_juego.py`;
la vista de consola en `vista/vista_consola.py`. La pantalla muestra sala, salidas
(con llave y cierre automático), enemigos con su `instancia_id`, suelo, trampas,
vida y estadísticas, efectos activos (veneno, velocidad, antorcha), inventario y
los últimos 20 mensajes. Los efectos del entorno (pulsos de veneno, rearme de
trampas, cierre de puertas, antorcha que se apaga) se narran con
`controlador/narrador_eventos.py`. Guardar y cargar (`G`/`L`) se agregan en el
bloque 4 junto con el guardado binario.
