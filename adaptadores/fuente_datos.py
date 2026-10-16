"""Interfaz común para consultar criptas y catálogos desde HTTP o archivos locales."""

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
