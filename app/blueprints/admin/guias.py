from flask import flash, redirect, render_template, request, url_for

from ...extensions import db
from ...models import GuiaConsumo
from ...utils.imagenes import borrar_imagen
from . import bp
from .forms_contenido import GuiaForm
from .utilidades import preparar_imagen


def _aplicar_guia(guia, form):
    guia.titulo = form.titulo.data
    guia.resumen = form.resumen.data or None
    guia.contenido = form.contenido.data
    guia.nivel_riesgo = form.nivel_riesgo.data
    guia.orden = form.orden.data if form.orden.data is not None else 0
    guia.publicada = form.publicada.data


@bp.route("/guias")
def guias_lista():
    guias = GuiaConsumo.query.order_by(GuiaConsumo.orden, GuiaConsumo.id).all()
    return render_template("admin/guias/lista.html", guias=guias)


@bp.route("/guias/nueva", methods=["GET", "POST"])
def guia_nueva():
    form = GuiaForm()
    if request.method == "GET":
        form.publicada.data = True
        form.orden.data = GuiaConsumo.query.count() + 1
    if form.validate_on_submit():
        guia = GuiaConsumo()
        _aplicar_guia(guia, form)
        valido, _ = preparar_imagen(guia, form)
        if valido:
            db.session.add(guia)
            db.session.commit()
            flash(f"Guía «{guia.titulo}» creada.", "success")
            return redirect(url_for("admin.guias_lista"))
    return render_template("admin/guias/formulario.html", form=form, guia=None)


@bp.route("/guias/<int:guia_id>/editar", methods=["GET", "POST"])
def guia_editar(guia_id):
    guia = db.get_or_404(GuiaConsumo, guia_id)
    form = GuiaForm(obj=guia)
    if form.validate_on_submit():
        _aplicar_guia(guia, form)
        valido, antigua = preparar_imagen(guia, form)
        if valido:
            db.session.commit()
            borrar_imagen(antigua)
            flash("Cambios guardados.", "success")
            return redirect(url_for("admin.guias_lista"))
        db.session.rollback()
    return render_template("admin/guias/formulario.html", form=form, guia=guia)


@bp.route("/guias/<int:guia_id>/eliminar", methods=["POST"])
def guia_eliminar(guia_id):
    guia = db.get_or_404(GuiaConsumo, guia_id)
    titulo, imagen = guia.titulo, guia.imagen
    db.session.delete(guia)
    db.session.commit()
    borrar_imagen(imagen)
    flash(f"Guía «{titulo}» eliminada.", "success")
    return redirect(url_for("admin.guias_lista"))