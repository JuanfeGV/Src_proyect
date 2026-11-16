import re
import unittest
from unittest.mock import patch

from flask import Flask

from app import create_app
from app.extensions import db
from app.models import Usuario
from app.services.correos_imap import (
    ConfiguracionIMAPIncompleta,
    ErrorCorreoIMAP,
    MensajeCorreo,
    MensajeCorreoDetalle,
    listar_mensajes,
    obtener_mensaje,
)
from config import DevelopmentConfig


class IMAPSimulado:
    def __init__(self, cantidad=35):
        self.uids = list(range(1, cantidad + 1))
        self.select_calls = []
        self.uid_calls = []
        self.logout_calls = 0

    def login(self, usuario, clave):
        self.assert_credentials(usuario, clave)
        return "OK", [b"authenticated"]

    def assert_credentials(self, usuario, clave):
        assert usuario == "cuenta@example.com"
        assert clave == "secreto-de-prueba"

    def select(self, buzon, readonly=False):
        self.select_calls.append((buzon, readonly))
        return "OK", [str(len(self.uids)).encode()]

    def uid(self, comando, *argumentos):
        self.uid_calls.append((comando, argumentos))
        if comando == "search":
            return "OK", [b" ".join(str(uid).encode() for uid in self.uids)]
        if comando == "fetch":
            identificadores = [int(valor) for valor in argumentos[0].split(",")]
            registros = []
            for uid in identificadores:
                estado = r"\Seen" if uid % 2 else ""
                encabezados = (
                    f"From: remitente{uid}@example.com\r\n"
                    f"Subject: Asunto {uid}\r\n"
                    "Date: Fri, 14 Nov 2025 09:00:00 +0000\r\n\r\n"
                ).encode()
                metadatos = (
                    f'1 (UID {uid} FLAGS ({estado}) INTERNALDATE "16-Nov-2026 18:59:00 +0000" '
                    f"BODY[HEADER.FIELDS (FROM SUBJECT DATE)] {{0}}"
                ).encode()
                registros.append((metadatos, encabezados))
            return "OK", registros
        raise AssertionError(f"Comando IMAP inesperado: {comando}")

    def logout(self):
        self.logout_calls += 1
        return "BYE", [b"closed"]


class IMAPSimuladoDetalle(IMAPSimulado):
    _ESTRUCTURA = (
        b'(("TEXT" "PLAIN" ("CHARSET" "UTF-8") NIL NIL "QUOTED-PRINTABLE" '
        b'15 1 NIL NIL NIL NIL) '
        b'("APPLICATION" "PDF" ("NAME" "adjunto.pdf") NIL NIL "BASE64" 100 '
        b'("ATTACHMENT" ("FILENAME" "adjunto.pdf")) NIL NIL) '
        b'("TEXT" "HTML" ("CHARSET" "UTF-8") NIL NIL "7BIT" 50 1 NIL NIL NIL NIL) '
        b'"MIXED" ("BOUNDARY" "borde"))'
    )

    def uid(self, comando, *argumentos):
        self.uid_calls.append((comando, argumentos))
        if comando != "fetch":
            return super().uid(comando, *argumentos)

        consulta = argumentos[1]
        if "BODYSTRUCTURE" in consulta:
            encabezados = (
                b"From: remitente@example.com\r\n"
                b"Subject: Detalle\r\n"
                b"Date: Fri, 14 Nov 2025 09:00:00 +0000\r\n\r\n"
            )
            metadatos = (
                b'1 (UID 42 FLAGS (\\Seen) INTERNALDATE "16-Nov-2026 18:59:00 +0000" BODYSTRUCTURE '
                + self._ESTRUCTURA
                + b" BODY[HEADER.FIELDS (FROM SUBJECT DATE)] {0}"
            )
            return "OK", [(metadatos, encabezados)]
        if "BODY.PEEK[1]" in consulta:
            return "OK", [(b"1 (UID 42 BODY[1]<0.16384> {15}", b"Hola=2C mundo=21")]
        raise AssertionError(f"Parte IMAP inesperada: {consulta}")


class CorreoIMAPServiceTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            IMAP_SERVER="imap.example.com",
            IMAP_PORT=993,
            IMAP_USERNAME="cuenta@example.com",
            IMAP_PASSWORD="secreto-de-prueba",
        )

    def test_lista_solo_los_ultimos_30_mensajes_en_solo_lectura(self):
        cliente = IMAPSimulado()
        with self.app.app_context(), patch(
            "app.services.correos_imap.imaplib.IMAP4_SSL",
            return_value=cliente,
        ) as conectar:
            mensajes = listar_mensajes()

        self.assertEqual(len(mensajes), 30)
        self.assertEqual(mensajes[0].uid, 35)
        self.assertEqual(mensajes[-1].uid, 6)
        self.assertEqual(mensajes[0].fecha, "16/11/2026 13:59")
        self.assertTrue(mensajes[0].leido)
        self.assertFalse(mensajes[1].leido)
        self.assertEqual(cliente.select_calls, [("INBOX", True)])
        conectar.assert_called_once()
        self.assertEqual(conectar.call_args.kwargs["timeout"], 10)
        self.assertEqual(cliente.logout_calls, 1)

        comandos = [argumentos for comando, argumentos in cliente.uid_calls if comando == "fetch"]
        self.assertEqual(len(comandos), 1)
        self.assertEqual(comandos[0][0], ",".join(str(uid) for uid in range(6, 36)))
        self.assertIn("BODY.PEEK", comandos[0][1])
        self.assertFalse(any(comando in ("store", "copy", "expunge", "delete") for comando, _ in cliente.uid_calls))

    def test_detalle_solo_descarga_texto_plano_y_no_adjuntos(self):
        cliente = IMAPSimuladoDetalle()
        with self.app.app_context(), patch(
            "app.services.correos_imap.imaplib.IMAP4_SSL",
            return_value=cliente,
        ):
            mensaje = obtener_mensaje(42)

        self.assertEqual(mensaje.contenido, "Hola, mundo!")
        self.assertEqual(mensaje.fecha, "16/11/2026 13:59")
        self.assertTrue(mensaje.leido)
        consultas = [argumentos[1] for comando, argumentos in cliente.uid_calls if comando == "fetch"]
        self.assertTrue(any("BODY.PEEK[1]" in consulta for consulta in consultas))
        self.assertFalse(any("BODY.PEEK[2]" in consulta for consulta in consultas))
        self.assertFalse(any("BODY.PEEK[3]" in consulta for consulta in consultas))
        self.assertTrue(all("BODY.PEEK" in consulta for consulta in consultas))
        self.assertEqual(cliente.select_calls, [("INBOX", True)])

    def test_contenido_se_limita_a_16_kb_de_respuesta_y_12_000_caracteres(self):
        class MensajeLargo(IMAPSimuladoDetalle):
            _ESTRUCTURA = (
                b'(("TEXT" "PLAIN" ("CHARSET" "UTF-8") NIL NIL "7BIT" 20000 1 '
                b'NIL NIL NIL NIL) "MIXED" ("BOUNDARY" "borde"))'
            )

            def uid(self, comando, *argumentos):
                self.uid_calls.append((comando, argumentos))
                if comando == "fetch" and "BODYSTRUCTURE" in argumentos[1]:
                    return "OK", [
                        (
                            b'1 (UID 42 FLAGS () INTERNALDATE "16-Nov-2026 18:59:00 +0000" BODYSTRUCTURE '
                            + self._ESTRUCTURA
                            + b" BODY[HEADER.FIELDS] {0}",
                            b"From: remitente@example.com\r\nSubject: Largo\r\n\r\n",
                        )
                    ]
                if comando == "fetch":
                    return "OK", [(b"1 (UID 42 BODY[TEXT] {16384}", b"a" * 16384)]
                raise AssertionError(comando)

        cliente = MensajeLargo()
        with self.app.app_context(), patch(
            "app.services.correos_imap.imaplib.IMAP4_SSL",
            return_value=cliente,
        ):
            mensaje = obtener_mensaje(42)

        self.assertEqual(len(mensaje.contenido), 12000)
        self.assertTrue(mensaje.truncado)
        self.assertTrue(any("<0.16384>" in argumentos[1] for _, argumentos in cliente.uid_calls if len(argumentos) > 1))

    def test_configuracion_incompleta_no_intenta_conectar(self):
        self.app.config["IMAP_PASSWORD"] = ""
        with self.app.app_context(), patch(
            "app.services.correos_imap.imaplib.IMAP4_SSL"
        ) as conectar:
            with self.assertRaises(ConfiguracionIMAPIncompleta):
                listar_mensajes()

        conectar.assert_not_called()

    def test_error_de_conexion_no_expone_credenciales(self):
        with self.app.app_context(), patch(
            "app.services.correos_imap.imaplib.IMAP4_SSL",
            side_effect=OSError("error de transporte con secreto-de-prueba"),
        ):
            with self.assertRaises(ErrorCorreoIMAP) as resultado:
                listar_mensajes()

        self.assertNotIn("secreto-de-prueba", str(resultado.exception))

    def test_fecha_ausente_o_invalida_se_muestra_como_desconocida(self):
        from app.services.correos_imap import _crear_mensaje

        mensajes = (
            _crear_mensaje(1, b"1 (UID 1 FLAGS ())", b"From: a@example.com\r\n\r\n"),
            _crear_mensaje(
                2,
                b'2 (UID 2 FLAGS () INTERNALDATE "fecha-invalida"',
                b"From: b@example.com\r\nDate: no es una fecha\r\n\r\n",
            ),
        )

        self.assertEqual([mensaje.fecha for mensaje in mensajes], ["Fecha desconocida", "Fecha desconocida"])


