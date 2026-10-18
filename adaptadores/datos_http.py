"""Consultas al servicio de CRIPTA, con control de presupuesto y reintentos."""

import time
import uuid

import requests

from adaptadores.fuente_datos import FuenteDeDatos

BASE_URL = "https://cripta-api.kad06a0zhgs84.us-east-2.cs.amazonlightsail.com/v1"
# Una identidad por ejecución, compartida por todas sus partidas y reintentos.
CLIENT_ID_EJECUCION = str(uuid.uuid4())

class DatosHTTP(FuenteDeDatos):
    """Obtiene los datos de la cripta a través de la interfaz FuenteDeDatos."""

    def __init__(self, max_reintentos=3):
        if type(max_reintentos) is not int or max_reintentos < 0:
            raise ValueError("max_reintentos debe ser un entero no negativo")
        self._max_reintentos = max_reintentos
        self._base_url = BASE_URL
        self._client_id = CLIENT_ID_EJECUCION
        self._headers = {"X-Cripta-Client-Id": self._client_id}
        self._contador = 0
        self._presupuesto = None



    def para_nueva_partida(self):
        """Otra partida con la misma identidad; conserva las métricas del anterior."""
        return DatosHTTP(max_reintentos=self._max_reintentos)

    @staticmethod
    def _leer_json(respuesta, ruta):
        contexto = f'GET {ruta} (HTTP {respuesta.status_code})'
        try:
            datos = respuesta.json()
        except ValueError as error:
            raise ValueError(f'{contexto}: no se pudo interpretar la respuesta JSON.') from error
        if not isinstance(datos, dict):
            raise ValueError(f'{contexto}: respuesta JSON inválida; se esperaba un objeto.')
        return datos

    def _get(self, ruta: str, params: dict = None) -> dict:
        """Ejecuta un GET y cuenta cada intento dentro del presupuesto disponible."""
        reintentos = 0
        while True:
            if self._presupuesto is not None and self._contador >= self._presupuesto:
                raise RuntimeError(f"Presupuesto de solicitudes agotado al consultar GET {ruta}.")
            self._contador += 1
            try:
                respuesta = requests.get(
                    f"{self._base_url}{ruta}", headers=self._headers,
                    params=params, timeout=10,
                )
            except requests.RequestException as error:
                raise RuntimeError(f"No se pudo consultar {ruta}: {error}") from error

            if respuesta.status_code == 200:
                return self._leer_json(respuesta, ruta)

            if respuesta.status_code == 429:
                if reintentos >= self._max_reintentos:
                    raise RuntimeError(f"GET {ruta}: el servidor sigue ocupado; límite de reintentos alcanzado.")
                if self._presupuesto is not None and self._contador >= self._presupuesto:
                    raise RuntimeError(f"Presupuesto de solicitudes agotado al consultar GET {ruta}.")
                datos = self._leer_json(respuesta, ruta)
                espera = datos.get("reintentar_en", 5)
                if type(espera) not in (int, float) or not 0 <= espera <= 60:
                    raise ValueError("Intervalo de reintento inválido o mayor de 60 segundos.")
                time.sleep(espera)
                reintentos += 1
                continue

            raise RuntimeError(
                f"GET {ruta} falló con status {respuesta.status_code}: {respuesta.text}"
            )



    def listar_criptas(self) -> dict:
        """Consulta las criptas disponibles."""
        return self._get("/criptas")


    def datos_cripta(self, cripta_id: str) -> dict:
        """Obtiene los datos generales y establece el presupuesto de solicitudes."""
        respuesta = self._get(f"/criptas/{cripta_id}")
        presupuesto = respuesta.get("presupuesto_solicitudes")
        if type(presupuesto) is not int or presupuesto < 0:
            raise ValueError("Presupuesto de solicitudes inválido.")
        self._presupuesto = presupuesto
        if self._contador > presupuesto:
            raise RuntimeError("La carga inicial ya excedió el presupuesto informado.")
        return respuesta


    def esqueleto_cripta(self, cripta_id: str, pagina: int) -> dict:
        """Consulta una página del mapa de salas."""
        return self._get(f"/criptas/{cripta_id}/salas", params={"pagina": pagina})

    def contenido_salas(self, cripta_id: str, sala_ids: list) -> dict:
        """Obtiene el contenido de un lote de hasta 10 salas."""
        if not sala_ids or len(sala_ids) > 10:
            raise ValueError("tope de maximo 10 salas por solicitud")
        salas = ",".join(str(s) for s in sala_ids)
        return self._get(f"/criptas/{cripta_id}/contenido", params={"salas": salas})

    def catalogo(self, tipo_ids: list) -> dict:
        """Consulta hasta 10 fichas del catálogo por sus identificadores."""
        if not tipo_ids or len(tipo_ids) > 10:
            raise ValueError("Máximo 10 ids por solicitud")
        ids = ",".join(tipo_ids)
        return self._get("/catalogo", params={"ids": ids})

    def version_cripta(self, cripta_id: str) -> dict:
        """Consulta la versión actual de la cripta."""
        return self._get(f"/criptas/{cripta_id}/version")

    def version_catalogo(self) -> dict:
        """Consulta la versión actual del catálogo."""
        return self._get("/catalogo/version")

    # Métricas del cliente para el reporte de solicitudes.
    @property
    def requests_realizados(self) -> int:
        return self._contador

    @property
    def presupuesto(self) -> int:
        return self._presupuesto if self._presupuesto is not None else 0

    @property
    def dentro_del_presupuesto(self) -> bool:
        if self._presupuesto is None:
            return True
        return self._contador <= self._presupuesto

    def reporte(self) -> dict:
        return {
            "client_id": self._client_id,
            "requests_realizados": self._contador,
            "presupuesto": self.presupuesto,
            "dentro_del_limite": self.dentro_del_presupuesto,
        }


# Las pruebas iniciales de este adaptador se elaboraron con asistencia de IA.
