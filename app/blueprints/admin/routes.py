from flask import render_template

from ...models import Articulo, GuiaConsumo, Municipio, NodoArbol
from . import bp


@bp.route("/")
def panel():
    return render_template(
        "admin/panel.html",
        total_municipios=Municipio.query.count(),
        sin_evaluar=Municipio.query.filter(Municipio.nivel_riesgo.is_(None)).count(),
        total_articulos=Articulo.query.count(),
        total_guias=GuiaConsumo.query.count(),
        total_nodos=NodoArbol.query.count(),
    )