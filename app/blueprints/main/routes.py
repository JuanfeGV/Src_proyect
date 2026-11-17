from flask import render_template
from sqlalchemy.orm import selectinload

from ...models import Municipio
from ...services.consultas import (
    articulos_publicados,
    datos_mapa,
    evaluar_cobertura_municipal,
    municipios_ordenados,
)
from . import bp


@bp.route("/")
def inicio():
    municipios = municipios_ordenados().options(
        selectinload(Municipio.indicadores)
    ).all()
    return render_template(
        "main/inicio.html",
        municipios=municipios,
        municipios_inicio=[
            {
                "municipio": municipio,
                "evaluacion": evaluar_cobertura_municipal(municipio),
            }
            for municipio in municipios
        ],
        puntos_mapa=datos_mapa(municipios, incluir_indicadores=True),
        noticias=articulos_publicados().limit(3).all(),
    )