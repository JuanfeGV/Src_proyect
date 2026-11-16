import unittest
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import Usuario
from config import DevelopmentConfig


class AutenticacionAdministrativaTests(unittest.TestCase):
    def setUp(self):
        self.database_config_patch = patch.object(
            DevelopmentConfig,
            "SQLALCHEMY_DATABASE_URI",
            "sqlite:///:memory:",
        )
        self.database_config_patch.start()
        self.app = create_app()
        self.app.config.update(
            TESTING=True,
            WTF_CSRF_ENABLED=False,
            RATELIMIT_ENABLED=False,
        )
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()

        self.administrador = Usuario(
            nombre="Administradora",
            email="admin@example.com",
            rol="admin",
        )
        self.administrador.set_password("una-clave-segura-123")
        self.usuario = Usuario(
            nombre="Usuario",
            email="usuario@example.com",
            rol="usuario",
        )
        self.usuario.set_password("otra-clave-segura-123")
        self.inactivo = Usuario(
            nombre="Inactivo",
            email="inactivo@example.com",
            rol="admin",
            activo=False,
        )
        self.inactivo.set_password("clave-segura-inactivo-123")
        db.session.add_all([self.administrador, self.usuario, self.inactivo])
        db.session.commit()

        self.client = self.app.test_client()
        self.client.environ_base["REMOTE_ADDR"] = "203.0.113.42"

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()
        self.database_config_patch.stop()

    def iniciar_sesion(self, cliente, usuario_id):
        with cliente.session_transaction() as sesion:
            sesion["_user_id"] = str(usuario_id)
            sesion["_fresh"] = True

    def test_footer_enlaza_al_login_en_paginas_publicas(self):
        for ruta in ("/", "/municipios", "/noticias"):
            with self.subTest(ruta=ruta):
                respuesta = self.client.get(ruta)

                self.assertEqual(respuesta.status_code, 200)
                self.assertIn('href="/ingresar">Administración</a>'.encode(), respuesta.data)

    def test_footer_de_administrador_enlaza_al_panel(self):
        self.client.post(
            "/ingresar",
            data={
                "email": "admin@example.com",
                "password": "una-clave-segura-123",
            },
        )

        respuesta = self.client.get("/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('href="/admin/">Administración</a>'.encode(), respuesta.data)

    def test_cerrar_sesion_conserva_su_funcionamiento(self):
        self.client.post(
            "/ingresar",
            data={
                "email": "admin@example.com",
                "password": "una-clave-segura-123",
            },
        )

        respuesta = self.client.post("/salir")

        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta.headers["Location"].endswith("/"))
        self.assertEqual(self.client.get("/admin/").status_code, 302)
        pagina = self.client.get("/")
        self.assertIn('href="/ingresar">Administración</a>'.encode(), pagina.data)

    def test_solo_un_administrador_activo_puede_iniciar_sesion(self):
        respuesta = self.client.post(
            "/ingresar",
            data={
                "email": "admin@example.com",
                "password": "una-clave-segura-123",
            },
        )

        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta.headers["Location"].endswith("/admin/"))
        self.assertEqual(self.client.get("/admin/").status_code, 200)

    def test_usuario_no_administrador_no_puede_iniciar_sesion_ni_entrar_al_panel(self):
        respuesta = self.client.post(
            "/ingresar",
            data={
                "email": "usuario@example.com",
                "password": "otra-clave-segura-123",
            },
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.client.get("/admin/").status_code, 302)

        admin_client = self.app.test_client()
        admin_client.post(
            "/ingresar",
            data={
                "email": "admin@example.com",
                "password": "una-clave-segura-123",
            },
        )
        self.administrador.rol = "usuario"
        db.session.commit()
        self.assertEqual(admin_client.get("/admin/").status_code, 403)

    def test_usuario_inactivo_no_puede_iniciar_sesion(self):
        respuesta = self.client.post(
            "/ingresar",
            data={
                "email": "inactivo@example.com",
                "password": "clave-segura-inactivo-123",
            },
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.client.get("/admin/").status_code, 302)

    def test_desactivar_usuario_revoca_el_acceso_administrativo_existente(self):
        self.iniciar_sesion(self.client, self.administrador.id)
        self.administrador.activo = False
        db.session.commit()

        respuesta = self.client.get("/admin/")

        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("/ingresar", respuesta.headers["Location"])
        self.assertEqual(self.client.get("/admin/").status_code, 302)

    def test_login_y_logout_rechazan_solicitudes_sin_token_csrf(self):
        self.app.config["WTF_CSRF_ENABLED"] = True
        self.assertEqual(self.client.post("/ingresar").status_code, 400)

        self.iniciar_sesion(self.client, self.administrador.id)
        self.assertEqual(self.client.post("/salir").status_code, 400)
        self.assertEqual(self.client.get("/admin/").status_code, 200)

    def test_login_limita_a_cinco_intentos_por_minuto_y_direccion(self):
        self.app.config["RATELIMIT_ENABLED"] = True

        for _ in range(5):
            respuesta = self.client.post(
                "/ingresar",
                data={"email": "admin@example.com", "password": "incorrecta"},
            )
            self.assertEqual(respuesta.status_code, 200)

        respuesta = self.client.post(
            "/ingresar",
            data={"email": "admin@example.com", "password": "incorrecta"},
        )
        self.assertEqual(respuesta.status_code, 429)

    def test_comando_crear_admin_usa_hash_y_no_muestra_la_contrasena(self):
        db.session.query(Usuario).delete()
        db.session.commit()
        clave = "UnaClaveDePrueba-123"

        resultado = self.app.test_cli_runner().invoke(
            args=["crear-admin"],
            input=f"Admin inicial\nprimero@example.com\n{clave}\n{clave}\n",
        )

        self.assertEqual(resultado.exit_code, 0, f"{resultado.output} {resultado.exception!r}")
        self.assertNotIn(clave, resultado.output)
        administrador = Usuario.query.filter_by(email="primero@example.com").one()
        self.assertEqual(administrador.rol, "admin")
        self.assertTrue(administrador.check_password(clave))
        self.assertNotEqual(administrador.password_hash, clave)

    def test_usuario_no_recibe_rol_admin_por_omision(self):
        usuario = Usuario(nombre="Nuevo", email="nuevo@example.com")

        self.assertIsNone(usuario.rol)


if __name__ == "__main__":
    unittest.main()
