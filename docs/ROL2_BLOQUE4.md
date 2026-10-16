# Rol 2 · Bloque 4

Implementación y verificación del plan v4, páginas 15 y 17. Fecha: 2026-10-16.

## Cambios

- El benchmark de ordenamiento ejecuta las funciones reales sobre Vector.
- Umbral calibrado a 50; evidencia y limitaciones en decisiones/4.09.txt.
- DatosSimulado delega los siete métodos de FuenteDeDatos, añade latencias por
  patrón/argumentos y no consume el PRNG del juego.
- reproducir acepta un despachador opcional para ensayar replay con hilos.
- verificar_determinismo compara bytes de estado, secuencia completa de mensajes
  y log entre offline y diez patrones. También reproduce cada log con otro patrón.
- FNV-1a de 64 bits propio, sin hash() de cadenas; la comparación de bytes evita
  aceptar una colisión de checksum. Se conservan hashes como evidencia legible.
- Se completaron las secciones de decisiones 4.3, 4.5 y 4.9; revisión humana pendiente.

## Repetir

Desde la raíz del repositorio, con Python 3.12 y las dependencias instaladas:

```console
python -m pip install -r requirements.txt
python -m pytest -q
python main.py --bench
python -m bench.calibrar_ordenamiento --salida docs/evidencia/ordenamiento-nueva-medicion.json
python -m herramientas.verificar_determinismo --cripta cripta-01 --guion docs/evidencia/guion-rol2.json --ensayo --salida docs/evidencia/determinismo-nueva-medicion.json
```

`--ensayo` modifica únicamente la vida máxima a 300 en la fuente de prueba, por
igual en offline, simulación y replay; no modifica los JSON oficiales. La ruta
incluye combate, equipo, llaves, retroceso y victoria. Para otros datos, omitir
`--ensayo` y proporcionar `--offline-dir CARPETA`, `--cripta ID` y un guion JSON.
Cada corrida usa caché vacía independiente. Los registros temporales se eliminan
al acabar; la evidencia JSON conserva comandos, semilla, resultados y contadores.

## Apéndice B: matriz de cobertura

Los siguientes nombres son pruebas ejecutables de la suite, no verificaciones manuales.

| Caso | Archivo y prueba |
|---|---|
| Inventario lleno, sin tiempo | test_controlador_juego.py::test_recoger_con_inventario_lleno_se_rechaza_sin_tiempo |
| Puerta sin llave, sin tiempo | test_controlador_juego.py::test_abrir_sin_llave_y_puerta_cerrada_se_rechazan |
| Errante sin salidas, costo 100 | test_rol2_bloque4.py::test_errante_aislado_espera_costo_100_sin_consumir_azar |
| Rastreador empatado, menor id | test_bloque2_entidades.py::test_rastreador_empate_puertas_y_no_busca_mapa |
| Cierre automático sin transportar actor | test_rol3_bloque3.py::test_cierre_no_teletransporta_y_errante_no_atraviesa |
| Curación hasta vida_max | test_bloque2.py::TestActorBase::test_actor_curar_no_supera_vida_max; test_efectos_bloque3.py::test_regeneracion_cura_cada_200_hasta_el_tope_de_vida_max |
| Antídoto cancela futuros pulsos | test_efectos_bloque3.py::test_antidoto_antes_del_proximo_pulso_evita_ese_dano; test_integracion_efectos_partida.py::test_usar_antidoto_real_cancela_el_veneno_activo |
| Sala pendiente espera sin reloj | test_orden_determinista.py::test_movimiento_hacia_sala_pendiente_espera_sin_mover_el_reloj |

No fue necesario cambiar las reglas del motor para estos casos; se agregó la
comprobación integrada del costo del errante, que antes solo tenía cobertura
de decisión. Los otros siete ya tenían pruebas de regresión útiles.

## Evidencia de determinismo

`evidencia/2026-10-16-determinismo.json`: once partidas hasta victoria (offline
+ diez patrones), 25 acciones registradas por partida; once replays con patrones
10 a 20. Todas coinciden byte a byte dentro de cada grupo:

| Salida | FNV-1a 64 |
|---|---|
| Estado final | 3891100dc92a62af |
| Mensajes de partida | 98240098ddce690e |
| Mensajes de replay | 81d5d3cbd21aca08 |
| Log completo de partida | 1dc9ae8efef23c71 |

Los mensajes de partida y replay tienen hashes distintos entre sí porque el
log omite siete comandos rechazados. Cada secuencia se compara con su propia
línea base; los replays sí tienen exactamente el mismo estado final de partida.
Se añaden diez ensayos de lotes concurrentes en una grilla de 25 salas, además
de la prueba existente que fuerza la llegada del segundo lote antes del primero.

Auditoría de producción (modelo/, controlador/, estructuras/): no se encontraron
llamadas time.time(), id(), set(), sorted() ni .sort(). El tiempo real de espera
solo pertenece al adaptador de prueba y no decide acciones del modelo. UUID de
archivos de carga y generación inicial de semilla no forman parte del estado
reproducible de una partida que ya tiene semilla.

## Alcance y límites

Las pruebas usan fuentes locales reales y sintéticas; no consultan el servicio
HTTP de una cripta desconocida. No prueban todas las posibles criptas ni sustituyen
la prueba conjunta de entrega, el escalado x10/x50 ni la defensa oral de los
cuatro roles. La representación de estado usada es la observable del replay
actual: no serializa todos los internos. La igualdad de log/mensajes/estado es
exacta para los escenarios ejecutados, no una prueba formal de todo el motor.

Validación completa: 665 pruebas aprobadas con Python 3.12.14. En este entorno
Windows los temporales se redirigieron a una carpeta de trabajo autorizada;
los primeros errores de acceso del sandbox no requirieron cambios al proyecto.
