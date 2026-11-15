from flask import render_template

from . import bp


@bp.route("/municipios")
def index():
    return render_template(
        "components/en_construccion.html",
        titulo="Municipios",
        mensaje="Aquí estarán el buscador, el mapa y la ficha de cada municipio de Sabana Centro.",
    )
