import os

from flask import Flask, render_template

from config import config_por_entorno

from .extensions import csrf, db, limiter, login_manager, migrate
from .models.constantes import ETIQUETAS_CATEGORIA, ETIQUETAS_NIVEL, ETIQUETAS_TIPO_NODO
from .utils.fechas import formatear_fecha
from .utils.imagenes import url_imagen
from .utils.texto import a_parrafos, enlaces_seguros


def create_app(entorno=None):
    entorno = entorno or os.environ.get("APP_ENV", "development")
    clase_config = config_por_entorno.get(entorno, config_por_entorno["development"])

    app = Flask(__name__)
    app.config.from_object(clase_config)
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    from . import models  # noqa: F401  (registra los modelos para las migraciones)

    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Inicia sesión para acceder al panel."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def cargar_usuario(id_usuario):
        return db.session.get(models.Usuario, int(id_usuario))

    _registrar_blueprints(app)
    _registrar_manejadores_error(app)

    from .commands import registrar_comandos

    registrar_comandos(app)

    app.add_template_filter(formatear_fecha, "fecha")
    app.add_template_filter(a_parrafos, "parrafos")
    app.add_template_filter(enlaces_seguros, "enlaces")

    @app.context_processor
    def variables_globales():
        return {
            "nombre_sitio": app.config["NOMBRE_SITIO"],
            "url_imagen": url_imagen,
            "ETIQUETAS_CATEGORIA": ETIQUETAS_CATEGORIA,
            "ETIQUETAS_NIVEL": ETIQUETAS_NIVEL,
            "ETIQUETAS_TIPO_NODO": ETIQUETAS_TIPO_NODO,
        }

    return app


def _registrar_blueprints(app):
    from .blueprints.admin import bp as admin_bp
    from .blueprints.aprende import bp as aprende_bp
    from .blueprints.auth import bp as auth_bp
    from .blueprints.busqueda import bp as busqueda_bp
    from .blueprints.main import bp as main_bp
    from .blueprints.municipios import bp as municipios_bp
    from .blueprints.noticias import bp as noticias_bp
    from .blueprints.reportes import bp as reportes_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(aprende_bp)
    app.register_blueprint(municipios_bp)
    app.register_blueprint(noticias_bp)
    app.register_blueprint(busqueda_bp)
    app.register_blueprint(reportes_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")


def _registrar_manejadores_error(app):
    mensajes = {
        403: ("Acceso denegado", "No tienes permiso para ver esta página."),
        404: ("Página no encontrada", "La página que buscas no existe o fue movida."),
        413: ("Archivo demasiado grande", "Lo que intentaste subir pesa demasiado. El máximo es de 8 MB."),
        429: ("Demasiados intentos", "Espera un momento antes de volver a intentarlo."),
        500: ("Error del servidor", "Algo salió mal de nuestro lado. Intenta de nuevo en unos minutos."),
    }

    def crear_manejador(codigo):
        def manejador(error):
            if codigo == 500:
                db.session.rollback()
            titulo, texto = mensajes[codigo]
            return render_template("errors/error.html", codigo=codigo, titulo=titulo, texto=texto), codigo

        return manejador

    for codigo in mensajes:
        app.register_error_handler(codigo, crear_manejador(codigo))