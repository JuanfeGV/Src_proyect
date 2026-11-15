from ..extensions import db
from ..utils.fechas import ahora_utc
from .mixins import BuscableMixin


class Articulo(BuscableMixin, db.Model):
    __tablename__ = "articulos"
    campos_busqueda = ("titulo", "resumen", "contenido")

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), nullable=False, unique=True, index=True)
    resumen = db.Column(db.String(300))
    contenido = db.Column(db.Text, nullable=False)
    imagen = db.Column(db.String(255))  # nombre del archivo de imagen subido
    categoria = db.Column(db.String(20), nullable=False, default="noticia")
    publicado = db.Column(db.Boolean, nullable=False, default=False)
    fecha_publicacion = db.Column(db.DateTime, default=ahora_utc)
    creado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    actualizado_en = db.Column(db.DateTime, nullable=False, default=ahora_utc, onupdate=ahora_utc)

    municipio_id = db.Column(db.Integer, db.ForeignKey("municipios.id", ondelete="SET NULL"), index=True)
    autor_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="SET NULL"), index=True)

    municipio = db.relationship("Municipio", backref=db.backref("articulos", lazy="dynamic"))
    autor = db.relationship("Usuario")

    def __repr__(self):
        return f"<Articulo {self.titulo}>"