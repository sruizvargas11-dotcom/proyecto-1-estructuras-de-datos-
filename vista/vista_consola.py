"""Vista de consola: entrada, estado, efectos y mensajes.

Solo presenta y lee: no cambia el modelo. La bitácora en pantalla (§4.8) es un
ArrayCircular de 20 mensajes: memoria constante, el más antiguo se sobrescribe.
"""
from estructuras.array_circular import ArrayCircular

CAPACIDAD_MENSAJES = 20

AYUDA = """Comandos (no distingue mayúsculas):
  N / S / E / O      moverse (100)            W            esperar (100)
  A [n]              atacar al enemigo n (100) AB <dir>     abrir puerta con llave (50)
  R [n]              recoger objeto n del suelo (25)
  T [n]              soltar objeto n del inventario (25)
  EQ [n]             equipar arma/armadura n (50)
  U [n]              usar objeto n (50)
  P                  pergamino de retroceso (sin tiempo)
  I [peso|valor|nombre]  ver inventario (sin tiempo)
  IS / IA / IC       siguiente / anterior / consultar objeto (sin tiempo)
  G [ruta]           guardar partida         L [ruta]     cargar partida
  H                  esta ayuda               Q            salir"""


class VistaConsola:
    def __init__(self, leer=input, escribir=print):
        self._leer = leer
        self._escribir = escribir
        self._mensajes = ArrayCircular(CAPACIDAD_MENSAJES)

    # ------------------------------------------------------------ bitácora en pantalla

    def agregar_mensaje(self, tiempo, texto):
        self._mensajes.agregarValor(f"[t={tiempo}] {texto}")

    def mensajes(self):
        """Del más antiguo al más reciente (máximo 20)."""
        return self._mensajes.listar_en_orden()

    def restaurar_mensajes(self, mensajes):
        self._mensajes = ArrayCircular(CAPACIDAD_MENSAJES)
        for mensaje in mensajes:
            self._mensajes.agregarValor(mensaje)

    # ------------------------------------------------------------ presentación

    def mostrar_estado(self, partida):
        jugador = partida.jugador
        sala = jugador.sala_actual
        e = self._escribir
        e("")
        e("=" * 64)
        e(f"t={partida.tiempo}  |  {sala.nombre} (sala {sala.id})")
        e(f"Vida {jugador.vida}/{jugador.vida_max}  Ataque {jugador.ataque}  "
          f"Defensa {jugador.defensa}  Velocidad {jugador.velocidad}")
        equipo = []
        if jugador.arma_equipada is not None:
            equipo.append(f"arma: {jugador.arma_equipada.nombre}")
        if jugador.armadura_equipada is not None:
            equipo.append(f"armadura: {jugador.armadura_equipada.nombre}")
        if equipo:
            e("Equipo: " + ", ".join(equipo))

        efectos = []
        if jugador.estado_veneno is not None:
            veneno = jugador.estado_veneno
            efectos.append(f'veneno ({veneno.pulsos_restantes} pulsos, '
                           f'{veneno.dano_por_pulso} de daño)')
        entrada = jugador.evento_mod_velocidad
        if entrada is not None and entrada.valido:
            efectos.append(f'velocidad modificada hasta t={entrada.tiempo}')
        for nodo in jugador.inventario.recorrer_desde_frente():
            objeto = nodo.valor
            if objeto.clase == 'antorcha' and objeto.encendida:
                efectos.append(f'{objeto.nombre} encendida hasta t={objeto.evento_apagado.tiempo}')
        e('Efectos: ' + ('; '.join(efectos) if efectos else 'ninguno'))

        salidas = []
        for salida in sala.salidas:
            estado = "cerrada" if salida.cerrada else "abierta"
            salidas.append(f"{salida.direccion}->{salida.sala_destino_id} ({estado})")
        e("Salidas: " + (", ".join(salidas) if salidas else "ninguna"))

        enemigos = [f"{i}. {partida.nombre_enemigo(x)} {x.vida}/{x.vida_max}"
                    for i, x in enumerate(sala.enemigos_activos, 1)]
        e("Enemigos: " + ("; ".join(enemigos) if enemigos else "ninguno"))

        suelo = [f"{i}. {o.nombre}" for i, o in enumerate(sala.objetos_suelo, 1)]
        e("Suelo: " + ("; ".join(suelo) if suelo else "nada"))

        trampas = [f"{t.nombre} ({'armada' if t.armada else 'desarmada'})"
                   for t in sala.trampas]
        if trampas:
            e("Trampas: " + "; ".join(trampas))

        inventario = [f"{i}. {n.valor.nombre}"
                      for i, n in enumerate(jugador.inventario.recorrer_desde_frente(), 1)]
        e(f"Inventario ({len(jugador.inventario)}/{jugador.inventario_max}): "
          + ("; ".join(inventario) if inventario else "vacío"))

        e("-" * 64)
        for linea in self.mensajes():
            e(linea)

    def mostrar_inventario(self, partida, objetos, criterio):
        titulo = "orden real" if criterio is None else f"ordenado por {criterio}"
        self._escribir(f"Inventario ({titulo}):")
        if len(objetos) == 0:
            self._escribir("  vacío")
        for i, objeto in enumerate(objetos, 1):
            numero = next(n for n, nodo in enumerate(
                partida.jugador.inventario.recorrer_desde_frente(), 1) if nodo.valor is objeto)
            self._escribir(f"  {numero}. {objeto.nombre}  peso {objeto.peso}  valor {objeto.valor}")

    def mostrar_ayuda(self):
        self._escribir(AYUDA)

    def mostrar_objeto(self, nodo):
        if nodo is None:
            self._escribir('Inventario vacío.')
        else:
            o = nodo.valor
            self._escribir(f'Selección: {o.nombre} ({o.instancia_id}), '
                           f'peso {o.peso}, valor {o.valor}.')

    def mostrar_fin(self, partida):
        self.mostrar_estado(partida)
        self._escribir("")
        if partida.estado == "victoria":
            self._escribir("¡Victoria! Escapaste de la cripta.")
        elif partida.estado == "derrota":
            self._escribir("Derrota: has muerto en la cripta.")
        else:
            self._escribir("Partida terminada por el jugador.")
        for campo, valor in partida.resumen_puntaje():
            self._escribir(f"  {campo}: {valor}")

    # ------------------------------------------------------------ entrada

    def leer_comando(self):
        try:
            return self._leer("> ")
        except (EOFError, KeyboardInterrupt):
            return "Q"


def informar(texto):
    """Salida de arranque/diagnóstico, sin crear una vista interactiva."""
    print(texto)


def seleccionar_cripta(criptas, leer=input):
    informar('Criptas disponibles:')
    for i, cripta in enumerate(criptas, 1):
        informar(f"  {i}. {cripta['id']}: {cripta['nombre']}")
    while True:
        try:
            entrada = leer('Cripta (número o id; Enter = primera; Q = salir): ').strip()
        except (EOFError, KeyboardInterrupt):
            return None
        if entrada.upper() == 'Q':
            return None
        if not entrada:
            return criptas[0]['id']
        for i, cripta in enumerate(criptas, 1):
            if entrada in (str(i), cripta['id']):
                return cripta['id']
        informar('Cripta desconocida.')
