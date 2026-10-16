import json
import os
from adaptadores.fuente_datos import FuenteDeDatos

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # La ruta parte del módulo para no depender del directorio de ejecución.
CARPETA_POR_DEFECTO = os.path.join(RAIZ, "datos_offline")

class DatosOffline(FuenteDeDatos):

    def __init__(self, carpeta=None):
        if carpeta is None:
            carpeta = CARPETA_POR_DEFECTO # Usa los datos incluidos en el repositorio si no se indica otra carpeta.
        self._carpeta = carpeta
        if not os.path.exists(self._carpeta):
            raise FileNotFoundError(
                f"Carpeta '{self._carpeta}' no encontrada. "
                f"Verifica que la carpeta '{self._carpeta}' exista en la raíz del "
                "proyecto y contenga los archivos JSON de la cripta."
            )


    def _leer(self, nombre_archivo):
        ruta = os.path.join(self._carpeta, nombre_archivo)
        if not os.path.exists(ruta):
            raise FileNotFoundError(f"Archivo offline no encontrado: '{ruta}'. ")
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)



    def descargada(self, cripta_id):
        """True si la cripta tiene su carpeta con los datos generales."""
        return (isinstance(cripta_id, str) and bool(cripta_id)
                and os.path.isfile(os.path.join(self._carpeta, cripta_id, "general.json")))

    def listar_criptas(self):
        """Solo las criptas que se pueden jugar sin conexión.

        criptas.json lo escribe descargar_offline con la lista completa del API,
        aunque solo se haya bajado una cripta; las que no tienen carpeta se omiten
        para no ofrecer en el menú una cripta que fallaría al cargarse.
        """
        respuesta = self._leer("criptas.json")
        if not isinstance(respuesta, dict) or not isinstance(respuesta.get("criptas"), list):
            return respuesta          # formato inválido: que lo reporte quien lo valida
        disponibles = [c for c in respuesta["criptas"]
                       if isinstance(c, dict) and self.descargada(c.get("id"))]
        if respuesta["criptas"] and not disponibles:
            raise FileNotFoundError(
                f"Ninguna cripta de criptas.json está descargada en '{self._carpeta}'. "
                "Descarga una con: python -m herramientas.descargar_offline <cripta_id>")
        # respuesta se acaba de leer del archivo: se ajusta ella misma, sin copiarla.
        respuesta["criptas"] = disponibles
        return respuesta

    # Cada método lee los archivos que corresponden a la misma consulta en HTTP.

    def datos_cripta(self, cripta_id):
        if not cripta_id:
            raise ValueError("informacion de cripta vacia ")
        return self._leer(os.path.join(cripta_id, "general.json"))

    def esqueleto_cripta(self, cripta_id, pagina):
        if not cripta_id:
            raise ValueError("id de la cripta no puede ser vacio.")
        if pagina < 1:
            raise ValueError(f"numero pagina invalido {pagina}")
        return self._leer(os.path.join(cripta_id, f"salas_p{pagina}.json"))

    def contenido_salas(self, cripta_id, sala_ids):
        if not sala_ids:
            raise ValueError("sala_ids no puede estar vacío.")
        if len(sala_ids) > 10:
            raise ValueError(
                f"Máximo 10 salas por consulta, recibido: {len(sala_ids)}"
            )
        resultado = [] # Conserva el orden de las salas solicitado por el controlador.
        for sala_id in sala_ids:
            ruta = os.path.join(cripta_id, "contenido", f"sala_{sala_id}.json")
            resultado.append(self._leer(ruta))
        return {"contenido": resultado}

    def catalogo(self, tipo_ids):
        if not tipo_ids:
            raise ValueError("tipo_ids no puede estar vacío.")
        if len(tipo_ids) > 10:
            raise ValueError(
                f"Máximo 10 ids por consulta, recibido: {len(tipo_ids)}"
            )
        resultado = [] # Conserva el orden de los tipos solicitado por el controlador.
        for tipo_id in tipo_ids:
            ruta = os.path.join("catalogo", f"{tipo_id}.json")
            resultado.append(self._leer(ruta))
        return {"entidades": resultado}

    def version_cripta(self, cripta_id):
        if not cripta_id:
            raise ValueError("id de la cripta  no puede estar vacio.")
        return self._leer(os.path.join(cripta_id, "version.json"))

    def version_catalogo(self):
        return self._leer("catalogo_version.json")

    def modo(self):
        return "offline"


# Las pruebas iniciales de este adaptador se elaboraron con asistencia de Claude.


