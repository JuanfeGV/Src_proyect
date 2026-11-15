from flask import abort, render_template, request
from flask_login import current_user

from ...extensions import db
from ...models import GuiaConsumo
from ...models.constantes import NIVELES_RIESGO
from ...services.consultas import estructura_arbol, guias_publicadas, municipios_ordenados
from . import bp


@bp.route("/aprende")
def index():
    municipios = municipios_ordenados().all()
    slug = request.args.get("municipio", "").strip()
    nivel = request.args.get("nivel", "").strip().lower()

    # Si se elige un municipio, su nivel de riesgo manda sobre el nivel escogido a mano.
    municipio = next((m for m in municipios if m.slug == slug), None) if slug else None
    solo_generales = False
    if municipio:
        if municipio.nivel_riesgo in NIVELES_RIESGO:
            nivel = municipio.nivel_riesgo
        else:
            nivel, solo_generales = "", True  # municipio sin evaluar: solo guías generales
    elif nivel not in NIVELES_RIESGO:
        nivel = ""

    guias = guias_publicadas(nivel or None, solo_generales).all()
    return render_template(
        "aprende/index.html",
        arbol=estructura_arbol(),
        guias=guias,
        municipios=municipios,
        municipio=municipio,
        nivel=nivel,
        solo_generales=solo_generales,
    )


@bp.route("/aprende/guias/<int:guia_id>")
def guia(guia_id):
    guia = db.get_or_404(GuiaConsumo, guia_id)
    if not guia.publicada and not current_user.is_authenticated:
        abort(404)  # las guías sin publicar solo las ve el administrador
    return render_template("aprende/guia.html", guia=guia)