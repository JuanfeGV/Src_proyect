from flask import render_template

from . import bp


@bp.route("/")
def inicio():
    return render_template("main/inicio.html")