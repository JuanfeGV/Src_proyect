import re
import unicodedata

from markupsafe import Markup, escape


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


def a_parrafos(texto):
    """Convierte texto plano en HTML seguro: una línea en blanco separa párrafos
    y un salto de línea simple pasa a <br>. Todo el contenido se escapa antes."""
    if not texto:
        return Markup("")
    bloques = [b.strip() for b in re.split(r"\n\s*\n", texto.replace("\r\n", "\n")) if b.strip()]
    saltos = Markup("<br>")
    return Markup("".join(f"<p>{saltos.join(escape(l) for l in b.split(chr(10)))}</p>" for b in bloques))