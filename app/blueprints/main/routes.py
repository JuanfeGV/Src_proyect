from flask import render_template

from ...services.consultas import articulos_publicados, datos_mapa, estructura_arbol, municipios_ordenados
from . import bp


@bp.route("/")
def inicio():
    municipios = municipios_ordenados().all()
    return render_template(
        "main/inicio.html",
        arbol=estructura_arbol(),
        municipios=municipios,
        puntos_mapa=datos_mapa(municipios),
        noticias=articulos_publicados().limit(3).all(),
    )