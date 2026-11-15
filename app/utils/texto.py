import re
import unicodedata


def normalizar(texto):
    """Minúsculas, sin tildes y sin espacios repetidos. Sirve para buscar."""
    if not texto:
        return ""
    descompuesto = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join(c for c in descompuesto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sin_tildes.lower()).strip()


def crear_slug(texto):
    """Convierte 'Chía y Cajicá' en 'chia-y-cajica' (para usar en las URL)."""
    return re.sub(r"[^a-z0-9]+", "-", normalizar(texto)).strip("-")