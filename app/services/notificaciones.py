import smtplib
import ssl
from email.message import EmailMessage

from flask import current_app


class EmailAvisoNoConfiguradoError(RuntimeError):
    pass


def enviar_aviso_reporte(reporte):
    configuracion = current_app.config
    servidor = configuracion.get("SMTP_SERVER")
    remitente = configuracion.get("SMTP_SENDER")
    destinatario = configuracion.get("EMAIL_REPORTS_TO")
    usuario = configuracion.get("SMTP_USERNAME")
    clave = configuracion.get("SMTP_PASSWORD")

    if not servidor or not remitente or not destinatario:
        raise EmailAvisoNoConfiguradoError("Falta configurar el servidor, remitente o destinatario.")
    if bool(usuario) != bool(clave):
        raise EmailAvisoNoConfiguradoError("SMTP_USERNAME y SMTP_PASSWORD deben configurarse juntos.")
    if not configuracion.get("SMTP_USE_TLS", True):
        raise EmailAvisoNoConfiguradoError("Las notificaciones SMTP deben usar TLS.")

    mensaje = EmailMessage()
    mensaje["Subject"] = f"Nuevo reporte ciudadano #{reporte.id}"
    mensaje["From"] = remitente
    mensaje["To"] = destinatario
    mensaje.set_content(
        "\n".join(
            [
                "Se recibió un nuevo reporte ciudadano.",
                "",
                f"Municipio: {reporte.municipio}",
                f"Barrio o vereda: {reporte.barrio}",
                f"Tipo de falla: {reporte.tipo_falla}",
                f"Fecha de recepción (UTC): {reporte.creado_en.isoformat()}",
                "",
                "Descripción:",
                reporte.descripcion,
            ]
        )
    )

    with smtplib.SMTP(servidor, configuracion.get("SMTP_PORT", 587), timeout=10) as smtp:
        smtp.ehlo()
        smtp.starttls(context=ssl.create_default_context())
        smtp.ehlo()
        if usuario:
            smtp.login(usuario, clave)
        smtp.send_message(mensaje)
