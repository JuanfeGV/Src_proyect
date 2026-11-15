from ...utils.imagenes import ImagenInvalida, guardar_imagen
from ...utils.texto import crear_slug


def slug_unico(modelo, texto, actual_id=None):
    """Crea un slug a partir del texto y le agrega -2, -3... si ya existe."""
    base = (crear_slug(texto) or "contenido")[:200]
    slug, numero = base, 2
    while True:
        consulta = modelo.query.filter(modelo.slug == slug)
        if actual_id is not None:
            consulta = consulta.filter(modelo.id != actual_id)
        if consulta.first() is None:
            return slug
        slug = f"{base}-{numero}"
        numero += 1


def preparar_imagen(objeto, form):
    """Sube o quita la imagen según lo que se pidió en el formulario.

    Devuelve (valido, antigua). 'antigua' es el archivo anterior, que se debe
    borrar con borrar_imagen() DESPUÉS de guardar los cambios en la base de datos.
    """
    archivo = form.imagen.data
    if archivo is not None and getattr(archivo, "filename", ""):
        try:
            nombre = guardar_imagen(archivo)
        except ImagenInvalida as error:
            form.imagen.errors.append(str(error))
            return False, None
        antigua, objeto.imagen = objeto.imagen, nombre
        return True, antigua
    if form.quitar_imagen.data and objeto.imagen:
        antigua, objeto.imagen = objeto.imagen, None
        return True, antigua
    return True, None