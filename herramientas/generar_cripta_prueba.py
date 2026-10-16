"""Crea datos de ensayo separados. Nunca cambia la cripta oficial/offline.

python -m herramientas.generar_cripta_prueba CARPETA_NUEVA
Luego: python main.py --offline --offline-dir CARPETA_NUEVA
"""
import json
import shutil
from pathlib import Path


def generar(destino):
    destino = Path(destino)
    if destino.exists():
        raise ValueError('Usa una carpeta nueva para no sobrescribir datos.')
    origen = Path(__file__).resolve().parents[1] / 'datos_offline'
    shutil.copytree(origen, destino)
    (destino / 'cripta-01').rename(destino / 'cripta-prueba')

    def leer(ruta):
        return json.loads((destino / ruta).read_text(encoding='utf-8'))

    def escribir(ruta, datos):
        (destino / ruta).write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding='utf-8')

    escribir('criptas.json', {'criptas': [{'id': 'cripta-prueba',
             'nombre': 'Laboratorio de consola (NO balance oficial)', 'salas': 6, 'dificultad': 0}]})
    generales = leer('cripta-prueba/general.json')
    generales.update(id='cripta-prueba', version='laboratorio-consola-v1')
    generales['jugador'].update(vida_max=300, ataque=30, defensa=15)
    escribir('cripta-prueba/general.json', generales)
    escribir('cripta-prueba/version.json', {'version': 'laboratorio-consola-v1'})
    escribir('catalogo_version.json', {'version': 'laboratorio-catalogo-v1'})
    escribir('catalogo/itm_velocidad_prueba.json', {
        'id': 'itm_velocidad_prueba', 'clase': 'pocion', 'nombre': 'Velocidad de ensayo',
        'peso': 1, 'valor': 12, 'cura': 0, 'modificador_velocidad': 20, 'duracion': 150})
    sala = leer('cripta-prueba/contenido/sala_1.json')
    sala['objetos'] = ['itm_antorcha', 'itm_daga_oxidada', 'itm_pocion_menor',
                       'itm_llave_bronce', 'itm_pergamino_retroceso',
                       'itm_antidoto', 'itm_velocidad_prueba']
    escribir('cripta-prueba/contenido/sala_1.json', sala)
    return destino


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destino')
    generar(parser.parse_args().destino)
