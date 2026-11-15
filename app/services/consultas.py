"""Consultas que usan las páginas públicas (solo lectura).

Las páginas públicas nunca muestran borradores: los artículos deben estar
publicados y las guías deben estar marcadas como publicadas.
"""
from flask import url_for

from ..models import Articulo, GuiaConsumo, Municipio, NodoArbol
from ..models.constantes import NIVELES_RIESGO
from ..utils.texto import normalizar

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


def datos_mapa(municipios):
    """Datos mínimos de cada municipio para dibujarlo en el mapa (solo los que tienen coordenadas)."""
    return [
        {
            "nombre": m.nombre,
            "slug": m.slug,
            "lat": m.latitud,
            "lng": m.longitud,
            "nivel": m.nivel_riesgo if m.nivel_riesgo in NIVELES_RIESGO else None,
            "suministro": m.estado_suministro,
            "url": url_for("municipios.ficha", slug=m.slug),
        }
        for m in municipios
        if m.latitud is not None and m.longitud is not None
    ]