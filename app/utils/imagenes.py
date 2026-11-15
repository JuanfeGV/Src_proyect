import re
import uuid
from pathlib import Path

from flask import current_app, url_for
from PIL import Image, ImageOps, UnidentifiedImageError

LADO_MAXIMO = 1200
LADO_MINIATURA = 480
PIXELES_MAXIMOS = 25_000_000
CALIDAD_WEBP = 80
FORMATOS_PERMITIDOS = ["JPEG", "PNG", "WEBP"]
_NOMBRE_VALIDO = re.compile(r"^[0-9a-f]{32}\.webp$")


class ImagenInvalida(Exception):
    """La imagen subida no se puede usar. El mensaje está listo para mostrarse."""


def _carpeta():
    carpeta = Path(current_app.static_folder) / "uploads"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def _nombre_miniatura(nombre):
    return nombre[: -len(".webp")] + "_mini.webp"


def guardar_imagen(archivo):
    """Valida que el archivo sea una imagen real, la reduce y la guarda en WebP
    (una versión normal y una miniatura). Devuelve el nombre del archivo guardado."""
    try:
        archivo.stream.seek(0)
        with Image.open(archivo.stream, formats=FORMATOS_PERMITIDOS) as original:
            if original.width * original.height > PIXELES_MAXIMOS:
                raise ImagenInvalida("La imagen tiene demasiados píxeles. Usa una más pequeña.")
            imagen = ImageOps.exif_transpose(original)  # respeta la orientación de la foto
            imagen.load()
    except ImagenInvalida:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError):
        raise ImagenInvalida("El archivo no es una imagen válida (JPG, PNG o WebP).")

    imagen = imagen.convert("RGBA" if imagen.mode in ("RGBA", "LA", "P") else "RGB")

    nombre = f"{uuid.uuid4().hex}.webp"  # nombre aleatorio: nunca se usa el nombre que sube la persona
    carpeta = _carpeta()

    principal = imagen.copy()
    principal.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
    principal.save(carpeta / nombre, "WEBP", quality=CALIDAD_WEBP, method=4)

    miniatura = imagen.copy()
    miniatura.thumbnail((LADO_MINIATURA, LADO_MINIATURA))
    miniatura.save(carpeta / _nombre_miniatura(nombre), "WEBP", quality=CALIDAD_WEBP, method=4)
    return nombre


def borrar_imagen(nombre):
    """Borra la imagen y su miniatura. No hace nada si el nombre no es válido."""
    if not nombre or not _NOMBRE_VALIDO.match(nombre):
        return
    carpeta = _carpeta()
    for archivo in (nombre, _nombre_miniatura(nombre)):
        try:
            (carpeta / archivo).unlink()
        except FileNotFoundError:
            pass


def url_imagen(nombre, miniatura=False):
    """Dirección de la imagen para usar en las plantillas (None si no hay imagen)."""
    if not nombre:
        return None
    archivo = _nombre_miniatura(nombre) if miniatura else nombre
    return url_for("static", filename=f"uploads/{archivo}")