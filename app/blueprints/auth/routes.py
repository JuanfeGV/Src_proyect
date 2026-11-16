from urllib.parse import urlparse

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from ...extensions import limiter
from ...models import Usuario
from . import bp
from .forms import LoginForm


def _destino_seguro(destino):
    """Solo acepta rutas internas del sitio (evita redirigir a páginas externas)."""
    if not destino:
        return None
    partes = urlparse(destino)
    if partes.scheme or partes.netloc:
        return None
    if not destino.startswith("/") or destino.startswith("//") or "\\" in destino:
        return None
    return destino


@bp.route("/ingresar", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        if current_user.is_active and current_user.rol == "admin":
            return redirect(url_for("admin.panel"))
        logout_user()

    form = LoginForm()
    if form.validate_on_submit():
        usuario = Usuario.query.filter_by(email=form.email.data.strip().lower()).first()
        if (
            usuario
            and usuario.activo
            and usuario.rol == "admin"
            and usuario.check_password(form.password.data)
        ):
            login_user(usuario, remember=form.recordar.data)
            return redirect(_destino_seguro(request.args.get("next")) or url_for("admin.panel"))
        flash("Correo o contraseña incorrectos.", "danger")

    return render_template("auth/login.html", form=form)


@bp.route("/salir", methods=["POST"])
def logout():
    logout_user()
    flash("Cerraste la sesión.", "success")
    return redirect(url_for("main.inicio"))