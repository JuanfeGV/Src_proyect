from datetime import datetime, timezone


def ahora_utc():
    """Fecha y hora actual en UTC, sin zona horaria (igual en cualquier base de datos)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)