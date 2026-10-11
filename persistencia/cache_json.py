"""Formato común de caché; no es el formato binario de guardado de partida."""
import json
import os
import tempfile


def validar_identificador(valor):
    """Un identificador debe ser un nombre portable, nunca una ruta."""
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError('El identificador debe ser texto no vacío.')
    if valor in ('.', '..') or valor.endswith((' ', '.')) or any(
        c in valor for c in '/\\:<>"|?*'
    ) or any(ord(c) < 32 for c in valor):
        raise ValueError('El identificador no puede contener una ruta ni caracteres inválidos.')
    base = valor.split('.', 1)[0].rstrip(' ').upper()
    if base in ('CON', 'PRN', 'AUX', 'NUL') or (
        base[:3] in ('COM', 'LPT') and base[3:] in
        ('1', '2', '3', '4', '5', '6', '7', '8', '9', '¹', '²', '³')
    ):
        raise ValueError('El identificador es un nombre reservado de Windows.')


def guardar_cache(ruta, version, identificador, datos):
    documento = {'formato_cache': 1, 'version': version,
                 'identificador': identificador, 'datos': datos}
    # Serializar primero: un error de datos no toca la copia anterior.
    texto = json.dumps(documento, ensure_ascii=False, indent=2, allow_nan=False)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    temporal = None
    try:
        # Nombre único y mismo directorio: dos escritores no comparten temporal.
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                         dir=os.path.dirname(ruta),
                                         suffix='.tmp', delete=False) as archivo:
            temporal = archivo.name
            archivo.write(texto)
        os.replace(temporal, ruta)
    finally:
        if temporal is not None:
            try:
                os.remove(temporal)
            except OSError:
                pass


def cargar_cache(ruta, version, identificador):
    try:
        with open(ruta, encoding='utf-8') as archivo:
            documento = json.load(archivo)
    except (FileNotFoundError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(documento, dict):
        return None
    if type(documento.get('formato_cache')) is not int or documento['formato_cache'] != 1:
        return None
    if documento.get('version') != version or documento.get('identificador') != identificador:
        return None
    datos = documento.get('datos')
    return datos if isinstance(datos, dict) else None
