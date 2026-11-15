from sqlalchemy import event

from ..extensions import db
from ..utils.texto import normalizar


class BuscableMixin:
    """Agrega un campo con el texto normalizado (minúsculas y sin tildes)
    para que el buscador funcione igual en cualquier base de datos."""

    campos_busqueda = ()
    texto_busqueda = db.Column(db.Text, nullable=False, default="")

    def actualizar_texto_busqueda(self):
        partes = [getattr(self, campo) or "" for campo in self.campos_busqueda]
        self.texto_busqueda = normalizar(" ".join(partes))


@event.listens_for(BuscableMixin, "before_insert", propagate=True)
@event.listens_for(BuscableMixin, "before_update", propagate=True)
def _actualizar_antes_de_guardar(mapper, conexion, objeto):
    objeto.actualizar_texto_busqueda()