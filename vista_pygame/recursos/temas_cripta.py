"""Identidad visual local; no cambia datos ni reglas recibidos de la API."""
from dataclasses import dataclass
from pathlib import Path
import unicodedata


@dataclass(frozen=True)
class TemaCripta:
    clave: str
    titulo: str
    frase: str
    acento: tuple
    particula: tuple
    piedra: tuple = (46,54,64)

    def recurso(self,carpeta,tipo):
        ruta=Path(carpeta)/'escenarios'/self.clave/(tipo+'.png')
        if ruta.is_file():return ruta
        return Path(carpeta)/'escenarios/osario'/(tipo+'.png')


TEMAS=(
    TemaCripta('osario','Osario menor','Entre urnas y huesos, la piedra conserva sus nombres.',(218,188,125),(163,151,123)),
    TemaCripta('catacumbas_menores','Catacumbas menores','Las raíces alcanzan las tumbas que el tiempo olvidó.',(182,200,129),(118,156,118),(83,86,65)),
    TemaCripta('catacumbas_medias','Catacumbas medias','Bajo las bóvedas, una luz fría acompaña tus pasos.',(139,192,219),(103,173,190),(40,54,68)),
    TemaCripta('catacumbas_profundas','Catacumbas profundas','El silencio pesa bajo los cimientos del mundo.',(218,151,111),(190,107,79),(47,38,38)),
)


def tema_por_cripta(id_cripta='',nombre=''):
    for indice in range(4):
        if id_cripta==f'cripta-{indice+1:02}':return TEMAS[indice]
    texto=''.join(c for c in unicodedata.normalize('NFD',str(nombre)).casefold()
                  if unicodedata.category(c)!='Mn')
    for palabra,indice in (('osario',0),('profund',3),('media',2),('menor',1)):
        if palabra in texto:return TEMAS[indice]
    if not id_cripta or id_cripta=='cripta-prueba':return TEMAS[0]
    # Criptas nuevas sin descripción: asignación estable, también tras cargar.
    return TEMAS[sum((i+1)*ord(c) for i,c in enumerate(str(id_cripta)))%len(TEMAS)]


def tema_estado(estado):
    return tema_por_cripta(getattr(estado,'cripta_id',''),getattr(estado,'cripta_nombre',''))
