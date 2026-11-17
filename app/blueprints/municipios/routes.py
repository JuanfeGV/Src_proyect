from flask import render_template, request
from sqlalchemy import or_
from sqlalchemy.orm import selectinload

from ...models import Articulo, Municipio
from ...models.constantes import NIVELES_RIESGO
from ...services.consultas import (
    ETIQUETAS_PRIORIDAD_COBERTURA,
    LARGO_MAXIMO_BUSQUEDA,
    articulos_publicados,
    datos_mapa,
    evaluar_cobertura_municipal,
    evaluar_recurrencia_municipal,
    filtrar_por_texto,
    guias_publicadas,
)
from . import bp


@bp.route("/municipios")
def index():
    q = request.args.get("q", "").strip()[:LARGO_MAXIMO_BUSQUEDA]
    nivel = request.args.get("nivel", "").strip().lower()
    slug = request.args.get("municipio", "").strip()
    prioridad_cobertura = request.args.get("prioridad_cobertura", "").strip().lower()
    if prioridad_cobertura not in (*ETIQUETAS_PRIORIDAD_COBERTURA, "sin-evaluar"):
        prioridad_cobertura = ""
    municipios_disponibles = (
        Municipio.query.options(selectinload(Municipio.indicadores))
        .order_by(Municipio.nombre)
        .all()
    )

    consulta = Municipio.query.options(selectinload(Municipio.indicadores))
    municipio_seleccionado = next((m for m in municipios_disponibles if m.slug == slug), None)
    if municipio_seleccionado:
        consulta = consulta.filter(Municipio.id == municipio_seleccionado.id)
    if nivel in NIVELES_RIESGO:
        consulta = consulta.filter(Municipio.nivel_riesgo == nivel)
    elif nivel == "sin-evaluar":
        consulta = consulta.filter(or_(Municipio.nivel_riesgo.is_(None), Municipio.nivel_riesgo == ""))
    else:
        nivel = ""
    consulta = filtrar_por_texto(consulta, Municipio, q)

    municipios = consulta.order_by(Municipio.nombre).all()
    municipios_comparacion = [
        {
            "municipio": municipio,
            "evaluacion": evaluar_cobertura_municipal(municipio),
            "recurrencia": evaluar_recurrencia_municipal(municipio),
        }
        for municipio in municipios
    ]
    if prioridad_cobertura == "sin-evaluar":
        municipios_comparacion = [
            fila
            for fila in municipios_comparacion
            if fila["evaluacion"]["prioridad"] is None
        ]
    elif prioridad_cobertura:
        municipios_comparacion = [
            fila
            for fila in municipios_comparacion
            if fila["evaluacion"]["prioridad"] == prioridad_cobertura
        ]
    municipios = [fila["municipio"] for fila in municipios_comparacion]

    return render_template(
        "municipios/index.html",
        municipios=municipios,
        municipios_comparacion=municipios_comparacion,
        municipios_disponibles=municipios_disponibles,
        municipio_seleccionado=municipio_seleccionado,
        puntos_mapa=datos_mapa(
            municipios,
            municipio_seleccionado=municipio_seleccionado,
            incluir_indicadores=True,
        ),
        q=q,
        nivel=nivel,
        prioridad_cobertura=prioridad_cobertura,
    )


@bp.route("/municipios/<slug>")
def ficha(slug):
    municipio = (
        Municipio.query.options(selectinload(Municipio.indicadores))
        .filter_by(slug=slug)
        .first_or_404()
    )
    evaluado = municipio.nivel_riesgo in NIVELES_RIESGO
    guias = guias_publicadas(municipio.nivel_riesgo if evaluado else None, solo_generales=not evaluado).all()
    noticias = articulos_publicados().filter(Articulo.municipio_id == municipio.id).limit(4).all()
    return render_template(
        "municipios/ficha.html",
        municipio=municipio,
        evaluacion_cobertura=evaluar_cobertura_municipal(municipio),
        evaluado=evaluado,
        guias=guias,
        noticias=noticias,
        puntos_mapa=datos_mapa([municipio], municipio_seleccionado=municipio),
    )