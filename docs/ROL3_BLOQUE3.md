# Rol 3 - Bloque 3: reloj, rastro, historial y entorno

12 de octubre de 2026. Rama: `jose-fabio`. Proyecto original de PyCharm. Base: cierre B2 integrado en `d1cc3cf`. Se conservaron los métodos `minimo` y `descartar_cancelados` que José Fabio ya había pegado. No se migraron carpetas.

## Resultado y alcance

Implementados los componentes del rol 3 del plan v4, páginas 10 y 12: completar heap, reloj entero, azar compartido, rastro, historial de cinco intervalos, deltas, rearme de trampas y cierre automático. Reglas principales: enunciado §§2.3, 2.10, 2.11 y 2.13.

**408 pruebas aprobadas:** 345 previas y 63 nuevas. No equivale al bloque 3 completo. Quedan a otros roles la partida, reglas concretas de veneno/poción/antorcha/regeneración, catálogo integrado, guardado y controlador/bucle. Los eventos simulados de efectos verifican el retroceso de su agenda; no sustituyen la implementación del rol 2.

## Archivos creados

| Archivo | Responsabilidad |
| --- | --- |
| `modelo/reloj.py` | Reloj, Evento, tiempo entero, secuencia, azar, cancelación y reprogramación |
| `modelo/rastro.py` | Registro, frescura y restauración de marcas |
| `modelo/historial.py` | GrupoDeltas, Historial y consumo irreversible de pergaminos |
| `modelo/deltas.py` | Inversas puntuales, sin copiar la partida |
| `modelo/entorno.py` | Rearme de trampas y cierre de salidas |
| `tests/test_rol3_bloque3.py` | 36 casos de heap, reloj, rastro y entorno |
| `tests/test_historial_bloque3.py` | 26 casos de reversión y estrés |
| `tests/test_integracion_rol3_bloque3.py` | 1 integración con contenido offline real de B2 |

## Cambios en clases existentes

- **HeapMinimo:** conserva `extraer_minimo()` que devuelve el dato. Añade `extraer_entrada()`, pertenencia/presencia del handle, `restaurarEntrada()` con su misma secuencia, lectura/restauración del próximo seq y contadores de consulta/limpieza/restauración.
- **ListaDoble:** `restaurar_nodo()` reintegra el mismo nodo para que los deltas y el cursor conserven referencias válidas. Prefiere los vecinos todavía presentes; no reinserta un pergamino consumido.
- **ListaSimple:** `insertar_en()` restaura un elemento en su posición lógica.
- **Actor:** enlace al reloj y lista propia de efectos pendientes. Vida/curación/muerte registran deltas si hay intervalo abierto. La muerte cancela su acción y efectos, sin recorrer toda la agenda. Sin reloj conserva el funcionamiento previo.
- **Jugador:** recoger, soltar y equipar registran DeltaObjeto. Las firmas públicas se conservan. Registrar al soltar un nodo conocido sigue siendo O(1); deshacer puede requerir búsqueda.
- **Trampa / Salida:** campos `evento_rearme` y `evento_cierre`. Entorno coordina sus eventos.
- **Pila:** se precisa que almacena grupos de deltas, no copias del estado.

## Reloj y contratos para rol 2 / rol 4

El heap ordena `(tiempo, secuencia)`. Hay UNA instancia `random.Random(semilla)` por Reloj. Rol 1 genera/persiste la semilla; Reloj la recibe. Pasar `reloj.azar` a Enemigo.decidir_accion, nunca crear otro generador del juego.

