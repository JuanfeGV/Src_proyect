from flask import Blueprint

bp = Blueprint("busqueda", __name__)

from . import routes  # noqa: E402,F401