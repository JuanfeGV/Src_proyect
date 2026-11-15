from flask import Blueprint, abort
from flask_login import current_user

from ...extensions import login_manager

bp = Blueprint("admin", __name__)


@bp.before_request
def proteger_panel():
    """Todas las rutas del panel exigen un administrador con la sesión iniciada."""
    if not current_user.is_authenticated:
        return login_manager.unauthorized()
    if current_user.rol != "admin":
        abort(403)


from . import arbol, articulos, guias, municipios, routes  # noqa: E402,F401