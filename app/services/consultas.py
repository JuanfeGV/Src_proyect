"""Consultas que usan las páginas públicas (solo lectura).

Las páginas públicas nunca muestran borradores: los artículos deben estar
publicados y las guías deben estar marcadas como publicadas.
"""
import math

from flask import url_for

from ..models import Articulo, GuiaConsumo, Municipio, NodoArbol
from ..models.constantes import NIVELES_RIESGO
from ..utils.texto import normalizar
from .semilla import MUNICIPIOS

LARGO_MAXIMO_BUSQUEDA = 100
LARGO_MINIMO_BUSQUEDA = 2
MAXIMO_PALABRAS = 6


def palabras_busqueda(texto):
    """Divide lo que escribió la persona en palabras normalizadas (sin tildes ni mayúsculas)."""
    normalizado = normalizar((texto or "")[:LARGO_MAXIMO_BUSQUEDA])
    return normalizado.split(" ")[:MAXIMO_PALABRAS] if normalizado else []


def filtrar_por_texto(consulta, modelo, texto):
    """Deja solo los registros que contienen TODAS las palabras buscadas.
    autoescape=True evita que '%' o '_' escritos por la persona actúen como comodines."""
    for palabra in palabras_busqueda(texto):
        consulta = consulta.filter(modelo.texto_busqueda.contains(palabra, autoescape=True))
    return consulta


def articulos_publicados():
    return Articulo.query.filter(Articulo.publicado.is_(True)).order_by(
        Articulo.fecha_publicacion.desc(), Articulo.id.desc()
    )


def guias_publicadas(nivel=None, solo_generales=False):
    """Guías visibles al público.

    - nivel 'bajo', 'medio' o 'alto': las de ese nivel y las que aplican a todos.
    - solo_generales=True: únicamente las que aplican a todos los niveles
      (se usa con municipios todavía sin nivel de riesgo evaluado).
    - sin filtros: todas.
    """
    consulta = GuiaConsumo.query.filter(GuiaConsumo.publicada.is_(True))
    if solo_generales:
        consulta = consulta.filter(GuiaConsumo.nivel_riesgo == "todos")
    elif nivel in NIVELES_RIESGO:
        consulta = consulta.filter(GuiaConsumo.nivel_riesgo.in_([nivel, "todos"]))
    return consulta.order_by(GuiaConsumo.orden, GuiaConsumo.id)


def municipios_ordenados():
    return Municipio.query.order_by(Municipio.nombre)


def estructura_arbol():
    """Arma el árbol del problema listo para mostrar.

    Devuelve un diccionario con:
      central: el nodo del problema central (o None si todavía no hay árbol)
      efectos: lista de (efecto directo, [efectos indirectos])
      causas:  lista de (causa directa, [causas indirectas])
    """

    def ramas(tipo_directo, tipo_indirecto):
        directos = (
            NodoArbol.query.filter_by(tipo=tipo_directo).order_by(NodoArbol.orden, NodoArbol.id).all()
        )
        return [(d, [h for h in d.hijos if h.tipo == tipo_indirecto]) for d in directos]

    central = (
        NodoArbol.query.filter_by(tipo="problema_central").order_by(NodoArbol.orden, NodoArbol.id).first()
    )
    return {
        "central": central,
        "efectos": ramas("efecto_directo", "efecto_indirecto"),
        "causas": ramas("causa_directa", "causa_indirecta"),
    }


def _coordenadas_validas(latitud, longitud):
    try:
        latitud = float(latitud)
        longitud = float(longitud)
    except (TypeError, ValueError, OverflowError):
        return None

    if not (
        math.isfinite(latitud)
        and math.isfinite(longitud)
        and -90 <= latitud <= 90
        and -180 <= longitud <= 180
    ):
        return None
    return latitud, longitud


_COORDENADAS_SEMILLA = {
    nombre: (latitud, longitud) for nombre, latitud, longitud in MUNICIPIOS
}


def datos_mapa(municipios, municipio_seleccionado=None):
    """Prepara ubicaciones válidas y usa coordenadas semilla solo si faltan en la BD."""
    puntos = []
    for municipio in municipios:
        if municipio.latitud is None or municipio.longitud is None:
            coordenadas = _COORDENADAS_SEMILLA.get(municipio.nombre)
        else:
            coordenadas = _coordenadas_validas(municipio.latitud, municipio.longitud)

        if coordenadas is None:
            continue

        latitud, longitud = coordenadas
        puntos.append(
            {
                "nombre": municipio.nombre,
                "slug": municipio.slug,
                "lat": latitud,
                "lng": longitud,
                "nivel": municipio.nivel_riesgo if municipio.nivel_riesgo in NIVELES_RIESGO else None,
                "suministro": municipio.estado_suministro,
                "resumen": municipio.resumen,
                "seleccionado": (
                    municipio_seleccionado is not None
                    and municipio.id == municipio_seleccionado.id
                ),
                "url": url_for("municipios.ficha", slug=municipio.slug),
            }
        )
    return puntos