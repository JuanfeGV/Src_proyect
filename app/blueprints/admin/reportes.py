from flask import render_template, request

from ...models import ReporteCiudadano
from . import bp


@bp.route("/reportes")
def reportes_lista():
    pagina = request.args.get("page", 1, type=int)
    paginacion = ReporteCiudadano.query.order_by(
        ReporteCiudadano.creado_en.desc(), ReporteCiudadano.id.desc()
    ).paginate(page=pagina, per_page=20, error_out=False)
    return render_template("admin/reportes/lista.html", paginacion=paginacion)
