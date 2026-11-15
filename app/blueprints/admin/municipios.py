from flask import flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from ...extensions import db
from ...models import IndicadorMunicipio, Municipio
from ...utils.fechas import ahora_utc
from ...utils.texto import crear_slug
from . import bp
from .forms import IndicadorForm, MunicipioForm


def _aplicar_municipio(municipio, form):
    municipio.nombre = form.nombre.data
    municipio.slug = crear_slug(form.nombre.data)
    municipio.latitud = form.latitud.data
    municipio.longitud = form.longitud.data
    municipio.nivel_riesgo = form.nivel_riesgo.data or None
    municipio.estado_suministro = form.estado_suministro.data or None
    municipio.resumen = form.resumen.data or None
    municipio.recomendaciones = form.recomendaciones.data or None


def _aplicar_indicador(indicador, form):
    indicador.nombre = form.nombre.data
    indicador.valor = form.valor.data
    indicador.unidad = form.unidad.data or None
    indicador.periodo = form.periodo.data or None
    indicador.fuente = form.fuente.data or None
    indicador.orden = form.orden.data if form.orden.data is not None else 0


@bp.route("/municipios")
def municipios_lista():
    municipios = Municipio.query.order_by(Municipio.nombre).all()
    return render_template("admin/municipios/lista.html", municipios=municipios)


@bp.route("/municipios/nuevo", methods=["GET", "POST"])
def municipio_nuevo():
    form = MunicipioForm()
    if form.validate_on_submit():
        municipio = Municipio()
        _aplicar_municipio(municipio, form)
        db.session.add(municipio)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("No se pudo guardar: ya existe un municipio con ese nombre.", "danger")
        else:
            flash(f"Municipio «{municipio.nombre}» creado. Ya puedes agregarle indicadores.", "success")
            return redirect(url_for("admin.municipio_editar", municipio_id=municipio.id))
    return render_template("admin/municipios/formulario.html", form=form, municipio=None)


@bp.route("/municipios/<int:municipio_id>/editar", methods=["GET", "POST"])
def municipio_editar(municipio_id):
    municipio = db.get_or_404(Municipio, municipio_id)
    form = MunicipioForm(obj=municipio, municipio_id=municipio.id)
    if request.method == "GET":
        form.nivel_riesgo.data = municipio.nivel_riesgo or ""
    if form.validate_on_submit():
        _aplicar_municipio(municipio, form)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("No se pudo guardar: ya existe un municipio con ese nombre.", "danger")
        else:
            flash("Cambios guardados.", "success")
            return redirect(url_for("admin.municipio_editar", municipio_id=municipio.id))
    return render_template("admin/municipios/formulario.html", form=form, municipio=municipio)


@bp.route("/municipios/<int:municipio_id>/eliminar", methods=["POST"])
def municipio_eliminar(municipio_id):
    municipio = db.get_or_404(Municipio, municipio_id)
    nombre = municipio.nombre
    db.session.delete(municipio)
    db.session.commit()
    flash(f"Municipio «{nombre}» eliminado.", "success")
    return redirect(url_for("admin.municipios_lista"))


@bp.route("/municipios/<int:municipio_id>/indicadores/nuevo", methods=["GET", "POST"])
def indicador_nuevo(municipio_id):
    municipio = db.get_or_404(Municipio, municipio_id)
    form = IndicadorForm()
    if request.method == "GET":
        form.orden.data = len(municipio.indicadores) + 1
    if form.validate_on_submit():
        indicador = IndicadorMunicipio(municipio=municipio)
        _aplicar_indicador(indicador, form)
        municipio.actualizado_en = ahora_utc()
        db.session.add(indicador)
        db.session.commit()
        flash("Indicador agregado.", "success")
        return redirect(url_for("admin.municipio_editar", municipio_id=municipio.id))
    return render_template("admin/municipios/indicador_form.html", form=form, municipio=municipio, indicador=None)


@bp.route("/indicadores/<int:indicador_id>/editar", methods=["GET", "POST"])
def indicador_editar(indicador_id):
    indicador = db.get_or_404(IndicadorMunicipio, indicador_id)
    form = IndicadorForm(obj=indicador)
    if form.validate_on_submit():
        _aplicar_indicador(indicador, form)
        indicador.municipio.actualizado_en = ahora_utc()
        db.session.commit()
        flash("Indicador actualizado.", "success")
        return redirect(url_for("admin.municipio_editar", municipio_id=indicador.municipio_id))
    return render_template(
        "admin/municipios/indicador_form.html", form=form, municipio=indicador.municipio, indicador=indicador
    )


@bp.route("/indicadores/<int:indicador_id>/eliminar", methods=["POST"])
def indicador_eliminar(indicador_id):
    indicador = db.get_or_404(IndicadorMunicipio, indicador_id)
    municipio = indicador.municipio
    municipio.actualizado_en = ahora_utc()
    db.session.delete(indicador)
    db.session.commit()
    flash("Indicador eliminado.", "success")
    return redirect(url_for("admin.municipio_editar", municipio_id=municipio.id))