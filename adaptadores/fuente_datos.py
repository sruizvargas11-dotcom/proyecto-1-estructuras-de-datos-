"""
Adaptadores de red y disco detrás de una interfaz común.
El modelo sólo conoce FuendeDeDatos, nunca ningún request ni archivos directos.
"""

from abc import ABC, abstractmethod


class FuenteDeDatos(ABC):


    @abstractmethod
    def listar_criptas(self) -> dict:
            raise NotImplementedError

    @abstractmethod
    def datos_cripta(self, cripta_id: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def esqueleto_cripta(self, cripta_id: str, pagina: int) -> dict:
        raise NotImplementedError

    @abstractmethod
    def contenido_salas(self, cripta_id: str, sala_ids: list) -> dict:
        raise NotImplementedError

    @abstractmethod
    def catalogo(self, tipo_ids: list) -> dict:
        raise NotImplementedError

    @abstractmethod
    def version_cripta(self, cripta_id: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def version_catalogo(self) -> dict:
        raise NotImplementedError
