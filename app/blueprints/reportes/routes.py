import logging
import smtplib

from flask import abort, flash, redirect, render_template, url_for
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from wtforms import SelectChoice

from ...extensions import db
from ...models import Municipio, ReporteCiudadano
from ...services.notificaciones import EmailAvisoNoConfiguradoError, enviar_aviso_reporte
from . import bp
from .forms import ReporteCiudadanoForm

logger = logging.getLogger(__name__)


def _error_base_datos():
    return (
        render_template(
            "errors/error.html",
            codigo=503,
            titulo="Servicio temporalmente no disponible",
            texto="No fue posible acceder a los datos. Intenta de nuevo más tarde.",
        ),
        503,
    )


@bp.route("/reporte-ciudadano", methods=["GET", "POST"])
def index():
    form = ReporteCiudadanoForm()
    try:
        municipios = db.session.scalars(select(Municipio).order_by(Municipio.nombre)).all()
    except SQLAlchemyError:
        db.session.rollback()
        logger.exception("No se pudieron consultar los municipios para el formulario de reportes.")
        return _error_base_datos()

    form.municipio_id.choices = [
        SelectChoice("0", "Selecciona un municipio")
    ] + [
        SelectChoice(str(municipio.id), municipio.nombre) for municipio in municipios
    ]

    if form.validate_on_submit():
        if form.sitio_web.data:
            abort(400)

        try:
            municipio = db.session.get(Municipio, form.municipio_id.data)
            if municipio is None:
                form.municipio_id.errors.append("Selecciona un municipio válido.")
                return render_template("reportes/formulario.html", form=form), 400

            reporte = ReporteCiudadano(
                municipio=municipio.nombre,
                barrio=form.barrio.data,
                tipo_falla=form.tipo_falla.data,
                descripcion=form.descripcion.data,
            )
            db.session.add(reporte)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            logger.exception("No se pudo guardar el reporte ciudadano.")
            return _error_base_datos()

        try:
            enviar_aviso_reporte(reporte)
        except EmailAvisoNoConfiguradoError:
            logger.warning("No se envió aviso por correo para el reporte %s: falta configuración SMTP.", reporte.id)
            flash(
                "Tu reporte quedó registrado, pero el aviso por correo está pendiente de configuración.",
                "warning",
            )
        except (OSError, smtplib.SMTPException):
            logger.exception("No se pudo enviar el aviso por correo para el reporte %s.", reporte.id)
            flash(
                "Tu reporte quedó registrado, pero no se pudo enviar el aviso por correo.",
                "warning",
            )
        else:
            flash("Tu reporte quedó registrado y se notificó al equipo.", "success")

        return redirect(url_for("reportes.confirmacion"))

    return render_template("reportes/formulario.html", form=form)


@bp.route("/reporte-ciudadano/confirmacion")
def confirmacion():
    return render_template("reportes/confirmacion.html")
