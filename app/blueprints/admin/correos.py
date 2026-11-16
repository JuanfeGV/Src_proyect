from flask import abort, current_app, render_template

from ...services.correos_imap import (
    ErrorCorreoIMAP,
    MensajeNoEncontrado,
    listar_mensajes,
    obtener_mensaje,
)
from . import bp


@bp.route("/correos")
def correos_lista():
    try:
        mensajes = listar_mensajes()
    except ErrorCorreoIMAP as error:
        current_app.logger.warning(
            "No se pudo consultar la bandeja IMAP (%s).",
            type(error).__name__,
        )
        return (
            render_template(
                "admin/correos/lista.html",
                mensajes=[],
                error="No fue posible acceder a la bandeja de entrada. Verifica la configuración IMAP.",
            ),
            503,
        )

    return render_template("admin/correos/lista.html", mensajes=mensajes, error=None)


@bp.route("/correos/<int:uid>")
def correo_detalle(uid):
    try:
        mensaje = obtener_mensaje(uid)
    except MensajeNoEncontrado:
        abort(404)
    except ErrorCorreoIMAP as error:
        current_app.logger.warning(
            "No se pudo consultar el mensaje IMAP (%s).",
            type(error).__name__,
        )
        return (
            render_template(
                "admin/correos/detalle.html",
                mensaje=None,
                error="No fue posible consultar el mensaje. Intenta actualizar la bandeja.",
            ),
            503,
        )

    return render_template("admin/correos/detalle.html", mensaje=mensaje, error=None)
