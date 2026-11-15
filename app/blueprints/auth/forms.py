from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length


class LoginForm(FlaskForm):
    email = StringField(
        "Correo electrónico",
        filters=[lambda valor: valor.strip() if isinstance(valor, str) else valor],
        validators=[
            DataRequired(message="Escribe tu correo."),
            Length(max=255),
            Email(message="Escribe un correo válido.", check_deliverability=False),
        ],
    )
    password = PasswordField("Contraseña", validators=[DataRequired(message="Escribe tu contraseña.")])
    recordar = BooleanField("Mantener la sesión iniciada")
    enviar = SubmitField("Ingresar")