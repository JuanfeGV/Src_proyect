import math

from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError

from ...models import Municipio
from ...models.constantes import ETIQUETAS_NIVEL, NIVELES_RIESGO
from ...utils.texto import crear_slug


def _limpiar(valor):
    return valor.strip() if isinstance(valor, str) else valor


OBLIGATORIO = DataRequired(message="Este campo es obligatorio.")


class DecimalFlexibleField(StringField):
    """Número decimal que acepta punto o coma (4.91 o 4,91). El valor queda como float."""

    def process_formdata(self, valores):
        if not valores or not valores[0].strip():
            self.data = None
            return
        texto = valores[0].strip().replace(",", ".")
        try:
            numero = float(texto)
            if not math.isfinite(numero):
                raise ValueError
        except ValueError:
            self.data = None
            raise ValueError("Escribe un número, por ejemplo 4.9186.")
        self.data = numero

    def _value(self):
        if self.raw_data:
            return self.raw_data[0]
        return "" if self.data is None else str(self.data)


class MunicipioForm(FlaskForm):
    nombre = StringField("Nombre del municipio", filters=[_limpiar], validators=[OBLIGATORIO, Length(max=100)])
    latitud = DecimalFlexibleField(
        "Latitud", validators=[Optional(), NumberRange(-90, 90, message="La latitud debe estar entre -90 y 90.")]
    )
    longitud = DecimalFlexibleField(
        "Longitud", validators=[Optional(), NumberRange(-180, 180, message="La longitud debe estar entre -180 y 180.")]
    )
    nivel_riesgo = SelectField(
        "Nivel de riesgo de desabastecimiento",
        choices=[("", "Sin evaluar")] + [(nivel, ETIQUETAS_NIVEL[nivel]) for nivel in NIVELES_RIESGO],
    )
    estado_suministro = StringField(
        "Estado del suministro", filters=[_limpiar], validators=[Optional(), Length(max=150)]
    )
    resumen = TextAreaField("Resumen", filters=[_limpiar], validators=[Optional(), Length(max=5000)])
    recomendaciones = TextAreaField(
        "Recomendaciones locales", filters=[_limpiar], validators=[Optional(), Length(max=5000)]
    )
    enviar = SubmitField("Guardar")

    def __init__(self, *args, municipio_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._municipio_id = municipio_id

    def validate_nombre(self, campo):
        slug = crear_slug(campo.data)
        if not slug:
            raise ValidationError("Escribe un nombre válido.")
        existente = Municipio.query.filter(Municipio.slug == slug).first()
        if existente and existente.id != self._municipio_id:
            raise ValidationError("Ya existe un municipio con ese nombre.")


class IndicadorForm(FlaskForm):
    nombre = StringField("Indicador", filters=[_limpiar], validators=[OBLIGATORIO, Length(max=120)])
    valor = StringField("Valor", filters=[_limpiar], validators=[OBLIGATORIO, Length(max=120)])
    unidad = StringField("Unidad", filters=[_limpiar], validators=[Optional(), Length(max=40)])
    periodo = StringField("Periodo", filters=[_limpiar], validators=[Optional(), Length(max=40)])
    fuente = StringField("Fuente", filters=[_limpiar], validators=[Optional(), Length(max=200)])
    orden = IntegerField(
        "Orden", validators=[Optional(), NumberRange(0, 9999, message="Usa un número entre 0 y 9999.")]
    )
    enviar = SubmitField("Guardar")