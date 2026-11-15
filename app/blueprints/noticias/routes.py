from flask import abort, render_template, request
from flask_login import current_user

from ...models import Articulo, Municipio
from ...models.constantes import CATEGORIAS_ARTICULO
from ...services.consultas import articulos_publicados
from . import bp

POR_PAGINA = 9


@bp.route("/noticias")
def index():
    pagina = request.args.get("page", 1, type=int)
    categoria = request.args.get("categoria", "").strip().lower()
    slug = request.args.get("municipio", "").strip()

    consulta = articulos_publicados()
    if categoria in CATEGORIAS_ARTICULO:
        consulta = consulta.filter(Articulo.categoria == categoria)
    else:
        categoria = ""

    municipio = Municipio.query.filter_by(slug=slug).first() if slug else None
    if municipio:
        consulta = consulta.filter(Articulo.municipio_id == municipio.id)

    # Filtros activos: se conservan al cambiar de página.
    filtros = {}
    if categoria:
        filtros["categoria"] = categoria
    if municipio:
        filtros["municipio"] = municipio.slug

    return render_template(
        "noticias/index.html",
        paginacion=consulta.paginate(page=pagina, per_page=POR_PAGINA, error_out=False),
        categoria=categoria,
        municipio=municipio,
        municipios=Municipio.query.order_by(Municipio.nombre).all(),
        filtros=filtros,
    )


@bp.route("/noticias/<slug>")
def detalle(slug):
    articulo = Articulo.query.filter_by(slug=slug).first_or_404()
    if not articulo.publicado and not current_user.is_authenticated:
        abort(404)  # los borradores solo los ve el administrador
    relacionados = (
        articulos_publicados()
        .filter(Articulo.id != articulo.id, Articulo.categoria == articulo.categoria)
        .limit(3)
        .all()
    )
    return render_template("noticias/detalle.html", articulo=articulo, relacionados=relacionados)