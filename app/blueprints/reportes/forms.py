from flask_wtf import FlaskForm
from wtforms import SelectChoice, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length


TIPOS_FALLA = [
    SelectChoice("fuga", "Fuga de agua"),
    SelectChoice("interrupcion", "Interrupción del servicio"),
    SelectChoice("baja_presion", "Baja presión"),
    SelectChoice("calidad", "Problema de calidad del agua"),
    SelectChoice("infraestructura", "Daño en infraestructura"),
    SelectChoice("otro", "Otro"),
]


def _limpiar(valor):
    return valor.strip() if isinstance(valor, str) else valor


class ReporteCiudadanoForm(FlaskForm):
    municipio_id = SelectField(
        "Municipio",
        coerce=int,
        validators=[DataRequired(message="Selecciona un municipio.")],
    )
    barrio = StringField(
        "Barrio o vereda",
        filters=[_limpiar],
        validators=[DataRequired(message="Escribe el barrio o vereda."), Length(max=120)],
    )
    tipo_falla = SelectField(
        "Tipo de falla",
        choices=TIPOS_FALLA,
        validators=[DataRequired(message="Selecciona el tipo de falla.")],
    )
    descripcion = TextAreaField(
        "Descripción",
        filters=[_limpiar],
        validators=[
            DataRequired(message="Describe lo que ocurre."),
            Length(min=10, max=2000, message="La descripción debe tener entre 10 y 2000 caracteres."),
        ],
    )
    sitio_web = StringField(filters=[_limpiar])
    enviar = SubmitField("Enviar reporte")
