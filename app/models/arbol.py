from ..extensions import db
from .mixins import BuscableMixin


class NodoArbol(BuscableMixin, db.Model):
    """Un recuadro del árbol del problema.

    'padre' es el nodo más cercano al problema central:
      causa indirecta -> causa directa -> problema central
      efecto indirecto -> efecto directo -> problema central
    """

    __tablename__ = "nodos_arbol"
    campos_busqueda = ("titulo", "descripcion")

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(30), nullable=False, index=True)
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    icono = db.Column(db.String(50))
    orden = db.Column(db.Integer, nullable=False, default=0)
    fuente = db.Column(db.String(200))
    padre_id = db.Column(db.Integer, db.ForeignKey("nodos_arbol.id", ondelete="SET NULL"), index=True)

    hijos = db.relationship(
        "NodoArbol",
        backref=db.backref("padre", remote_side=[id]),
        order_by="NodoArbol.orden",
    )
    

    def __repr__(self):
        return f"<Nodo {self.tipo}: {self.titulo[:30]}>"