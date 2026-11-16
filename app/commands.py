import click
from email_validator import EmailNotValidError, validate_email

from .extensions import db
from .models import Usuario
from .services.semilla import sembrar_todo


def registrar_comandos(app):
    @app.cli.command("crear-admin")
    def crear_admin():
        """Crea un usuario administrador pidiendo los datos por la terminal."""
        nombre = click.prompt("Nombre").strip()
        correo = click.prompt("Correo electrónico").strip()
        try:
            email = validate_email(correo, check_deliverability=False).normalized.lower()
        except EmailNotValidError as error:
            raise click.ClickException(f"Correo no válido: {error}")

        if Usuario.query.filter_by(email=email).first():
            raise click.ClickException("Ya existe un usuario con ese correo.")

        clave = click.prompt("Contraseña (mínimo 12 caracteres)", hide_input=True, confirmation_prompt=True)
        if len(clave) < 12:
            raise click.ClickException("La contraseña debe tener al menos 12 caracteres.")

        usuario = Usuario(nombre=nombre, email=email, rol="admin")
        usuario.set_password(clave)
        db.session.add(usuario)
        db.session.commit()
        click.echo(f"Administrador creado: {email}")

    @app.cli.command("sembrar-datos")
    def sembrar_datos():
        """Carga municipios, árbol del problema y contenido de ejemplo."""
        resultado = sembrar_todo()
        for nombre, cantidad in resultado.items():
            click.echo(f"{nombre}: {cantidad} nuevos")
        click.echo("Listo. Puedes ejecutarlo de nuevo sin duplicar datos.")