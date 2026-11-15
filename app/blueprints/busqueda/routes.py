from flask import render_template, request

from ...models import GuiaConsumo, Municipio, NodoArbol
from ...models.articulo import Articulo
from ...services.consultas import (
    LARGO_MAXIMO_BUSQUEDA,
    LARGO_MINIMO_BUSQUEDA,
    articulos_publicados,
    filtrar_por_texto,
    guias_publicadas,
)
from ...utils.texto import normalizar
from . import bp

LIMITE_POR_GRUPO = 20


@bp.route("/buscar")
def index():
    q = request.args.get("q", "").strip()[:LARGO_MAXIMO_BUSQUEDA]
    resultados = None
    muy_corta = False

    if q and len(normalizar(q)) < LARGO_MINIMO_BUSQUEDA:
        muy_corta = True
    elif q:
        resultados = {
            "municipios": filtrar_por_texto(Municipio.query.order_by(Municipio.nombre), Municipio, q)
            .limit(LIMITE_POR_GRUPO)
            .all(),
            "articulos": filtrar_por_texto(articulos_publicados(), Articulo, q).limit(LIMITE_POR_GRUPO).all(),
            "guias": filtrar_por_texto(guias_publicadas(), GuiaConsumo, q).limit(LIMITE_POR_GRUPO).all(),
            "nodos": filtrar_por_texto(
                NodoArbol.query.order_by(NodoArbol.tipo, NodoArbol.orden), NodoArbol, q
            )
            .limit(LIMITE_POR_GRUPO)
            .all(),
        }
        resultados["total"] = sum(len(lista) for lista in resultados.values())

    return render_template(
        "busqueda/resultados.html", q=q, resultados=resultados, muy_corta=muy_corta,
        minimo=LARGO_MINIMO_BUSQUEDA,
    )