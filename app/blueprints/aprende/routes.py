from flask import render_template

from . import bp


@bp.route("/aprende")
def index():
    return render_template(
        "components/en_construccion.html",
        titulo="Aprende",
        mensaje="Aquí estará el árbol del problema hídrico y las guías de consumo responsable.",
    )