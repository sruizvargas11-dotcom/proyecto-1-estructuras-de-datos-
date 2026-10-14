from estructuras.array_circular import ArrayCircular
from estructuras.vector_dinamico import Vector

CAPACIDAD_MENSAJES = 20
ANCHO = 68

AYUDA = """Comandos (no distingue mayúsculas; [n] es opcional y vale 1 por defecto):
  N / S / E / O          moverse ............................ 100
  A [n]                  atacar al enemigo n ................ 100
  W                      esperar ............................ 100
  U [n]                  usar objeto n del inventario ........ 50
  EQ [n]                 equipar arma/armadura n ............. 50
  AB <dir>               abrir puerta con llave (AB E) ....... 50
  R [n]                  recoger objeto n del suelo .......... 25
  T [n]                  soltar objeto n del inventario ...... 25
  P                      pergamino de retroceso ......... sin tiempo
  I [peso|valor|nombre]  inventario: orden real u ordenado  sin tiempo
  H                      esta ayuda                    Q   salir
"""



def _pendiente(entrada):
    """Instante de un evento aún agendado, o None."""
    if entrada is None or not entrada.valido or not entrada._en_heap:
        return None
    return entrada.tiempo


def _barra(actual, maximo, ancho=20):
    if maximo <= 0:
        return ""
    llenos = (actual * ancho) // maximo
    if actual > 0 and llenos == 0:
        llenos = 1
    return "[" + "#" * llenos + "." * (ancho - llenos) + "]"


def _unir(partes, vacio):
    texto = ""
    for parte in partes:
        texto = parte if texto == "" else texto + "; " + parte
    return texto if texto else vacio


def describir_objeto(objeto):
    """Detalle corto según la clase del objeto: lo que importa para decidir."""
    clase = objeto.clase
    if clase == "arma":
        return f"+{objeto.ataque_bonus} ataque"
    if clase == "armadura":
        return f"+{objeto.defensa_bonus} defensa"
    if clase == "pocion":
        partes = Vector()
        if objeto.cura:
            partes.agregarValor(f"cura {objeto.cura}")
        if objeto.modificador_velocidad:
            signo = "+" if objeto.modificador_velocidad > 0 else ""
            partes.agregarValor(f"velocidad {signo}{objeto.modificador_velocidad} "
                                f"por {objeto.duracion}")
        return ", ".join(partes) if len(partes) else "poción"
    if clase == "antidoto":
        return "cura el veneno"
    if clase == "antorcha":
        return f"luz por {objeto.duracion}"
    if clase == "llave":
        return "llave"
    if clase == "pergamino_retroceso":
        return "deshace tu última acción; se lee con P"
    return clase


