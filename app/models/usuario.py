from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..utils.fechas import ahora_utc


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), nullable=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)

    def set_password(self, clave):
        self.password_hash = generate_password_hash(clave)

    def check_password(self, clave):
        return check_password_hash(self.password_hash, clave)

    @property
    def is_active(self):  # Flask-Login: un usuario inactivo no puede entrar
        return self.activo

    def __repr__(self):
        return f"<Usuario {self.email}>"