class CorreoIMAPRoutesTests(unittest.TestCase):
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
            email="admin-imap@example.com",
            rol="admin",
        )
        self.administrador.set_password("clave-segura-para-imap")
        db.session.add(self.administrador)
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.context.pop()
        self.database_config_patch.stop()

    def iniciar_sesion(self):
        respuesta = self.client.post(
            "/ingresar",
            data={
                "email": "admin-imap@example.com",
                "password": "clave-segura-para-imap",
            },
        )
        self.assertEqual(respuesta.status_code, 302)

    def test_ruta_de_bandeja_exige_autenticacion(self):
        with patch("app.blueprints.admin.correos.listar_mensajes") as listar:
            respuesta = self.client.get("/admin/correos")

        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("/ingresar", respuesta.headers["Location"])
        listar.assert_not_called()

    def test_administrador_ve_el_menu_y_la_lista_de_mensajes(self):
        self.iniciar_sesion()
        with patch(
            "app.blueprints.admin.correos.listar_mensajes",
            return_value=[
                MensajeCorreo(7, "remitente@example.com", "Pendiente", "16/11/2026 13:59", False),
                MensajeCorreo(8, "otro@example.com", "Mensaje leído", "16/11/2026 12:00", True),
            ],
        ):
            respuesta = self.client.get("/admin/correos")

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("Bandeja de entrada".encode(), respuesta.data)
        self.assertIn("remitente@example.com".encode(), respuesta.data)
        self.assertIn(b"No le\xc3\xaddo", respuesta.data)
        self.assertIn("Leído".encode(), respuesta.data)
        self.assertIsNotNone(
            re.search(rb'<a class="fw-bold"\s+href="/admin/correos/7">Pendiente', respuesta.data)
        )
        self.assertIsNotNone(
            re.search(rb'<a class=""\s+href="/admin/correos/8">Mensaje le\xc3\xaddo', respuesta.data)
        )
        self.assertIn("Actualizar".encode(), respuesta.data)
        self.assertIn(b"/admin/correos/7", respuesta.data)

    def test_lista_muestra_un_mensaje_claro_cuando_no_hay_correos(self):
        self.iniciar_sesion()
        with patch("app.blueprints.admin.correos.listar_mensajes", return_value=[]):
            respuesta = self.client.get("/admin/correos")

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("No hay correos en la bandeja de entrada.".encode(), respuesta.data)

    def test_cuenta_que_deja_de_ser_admin_pierde_acceso_a_la_bandeja(self):
        self.iniciar_sesion()
        self.administrador.rol = "usuario"
        db.session.commit()

        respuesta = self.client.get("/admin/correos")

        self.assertEqual(respuesta.status_code, 403)

    def test_error_imap_no_expone_detalles_en_la_respuesta(self):
        self.iniciar_sesion()
        with self.assertLogs("app", level="WARNING") as registros:
            with patch(
                "app.blueprints.admin.correos.listar_mensajes",
                side_effect=ErrorCorreoIMAP("secreto-de-prueba"),
            ):
                respuesta = self.client.get("/admin/correos")

        self.assertEqual(respuesta.status_code, 503)
        self.assertIn("Verifica la configuración IMAP".encode(), respuesta.data)
        self.assertNotIn(b"secreto-de-prueba", respuesta.data)
        self.assertNotIn("secreto-de-prueba", " ".join(registros.output))

    def test_detalle_escapa_el_contenido_texto(self):
        self.iniciar_sesion()
        mensaje = MensajeCorreoDetalle(
            7,
            "remitente@example.com",
            "Asunto",
            "2026-11-16",
            False,
            "<script>alert(1)</script>",
            False,
        )
        with patch(
            "app.blueprints.admin.correos.obtener_mensaje",
            return_value=mensaje,
        ):
            respuesta = self.client.get("/admin/correos/7")

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(b"&lt;script&gt;alert(1)&lt;/script&gt;", respuesta.data)
        self.assertNotIn(b"<script>alert(1)</script>", respuesta.data)


if __name__ == "__main__":
    unittest.main()
