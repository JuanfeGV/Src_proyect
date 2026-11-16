from ..extensions import db
from ..utils.fechas import ahora_utc


class ReporteCiudadano(db.Model):
    __tablename__ = "reportes_ciudadanos"

    id = db.Column(db.Integer, primary_key=True)
    municipio = db.Column(db.String(100), nullable=False)
    barrio = db.Column(db.String(120), nullable=False)
    tipo_falla = db.Column(db.String(40), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc, index=True)

    def __repr__(self):
        return f"<ReporteCiudadano {self.id}: {self.tipo_falla}>"
