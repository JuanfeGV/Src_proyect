from ..extensions import db
from ..utils.fechas import ahora_utc
from .mixins import BuscableMixin


class Municipio(BuscableMixin, db.Model):
    __tablename__ = "municipios"
    campos_busqueda = ("nombre", "resumen", "recomendaciones", "estado_suministro")

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    slug = db.Column(db.String(120), nullable=False, unique=True, index=True)
    latitud = db.Column(db.Float)
    longitud = db.Column(db.Float)
    # "bajo", "medio" o "alto". Vacío (None) significa "sin evaluar".
    nivel_riesgo = db.Column(db.String(10))
    estado_suministro = db.Column(db.String(150))
    resumen = db.Column(db.Text)
    recomendaciones = db.Column(db.Text)
    actualizado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc, onupdate=ahora_utc)

    indicadores = db.relationship(
        "IndicadorMunicipio",
        back_populates="municipio",
        cascade="all, delete-orphan",
        order_by="IndicadorMunicipio.orden",
    )

    def __repr__(self):
        return f"<Municipio {self.nombre}>"


class IndicadorMunicipio(db.Model):
    """Dato que el administrador carga para un municipio (cobertura, IRCA, ICA...)."""

    __tablename__ = "indicadores_municipio"

    id = db.Column(db.Integer, primary_key=True)
    municipio_id = db.Column(
        db.Integer, db.ForeignKey("municipios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nombre = db.Column(db.String(120), nullable=False)
    valor = db.Column(db.String(120), nullable=False)
    unidad = db.Column(db.String(40))
    periodo = db.Column(db.String(40))
    fuente = db.Column(db.String(200))
    orden = db.Column(db.Integer, nullable=False, default=0)

    municipio = db.relationship("Municipio", back_populates="indicadores")

    def __repr__(self):
        return f"<Indicador {self.nombre}={self.valor}>"