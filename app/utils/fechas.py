from datetime import datetime, timezone

MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


def ahora_utc():
    """Fecha y hora actual en UTC, sin zona horaria (igual en cualquier base de datos)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def formatear_fecha(fecha):
    """Convierte una fecha en texto legible: '15 de noviembre de 2026'. Vacío si no hay fecha."""
    if not fecha:
        return ""
    return f"{fecha.day} de {MESES[fecha.month - 1]} de {fecha.year}"