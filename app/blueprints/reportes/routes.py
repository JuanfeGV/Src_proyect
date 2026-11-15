from flask import render_template

from . import bp


@bp.route("/reporte-ciudadano")
def index():
    # Este módulo lo desarrollará otro integrante del equipo.
    return render_template(
        "components/en_construccion.html",
        titulo="Reporte Ciudadano",
        mensaje="Módulo en desarrollo por otro integrante del equipo.",
    )