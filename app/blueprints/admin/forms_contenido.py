from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import BooleanField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import Length, NumberRange, Optional

from ...extensions import db
from ...models import Municipio, NodoArbol
from ...models.constantes import ETIQUETAS_CATEGORIA, ETIQUETAS_NIVEL, ETIQUETAS_TIPO_NODO, NIVELES_GUIA
from .forms import OBLIGATORIO, _limpiar

VALIDAR_IMAGEN = FileAllowed(["jpg", "jpeg", "png", "webp"], "Solo se permiten imágenes JPG, PNG o WebP.")
VALIDAR_ORDEN = NumberRange(0, 9999, message="Usa un número entre 0 y 9999.")


class ArticuloForm(FlaskForm):
    titulo = StringField("Título", filters=[_limpiar], validators=[OBLIGATORIO, Length(max=200)])
    resumen = StringField("Resumen corto", filters=[_limpiar], validators=[Optional(), Length(max=300)])
    contenido = TextAreaField("Contenido", filters=[_limpiar], validators=[OBLIGATORIO, Length(max=50000)])
    categoria = SelectField(
        "Categoría", choices=[(clave, texto) for clave, texto in ETIQUETAS_CATEGORIA.items()]
    )
    municipio_id = SelectField("Municipio relacionado", coerce=int)
    imagen = FileField("Imagen", validators=[VALIDAR_IMAGEN])
    quitar_imagen = BooleanField("Quitar la imagen actual")
    publicado = BooleanField("Publicado (visible para el público)")
    enviar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        municipios = Municipio.query.order_by(Municipio.nombre).all()
        self.municipio_id.choices = [(0, "Toda la región")] + [(m.id, m.nombre) for m in municipios]


class GuiaForm(FlaskForm):
    titulo = StringField("Título", filters=[_limpiar], validators=[OBLIGATORIO, Length(max=200)])
    resumen = StringField("Resumen corto", filters=[_limpiar], validators=[Optional(), Length(max=300)])
    contenido = TextAreaField("Contenido", filters=[_limpiar], validators=[OBLIGATORIO, Length(max=20000)])
    nivel_riesgo = SelectField(
        "Nivel de riesgo al que aplica",
        choices=[(nivel, ETIQUETAS_NIVEL[nivel]) for nivel in NIVELES_GUIA],
    )
    orden = IntegerField("Orden", validators=[Optional(), VALIDAR_ORDEN])
    imagen = FileField("Imagen", validators=[VALIDAR_IMAGEN])
    quitar_imagen = BooleanField("Quitar la imagen actual")
    publicada = BooleanField("Publicada (visible para el público)")
    enviar = SubmitField("Guardar")


class NodoForm(FlaskForm):
    tipo = SelectField("Tipo de nodo", choices=list(ETIQUETAS_TIPO_NODO.items()))
    titulo = StringField("Título", filters=[_limpiar], validators=[OBLIGATORIO, Length(max=200)])
    descripcion = TextAreaField(
        "Descripción", filters=[_limpiar], validators=[Optional(), Length(max=5000)]
    )
    padre_id = SelectField("Depende de", coerce=int)
    orden = IntegerField("Orden", validators=[Optional(), VALIDAR_ORDEN])
    fuente = StringField("Fuente", filters=[_limpiar], validators=[Optional(), Length(max=200)])
    enviar = SubmitField("Guardar")

    def __init__(self, *args, nodo=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._nodo = nodo
        directos = (
            NodoArbol.query.filter(NodoArbol.tipo.in_(["efecto_directo", "causa_directa"]))
            .order_by(NodoArbol.tipo, NodoArbol.orden)
            .all()
        )
        self.padre_id.choices = [(0, "— No aplica —")] + [
            (n.id, f"{ETIQUETAS_TIPO_NODO[n.tipo]}: {n.titulo[:70]}") for n in directos
        ]

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators=extra_validators):
            return False

        tipo = self.tipo.data
        propio = self._nodo.id if self._nodo else None
        otro_central = NodoArbol.query.filter(
            NodoArbol.tipo == "problema_central", NodoArbol.id != propio
        ).first()

        if tipo == "problema_central" and otro_central:
            self.tipo.errors.append("Ya existe un problema central. Solo puede haber uno.")
        elif tipo in ("efecto_directo", "causa_directa") and not otro_central:
            self.tipo.errors.append("Primero crea el problema central.")
        elif tipo in ("efecto_indirecto", "causa_indirecta"):
            esperado = "efecto_directo" if tipo == "efecto_indirecto" else "causa_directa"
            padre = db.session.get(NodoArbol, self.padre_id.data) if self.padre_id.data else None
            if padre is None or padre.tipo != esperado:
                texto = "un efecto directo" if esperado == "efecto_directo" else "una causa directa"
                self.padre_id.errors.append(f"Este tipo de nodo debe depender de {texto}.")

        if self._nodo is not None and self._nodo.hijos and tipo != self._nodo.tipo:
            self.tipo.errors.append(
                "Este nodo tiene elementos que dependen de él. Muévelos o elimínalos antes de cambiar su tipo."
            )
        return not (self.tipo.errors or self.padre_id.errors)