class VistaConsola:
    def __init__(self, leer=input, escribir=print):
        self._leer = leer
        self._escribir = escribir
        self._mensajes = ArrayCircular(CAPACIDAD_MENSAJES)
        self._panel = Vector()          # líneas que salen bajo el próximo estado


    def agregar_mensaje(self, tiempo, texto):
        self._mensajes.agregarValor(f"[t={tiempo}] {texto}")

    def mensajes(self):
        """Del más antiguo al más reciente (máximo 20)."""
        return self._mensajes.listar_en_orden()


    def elegir_cripta(self, criptas):
        """Lista las criptas (dicts con id y nombre) y devuelve el id elegido.

        Se acepta el número de la lista o el id; Enter elige la primera.
        """
        e = self._escribir
        e("Criptas disponibles:")
        for i, cripta in enumerate(criptas, 1):
            e(f"  {i}. {cripta['id']}: {cripta['nombre']}")
        while True:
            try:
                texto = self._leer("Elige una cripta [1]: ").strip()
            except EOFError:
                texto = ""
            if texto == "":
                return criptas[0]["id"]
            if texto.isdigit() and 1 <= int(texto) <= len(criptas):
                return criptas[int(texto) - 1]["id"]
            for cripta in criptas:
                if cripta["id"] == texto:
                    return texto
            e("Opción inválida: escribe el número o el id de la cripta.")

    def mostrar_inicio(self, cripta_id, semilla):
        self._escribir(f"Partida en {cripta_id} | semilla {semilla} | H para ver los comandos")


    def mostrar_estado(self, partida):
        jugador = partida.jugador
        sala = jugador.sala_actual
        e = self._escribir
        e("")
        e("=" * ANCHO)
        e(f" {sala.nombre} (sala {sala.id})".ljust(ANCHO - 10) + f"t = {partida.tiempo}".rjust(10))
        e("=" * ANCHO)
        e(f" Vida {_barra(jugador.vida, jugador.vida_max)} {jugador.vida}/{jugador.vida_max}")
        e(f" Ataque {jugador.ataque}   Defensa {jugador.defensa}   "
          f"Velocidad {jugador.velocidad}")
        equipo = Vector()
        if jugador.arma_equipada is not None:
            equipo.agregarValor(f"arma {jugador.arma_equipada.nombre}")
        if jugador.armadura_equipada is not None:
            equipo.agregarValor(f"armadura {jugador.armadura_equipada.nombre}")
        e(" Equipo: " + _unir(equipo, "nada equipado"))
        e(" Efectos: " + _unir(self._efectos(jugador), "ninguno"))
        e("-" * ANCHO)
        self._seccion("Salidas", self._salidas(partida, sala), "ninguna")
        self._seccion("Enemigos", self._enemigos(partida, sala), "ninguno")
        self._seccion("Suelo", self._suelo(sala), "nada")
        trampas = self._trampas(sala)
        if len(trampas):
            self._seccion("Trampas", trampas, "")
        e(f" Inventario ({len(jugador.inventario)}/{jugador.inventario_max}): "
          + _unir(self._inventario_corto(jugador), "vacío"))
        e("-" * ANCHO)
        lineas = self.mensajes()
        if not lineas:
            e(" (sin mensajes)")
        for linea in lineas:
            e(" " + linea)
        if len(self._panel):
            e("-" * ANCHO)
            for linea in self._panel:
                e(linea)
            self._panel = Vector()

    def _seccion(self, titulo, lineas, vacio):
        """Un elemento por renglón: así se lee el número para A/R sin contar."""
        if len(lineas) == 0:
            self._escribir(f" {titulo}: {vacio}")
            return
        self._escribir(f" {titulo}:")
        for linea in lineas:
            self._escribir(f"   {linea}")

    def _efectos(self, jugador):
        efectos = Vector()
        veneno = getattr(jugador, "estado_veneno", None)
        if veneno is not None:
            texto = (f"envenenado ({veneno.dano_por_pulso} por pulso, "
                     f"{veneno.pulsos_restantes} restantes")
            proximo = _pendiente(getattr(jugador, "evento_veneno", None))
            texto += f", próximo t={proximo})" if proximo is not None else ")"
            efectos.agregarValor(texto)
        fin = _pendiente(getattr(jugador, "evento_mod_velocidad", None))
        if fin is not None:
            efectos.agregarValor(f"velocidad alterada hasta t={fin}")
        for nodo in jugador.inventario.recorrer_desde_frente():
            objeto = nodo.valor
            if objeto.clase == "antorcha" and objeto.encendida:
                apagado = _pendiente(objeto.evento_apagado)
                efectos.agregarValor(f"{objeto.nombre} encendida"
                                     + (f" hasta t={apagado}" if apagado is not None else ""))
        return efectos

    def _salidas(self, partida, sala):
        salidas = Vector()
        for salida in sala.salidas:
            destino = salida.sala_destino
            if destino is None:
                destino = partida.cripta.sala_por_id(salida.sala_destino_id)
            nombre = destino.nombre if destino is not None else f"sala {salida.sala_destino_id}"
            if salida.cerrada:
                estado = "cerrada"
                if salida.llave is not None:
                    estado += ", tienes la llave" if partida.llave_para(salida) else ", sin llave"
            else:
                estado = "abierta"
                cierre = _pendiente(salida.evento_cierre)
                if cierre is not None:
                    estado += f", se cierra en t={cierre}"
            salidas.agregarValor(f"{salida.direccion}  {nombre} ({estado})")
        return salidas

    def _enemigos(self, partida, sala):
        enemigos = Vector()
        for i, enemigo in enumerate(sala.enemigos_activos, 1):
            enemigos.agregarValor(f"{i}. {partida.nombre_enemigo(enemigo)} "
                                  f"{enemigo.vida}/{enemigo.vida_max} {enemigo.comportamiento}")
        return enemigos

    def _suelo(self, sala):
        suelo = Vector()
        for i, objeto in enumerate(sala.objetos_suelo, 1):
            suelo.agregarValor(f"{i}. {objeto.nombre} ({describir_objeto(objeto)})")
        return suelo

    def _trampas(self, sala):
        trampas = Vector()
        for trampa in sala.trampas:
            if trampa.armada:
                trampas.agregarValor(f"{trampa.nombre} (armada)")
            else:
                rearme = _pendiente(trampa.evento_rearme)
                trampas.agregarValor(f"{trampa.nombre} (desarmada"
                                     + (f", se rearma en t={rearme})" if rearme is not None
                                        else ")"))
        return trampas

    @staticmethod
    def _marca(jugador, objeto):
        if objeto is jugador.arma_equipada or objeto is jugador.armadura_equipada:
            return " [equipada]"
        if objeto.clase == "antorcha" and objeto.encendida:
            return " [encendida]"
        return ""

    def _inventario_corto(self, jugador):
        objetos = Vector()
        for i, nodo in enumerate(jugador.inventario.recorrer_desde_frente(), 1):
            objetos.agregarValor(f"{i}. {nodo.valor.nombre}{self._marca(jugador, nodo.valor)}")
        return objetos


    def mostrar_inventario(self, partida, objetos, criterio):
        """objetos: lista propia ya en el orden pedido (real u ordenado)."""
        jugador = partida.jugador
        titulo = "orden real" if criterio is None else f"vista ordenada por {criterio}"
        panel = Vector()
        panel.agregarValor(f" Inventario ({titulo}) - "
                           f"{len(jugador.inventario)}/{jugador.inventario_max} espacios")
        if len(objetos) == 0:
            panel.agregarValor("   vacío")
        else:
            panel.agregarValor("   #  " + "Nombre".ljust(24) + "Peso".rjust(6)
                               + "Valor".rjust(7) + "  Detalle")
        for i, objeto in enumerate(objetos, 1):
            panel.agregarValor(f"  {str(i).rjust(2)}  " + objeto.nombre[:24].ljust(24)
                               + str(objeto.peso).rjust(6) + str(objeto.valor).rjust(7)
                               + "  " + describir_objeto(objeto) + self._marca(jugador, objeto))
        if criterio is not None and len(objetos):
            panel.agregarValor("  (los números de U/EQ/T siguen el orden real; usa I sin criterio)")
        self._panel = panel

    def mostrar_ayuda(self):
        panel = Vector()
        for linea in AYUDA.split("\n"):
            panel.agregarValor(linea)
        self._panel = panel


    def mostrar_fin(self, partida):
        e = self._escribir
        e("")
        e("=" * ANCHO)
        if partida.estado == "victoria":
            e(" ¡Victoria! Escapaste de la cripta.")
        elif partida.estado == "derrota":
            e(" Derrota: has muerto en la cripta.")
        else:
            e(" Partida terminada por el jugador.")
        e("=" * ANCHO)
        e(" Últimos mensajes:")
        for linea in self.mensajes():
            e("   " + linea)
        e(" Resumen:")
        for campo, valor in partida.resumen_puntaje():
            e(f"   {campo}: {valor}")


    def leer_comando(self):
        try:
            return self._leer("> ")
        except (EOFError, KeyboardInterrupt):
            return "Q"