- `programar(actor, costo, ejecutar)`: tiempo = ahora + max(1, costo*100//velocidad). El callback recibe el reloj.
- `programar_inicial(jugador, ejecutar)`: primera acción en t=0. Enemigos se activan con costo 100, en orden ascendente de instancia_id establecido por quien los activa.
- `programar_en(tiempo, ejecutar, tipo=..., dueno=..., campo=...)`: evento absoluto. El campo opcional debe existir y recibe el handle. Efectos de actores también quedan en su lista de pendientes. Rol 2 añade los campos particulares de sus efectos.
- `cancelar(entrada)`: marca y desenlaza el efecto del dueño, sin buscar en la agenda.
- `reprogramar_por_velocidad(actor, nueva_velocidad)`: llamar ANTES de modificar manualmente velocidad. Conserva el progreso con max(1, restante*vel_anterior//vel_nueva), cancela y asigna seq nuevo. Exige velocidades enteras positivas.
- `calcular_dano(ataque, defensa)`: max(1, ataque + azar.randint(0,4) - defensa).

`avanzar_y_ejecutar()` procesa un evento; con argumento `hasta`, procesa todos los eventos <= ese tiempo y deja el reloj allí. Para el bucle usar **`avanzar_hasta_turno(jugador)`**: procesa lo anterior a su turno según tiempo Y seq; deja la decisión pendiente. Si un efecto cambia la velocidad durante la espera, considera el nuevo handle. Si el jugador muere devuelve None.

`tomar_turno(jugador)` retira la decisión pendiente sin ejecutar la interfaz. El controlador valida primero, inicia historial, toma el turno, ejecuta la acción y programa la siguiente. Los callbacks no pueden avanzar el reloj recursivamente. Un callback recurrente debe programar una fecha posterior, no un ciclo infinito en el mismo instante.

Ejemplo §2.13 verificado: jugador 0; rata 66; jugador 100; jugador 125; rata 132; jugador 175.

## Historial: registrar el intervalo completo

1. Validar acción, llave, espacio y contenido de destino.
2. `historial.iniciar_accion(reloj)` cuando toca decidir al jugador.
3. `reloj.tomar_turno(jugador)`; realizar cambios y programar la siguiente acción.
4. `reloj.avanzar_hasta_turno(jugador)` procesa enemigos/efectos intermedios.
5. `historial.confirmar_accion()` al llegar a la siguiente decisión o terminar la partida.

**No confirmar inmediatamente después del cambio del jugador:** deben quedar incluidos los eventos siguientes del intervalo. Ante una operación fallida, `abortar_accion()` revierte lo registrado sin apilarla.

Cinco GrupoDeltas en Pila propia; deltas en Vector y reversión en orden inverso. DeltaReloj conserva tiempo, siguiente seq y estado del único PRNG una vez por intervalo: metadatos de tamaño independiente del mapa, no copia de la partida. Los contadores técnicos y la caché no se deshacen.

### Registro automático y explícito

Automático al usar la API: eventos del reloj, vida de actores vinculados, recoger/soltar/equipar de Jugador vinculado, Rastro con historial compartido y Entorno.

Una asignación directa no se detecta automáticamente. Antes de otro cambio:

```python
historial.registrar(DeltaAtributos(actor, 'sala_actual'))
actor.sala_actual = destino
```

Para mover un enemigo entre listas registrar `DeltaListaSimple(lista, enemigo)` por cada lista afectada y el delta de sala_actual. Para consumir un objeto normal registrar `DeltaObjeto(jugador, objeto, nodo)` antes de retirarlo. Para efectos registrar los campos concretos modificados. Para botín reversible registrar `fabrica.siguiente_id` y la pertenencia de cada objeto creado.

Vincular los actores con `reloj.vincular_actor(actor)` antes de afectar vida. Compartir UNA instancia de Historial entre Reloj y Rastro. No modificar directamente las claves/validez de eventos ni extraer desde `reloj.agenda` durante el juego: eso evitaría el registro de deltas.

### Por qué no basta con valido=True

Un evento ejecutado o cancelado puede haber salido físicamente del heap. DeltaEvento/DeltaEfecto restauran el mismo handle, su presencia y enlace al dueño. Deshacer conserva la secuencia original; reprogramar normalmente crea otra. La secuencia global retrocede solo después de invertir el resto del grupo.

### Pergaminos

`historial.usar_pergamino(jugador, nodo)` se llama ENTRE intervalos, consume uno y revierte un grupo, sin tiempo ni nueva acción. Si no hay historia o el jugador murió devuelve False sin consumir. DeltaObjeto y DeltaListaSimple excluyen `pergamino_retroceso`: recoger y soltar pergaminos tampoco se invierte. Dos usos consecutivos revierten dos acciones distintas. El cursor se ajusta si apuntaba al consumido.

## Entorno

`Entorno.al_entrar(jugador, sala)` va inmediatamente después de mover y registrar rastro, antes del siguiente evento. Trampa armada aplica daño, se desarma y programa rearme (+300 si null en ficha). Desarmada no repite. Si muere el jugador se detiene la activación de las demás trampas de esa entrada.

El parámetro opcional `aplicar_efecto(trampa, actor, reloj)` deja al rol 2 conectar efectos concretos del catálogo sin inventar reglas aquí. Por defecto se conserva el daño del B2.

`Entorno.abrir(salida)` presupone llave validada por el controlador. Abre y programa cierre, si lo hay. Cierre 0 se programa en el instante actual con seq propia. Cerrar no teletransporta a quien ya cruzó; los enemigos existentes consultan `salida.cerrada`.

## Rastro y complejidades

Una sola marca: `Sala.tiempo_rastro` dentro del Vector ordenado de CriptaModelo. Consultar/registrar por ID usa su búsqueda binaria O(log n). Se adapta el texto del plan "vector indexado por sala_id" para admitir IDs dispersos sin memoria proporcional al ID máximo ni dict. Una prueba usa ID 1 000 000 000. El rastreador sigue leyendo directamente las vecinas enlazadas: O(grado). Fresco: 0 <= ahora - marca < 400; -1 y marcas futuras no sirven. La caducidad se evalúa al consultar.

Heap: consultar raíz O(1); limpiar k cancelados O(k log n); insertar/restaurar O(log n) amortizado por redimensionamiento del Vector. Cancelar O(1); morir O(e) para los efectos del propio actor, no para toda la agenda. Cancelados internos permanecen hasta alcanzar la raíz: medir acumulación en B4.

Historial: apilar grupo O(1), agregar delta O(1) amortizado. Deshacer depende del número de cambios y sus inversas: reinserción de evento O(log n), búsqueda de objeto O(n), restauración de suelo O(s). Cinco grupos no significa cinco deltas: un intervalo puede contener muchos eventos.

## Evidencia, reproducción y pendientes

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

408 aprobadas. Casos nuevos: empates con jugador, velocidad durante espera, muerte con efectos ya retirados, restauración de seq/azar, dos pergaminos, exclusión de recoger/soltar pergaminos, rearme/cierre, 100 reprogramaciones y cinco intervalos con cinco semillas. Integración offline: entrada a sala 2, activación de enemigos y trampa, reversión de estado y conservación de caché.

Pendiente de integración del equipo: controlador jugable, reglas concretas de efectos del rol 2, guardado del rol 1 y benchmark B4. Los callbacks se reconstruyen por tipo/dueño al cargar; no serializar funciones Python. El estado PRNG y las secuencias deben persistirse. No se declara partida completa ni rendimiento <20 ms.

## Qué falta para cerrar el bloque 3

Este listado indica lo pendiente de incorporar y verificar en esta base; no afirma que los compañeros no tengan avances en sus ramas. Referencia: plan v4, páginas 10 a 13.

- **Rol 1:** bitácora append-only con cabecera, versiones, semilla y flush; generación de semilla de partida; guardado binario propio e índice de salas para acceso directo; carga consistente de tiempo, secuencias y estado del PRNG. Reconstruir eventos por tipo y dueño, sin serializar callbacks. Fuente DatosSimulado con latencia y respuestas desordenadas, semilla de simulación independiente y generador de criptas sintéticas válidas.
- **Rol 2:** integrar catálogo con LRU, pendientes, lotes y protección en_uso; implementar los efectos reales (veneno, regeneración, velocidad y antorcha) y sus inversas mediante estas APIs. Completar Partida e inicialización con playerStats, rastro inicial y activación ordenada. Preparar las alternativas funcionales de benchmark separadas del juego; las mediciones comparativas pertenecen a B4.
- **Rol 4:** numerar peticiones según estado y aplicar respuestas en orden determinista; esperar contenido sin avanzar tiempo. Integrar controlador y bucle jugable: movimiento/ataque/espera 100, uso/equipar/abrir 50, recoger/soltar 25. Validar antes de abrir el intervalo; conectar trampas, rastro, enemigos, historial, mensajes y fin de partida.
- **Equipo / rol 3:** revisar los contratos con quienes los consumen y repetir las pruebas integradas con sus implementaciones reales. Comprobar guardado/carga, efectos, cinco retrocesos, muerte, catálogo protegido y misma secuencia lógica bajo latencias diferentes. Completar los borradores de decisiones exigidos para B3.

## Recomendaciones para la integración

1. Integrar primero esta base del rol 3. Rol 1 puede avanzar bitácora y semilla en paralelo; luego conectar persistencia, rol 2 y controlador del rol 4 según dependencias.
2. Mantener un solo reloj, Historial y generador de azar de juego por partida. No cambiar directamente campos de eventos; usar la API para que el retroceso los registre.
3. Acordar y documentar las políticas abiertas: reaplicación de efectos, origen/daño del veneno y pulso en el límite t+400. No inventar esas reglas al conectar callbacks.
4. Ejecutar la suite tras cada integración y añadir casos con las clases reales de efectos y persistencia. Las 408 pruebas actuales no demuestran todavía una partida completa ni ausencia de todos los bugs.
5. Posponer el traslado MVC hasta terminar B3, como acordó el equipo. Al hacerlo, reservar una carpeta de recursos para imágenes y cargarlas desde presentación; las reglas del juego no deben depender de rutas de imágenes. No añadir base de datos ni backend por imitar el ejemplo Java.
6. En B4 medir crecimiento de eventos cancelados, coste de retroceso y alternativas con cargas representativas. No usar la duración de pytest como benchmark del juego.

## Publicación

`Implementa rol 3 del bloque 3: reloj, deltas, rastro y eventos de entorno`

Entrega en `jose-fabio` mediante commit, push y PR hacia `main`; el hash y enlace de publicación se indican en el informe PDF. El merge requiere revisión del equipo. Se excluye el documento previo no seguido `docs/BLOQUE1_PRUEBAS.md`. Esta entrega no cierra todo B3.
