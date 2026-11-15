from ..extensions import db
from ..utils.fechas import ahora_utc
from .mixins import BuscableMixin


class GuiaConsumo(BuscableMixin, db.Model):
    __tablename__ = "guias_consumo"
    campos_busqueda = ("titulo", "resumen", "contenido")

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    resumen = db.Column(db.String(300))
    contenido = db.Column(db.Text, nullable=False)
    # "bajo", "medio", "alto" o "todos" (aplica a cualquier nivel de riesgo).
    nivel_riesgo = db.Column(db.String(10), nullable=False, default="todos", index=True)
    imagen = db.Column(db.String(255))
    orden = db.Column(db.Integer, nullable=False, default=0)
    publicada = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    actualizado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc, onupdate=ahora_utc)

    def __repr__(self):
        return f"<Guia {self.titulo}>"