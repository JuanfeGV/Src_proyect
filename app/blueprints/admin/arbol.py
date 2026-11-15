from flask import flash, redirect, render_template, request, url_for

from ...extensions import db
from ...models import NodoArbol
from . import bp
from .forms_contenido import NodoForm


def _problema_central():
    return NodoArbol.query.filter_by(tipo="problema_central").first()


def _aplicar_nodo(nodo, form):
    tipo = form.tipo.data
    nodo.tipo = tipo
    nodo.titulo = form.titulo.data
    nodo.descripcion = form.descripcion.data or None
    nodo.fuente = form.fuente.data or None
    nodo.orden = form.orden.data if form.orden.data is not None else 0
    if tipo == "problema_central":
        nodo.padre_id = None
    elif tipo in ("efecto_directo", "causa_directa"):
        nodo.padre_id = _problema_central().id  # los directos siempre cuelgan del problema central
    else:
        nodo.padre_id = form.padre_id.data


@bp.route("/arbol")
def arbol_lista():
    return render_template(
        "admin/arbol/lista.html",
        central=_problema_central(),
        efectos=NodoArbol.query.filter_by(tipo="efecto_directo").order_by(NodoArbol.orden).all(),
        causas=NodoArbol.query.filter_by(tipo="causa_directa").order_by(NodoArbol.orden).all(),
        sin_ubicar=NodoArbol.query.filter(
            NodoArbol.tipo.in_(["efecto_indirecto", "causa_indirecta"]), NodoArbol.padre_id.is_(None)
        ).all(),
    )


@bp.route("/arbol/nuevo", methods=["GET", "POST"])
def nodo_nuevo():
    form = NodoForm()
    if request.method == "GET":
        form.orden.data = NodoArbol.query.count() + 1
        tipo = request.args.get("tipo")
        if tipo in dict(form.tipo.choices):
            form.tipo.data = tipo
    if form.validate_on_submit():
        nodo = NodoArbol()
        _aplicar_nodo(nodo, form)
        db.session.add(nodo)
        db.session.commit()
        flash("Nodo agregado al árbol.", "success")
        return redirect(url_for("admin.arbol_lista"))
    return render_template("admin/arbol/formulario.html", form=form, nodo=None)


@bp.route("/arbol/<int:nodo_id>/editar", methods=["GET", "POST"])
def nodo_editar(nodo_id):
    nodo = db.get_or_404(NodoArbol, nodo_id)
    form = NodoForm(obj=nodo, nodo=nodo)
    if request.method == "GET":
        form.padre_id.data = nodo.padre_id if nodo.tipo in ("efecto_indirecto", "causa_indirecta") else 0
    if form.validate_on_submit():
        _aplicar_nodo(nodo, form)
        db.session.commit()
        flash("Cambios guardados.", "success")
        return redirect(url_for("admin.arbol_lista"))
    return render_template("admin/arbol/formulario.html", form=form, nodo=nodo)


@bp.route("/arbol/<int:nodo_id>/eliminar", methods=["POST"])
def nodo_eliminar(nodo_id):
    nodo = db.get_or_404(NodoArbol, nodo_id)
    if nodo.hijos:
        flash(
            f"No se puede eliminar: {len(nodo.hijos)} elemento(s) dependen de este nodo. "
            "Elimínalos o muévelos primero.",
            "danger",
        )
        return redirect(url_for("admin.arbol_lista"))
    titulo = nodo.titulo
    db.session.delete(nodo)
    db.session.commit()
    flash(f"Nodo «{titulo[:60]}» eliminado.", "success")
    return redirect(url_for("admin.arbol_lista"))