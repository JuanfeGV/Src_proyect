from flask import render_template

from . import bp


@bp.route("/noticias")
def index():
    return render_template(
        "components/en_construccion.html",
        titulo="Noticias",
        mensaje="Aquí estarán las noticias y artículos sobre la cuenca del río Bogotá.",
    )
