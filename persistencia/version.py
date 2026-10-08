from pathlib import Path


class PersistenciaVersiones:
    def __init__(self, carpeta_base=None):
        if carpeta_base is None:
            raiz_proyecto = Path(__file__).resolve().parent.parent
            carpeta_base = raiz_proyecto / "partidas" / "cache"

        self._carpeta_base = Path(carpeta_base)

    def guardar_version_cripta(self, cripta_id, version):
        ruta = self._ruta_cripta(cripta_id)
        self._guardar(ruta, version)

    def version_cripta_local(self, cripta_id, version_actual=None):
        ruta = self._ruta_cripta(cripta_id)
        return self._leer(ruta, version_actual)

    def guardar_version_catalogo(self, version):
        ruta = self._carpeta_base / "catalogo_version.txt"
        self._guardar(ruta, version)

    def version_catalogo_local(self, version_actual=None):
        ruta = self._carpeta_base / "catalogo_version.txt"
        return self._leer(ruta, version_actual)

    def _ruta_cripta(self, cripta_id):
        if not isinstance(cripta_id, str) or not cripta_id.strip():
            raise ValueError("El identificador debe ser un texto no vacío.")

        if cripta_id in (".", "..") or any(
            caracter in cripta_id for caracter in '/\\:'
        ):
            raise ValueError("El identificador no puede contener una ruta.")

        return self._carpeta_base / cripta_id / "version.txt"

    def _guardar(self, ruta, version):
        if not isinstance(version, str) or not version.strip():
            raise ValueError("La versión debe ser un texto no vacío.")

        ruta.parent.mkdir(parents=True, exist_ok=True)
        temporal = ruta.with_suffix(".tmp")
        temporal.write_text(version.strip(), encoding="utf-8")
        temporal.replace(ruta)

    def _leer(self, ruta, version_actual):
        try:
            version_local = ruta.read_text(encoding="utf-8").strip()
        except (FileNotFoundError, UnicodeDecodeError):
            return None

        if not version_local:
            return None

        if version_actual is not None and version_local != version_actual:
            return None

        return version_local
