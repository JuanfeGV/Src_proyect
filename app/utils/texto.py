import re
import unicodedata
from urllib.parse import urlsplit

from markupsafe import Markup, escape

_PATRON_URL = re.compile(
    r"""https?://[^\s<>"']+|www\.[^\s<>"']+|(?<![\w@:/<])(?:\.\.?/|/(?!/))[^\s<>"']+|(?<![\w@:/<])#[A-Za-z0-9][\w:.-]*""",
    re.IGNORECASE,
)


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


def enlaces_seguros(texto):
    """Escapa texto plano y enlaza solo URLs web o rutas internas reconocidas."""
    if texto is None:
        return Markup("")

    valor = str(texto)
    partes = []
    inicio = 0
    for coincidencia in _PATRON_URL.finditer(valor):
        candidato = coincidencia.group(0)
        url = _recortar_puntuacion(candidato)
        destino = _destino_seguro(url)
        if destino is None:
            continue

        fin = coincidencia.start() + len(url)
        partes.append(escape(valor[inicio:coincidencia.start()]))
        href, externo = destino
        atributos = (
            Markup(' target="_blank" rel="noopener noreferrer"')
            if externo
            else Markup("")
        )
        partes.append(
            Markup('<a href="{}"{}>{}</a>').format(
                escape(href), atributos, escape(url)
            )
        )
        inicio = fin

    partes.append(escape(valor[inicio:]))
    return Markup("").join(partes)


def _recortar_puntuacion(url):
    while url.endswith((".", ",", ";", ":", "!", "?")):
        url = url[:-1]

    pares = (("(", ")"), ("[", "]"), ("{", "}"))
    while url.endswith((")", "]", "}")):
        apertura, cierre = next(par for par in pares if par[1] == url[-1])
        if url.count(cierre) <= url.count(apertura):
            break
        url = url[:-1]
    return url


def _destino_seguro(url):
    if not url or "\\" in url:
        return None

    externo = False
    href = url
    if url.lower().startswith("www."):
        href = "https://" + url
        externo = True
    elif url.lower().startswith(("http://", "https://")):
        externo = True
    elif url.startswith(("/", "./", "../", "#")) and not url.startswith("//"):
        return url, False
    else:
        return None

    try:
        parsed = urlsplit(href)
        _ = parsed.port
    except ValueError:
        return None

    if (
        parsed.scheme.lower() not in ("http", "https")
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or (url.lower().startswith("www.") and parsed.hostname.rstrip(".").count(".") < 1)
    ):
        return None
    return href, externo


def a_parrafos(texto):
    """Convierte texto plano en HTML seguro: una línea en blanco separa párrafos
    y un salto de línea simple pasa a <br>. El texto se escapa antes de enlazar URLs."""
    if not texto:
        return Markup("")
    bloques = [b.strip() for b in re.split(r"\n\s*\n", texto.replace("\r\n", "\n")) if b.strip()]
    saltos = Markup("<br>")
    return Markup("").join(
        Markup("<p>{}</p>").format(
            saltos.join(enlaces_seguros(linea) for linea in bloque.split("\n"))
        )
        for bloque in bloques
    )