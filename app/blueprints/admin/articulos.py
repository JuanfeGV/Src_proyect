from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import null

from ...extensions import db
from ...models import Articulo
from ...utils.fechas import ahora_utc
from ...utils.imagenes import borrar_imagen
from . import bp
from .forms_contenido import ArticuloForm
from .utilidades import preparar_imagen, slug_unico


def _aplicar_articulo(articulo, form):
    articulo.titulo = form.titulo.data
    articulo.resumen = form.resumen.data or None
    articulo.contenido = form.contenido.data
    articulo.categoria = form.categoria.data
    articulo.municipio_id = form.municipio_id.data or None
    articulo.publicado = form.publicado.data


@bp.route("/articulos")
def articulos_lista():
    pagina = request.args.get("page", 1, type=int)
    paginacion = Articulo.query.order_by(Articulo.creado_en.desc(), Articulo.id.desc()).paginate(
        page=pagina, per_page=15, error_out=False
    )
    return render_template("admin/articulos/lista.html", paginacion=paginacion)


@bp.route("/articulos/nuevo", methods=["GET", "POST"])
def articulo_nuevo():
    form = ArticuloForm()
    if request.method == "GET":
        form.publicado.data = True
    if form.validate_on_submit():
        articulo = Articulo(slug=slug_unico(Articulo, form.titulo.data), autor_id=current_user.id)
        _aplicar_articulo(articulo, form)
        # Un borrador no tiene fecha de publicación. Se usa null() porque la columna tiene un
        # valor por defecto (la fecha actual) que, de otro modo, se aplicaría también a los borradores.
        articulo.fecha_publicacion = ahora_utc() if articulo.publicado else null()
        valido, _ = preparar_imagen(articulo, form)
        if valido:
            db.session.add(articulo)
            db.session.commit()
            flash(f"Artículo «{articulo.titulo}» creado.", "success")
            return redirect(url_for("admin.articulos_lista"))
    return render_template("admin/articulos/formulario.html", form=form, articulo=None)


@bp.route("/articulos/<int:articulo_id>/editar", methods=["GET", "POST"])
def articulo_editar(articulo_id):
    articulo = db.get_or_404(Articulo, articulo_id)
    form = ArticuloForm(obj=articulo)
    if request.method == "GET":
        form.municipio_id.data = articulo.municipio_id or 0
    if form.validate_on_submit():
        _aplicar_articulo(articulo, form)
        if articulo.publicado and not articulo.fecha_publicacion:
            articulo.fecha_publicacion = ahora_utc()
        valido, antigua = preparar_imagen(articulo, form)
        if valido:
            db.session.commit()
            borrar_imagen(antigua)
            flash("Cambios guardados.", "success")
            return redirect(url_for("admin.articulos_lista"))
        db.session.rollback()
    return render_template("admin/articulos/formulario.html", form=form, articulo=articulo)


@bp.route("/articulos/<int:articulo_id>/eliminar", methods=["POST"])
def articulo_eliminar(articulo_id):
    articulo = db.get_or_404(Articulo, articulo_id)
    titulo, imagen = articulo.titulo, articulo.imagen
    db.session.delete(articulo)
    db.session.commit()
    borrar_imagen(imagen)
    flash(f"Artículo «{titulo}» eliminado.", "success")
    return redirect(url_for("admin.articulos_lista"))
