import json
import os
from adaptadores.fuente_datos import FuenteDeDatos

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # implementacion de ruta absoluta
CARPETA_POR_DEFECTO = os.path.join(RAIZ, "datos_offline")

class DatosOffline(FuenteDeDatos):

    def __init__(self, carpeta=None):
        if carpeta is None:
            carpeta = CARPETA_POR_DEFECTO # aqui se modifica el acceso a ruta previo por el de la ruta absoluta
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



    def listar_criptas(self):
        return self._leer("criptas.json")

    # QUE CAMBIÓ:
    # los metodos retornan exactamente lo mismo que su estado previo
    # pero se adaptó cómo se accede a los archivos y los retornos vienen formateados
    # para que el metodo lean el contenido de la ruta de los archivos a leer

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
        resultado = [] # se guardan en una "lista" los contenidos de cada sala que se vaya leyendo
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
        resultado = [] # se guardan en una "lista" las entidades de cada tipo a los que el metodo vaya accediendo
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


""" la informacion recibida de la api se almacena en un json, un json por cada get basicamente
se hace un wrapper funcion que guarda un json normal y se implementa y se llama en el resto de metodos
 ,validaciones que pide el profe en el enunciado en las demas funciones heredadas se llama al
 wrapper y con el archivo por leer,manejo de excepciones en caso de errores 
 




"""


