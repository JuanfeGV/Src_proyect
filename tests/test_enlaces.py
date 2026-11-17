import unittest
from html.parser import HTMLParser
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import Articulo, GuiaConsumo, IndicadorMunicipio, Municipio
from app.utils.texto import a_parrafos, enlaces_seguros
from config import DevelopmentConfig


class EnlacesParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.enlaces = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.enlaces.append(dict(attrs))


class EnlacesSegurosTests(unittest.TestCase):
    def test_enlaza_solo_destinos_web_o_rutas_internas_y_escapa_texto(self):
        resultado = str(
            enlaces_seguros(
                "Fuente (https://example.gov/documento.pdf); www.example.org/guia. "
                "/municipios/chia ../documento.pdf javascript:alert(1) "
                "data:text/html,x file:///etc/passwd https://usuario@ejemplo.gov/a "
                "https://ejemplo.gov:puerto/a //externo.gov/a <script>alert(1)</script>"
            )
        )
        parser = EnlacesParser()
        parser.feed(resultado)

        self.assertEqual(len(parser.enlaces), 4)
        externos = parser.enlaces[:2]
        for enlace in externos:
            self.assertEqual(enlace["target"], "_blank")
            self.assertEqual(enlace["rel"], "noopener noreferrer")
        self.assertEqual(externos[0]["href"], "https://example.gov/documento.pdf")
        self.assertEqual(externos[1]["href"], "https://www.example.org/guia")
        self.assertEqual(parser.enlaces[2]["href"], "/municipios/chia")
        self.assertNotIn("target", parser.enlaces[2])
        self.assertEqual(parser.enlaces[3]["href"], "../documento.pdf")
        self.assertNotIn("javascript:", resultado.lower().split("<a", 1)[0])
        self.assertIn("javascript:alert(1)", resultado)
        self.assertIn("data:text/html,x", resultado)
        self.assertIn("file:///etc/passwd", resultado)
        self.assertIn("https://usuario@ejemplo.gov/a", resultado)
        self.assertIn("https://ejemplo.gov:puerto/a", resultado)
        self.assertIn("//externo.gov/a", resultado)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", resultado)
        self.assertNotIn("<script>", resultado)

    def test_parrafos_conserva_saltos_y_convierte_urls_sin_confiar_en_html(self):
        resultado = str(a_parrafos("Texto <b>literal</b>.\nFuente: https://example.gov/a.pdf."))

        self.assertIn("<p>Texto &lt;b&gt;literal&lt;/b&gt;.<br>Fuente:", resultado)
        self.assertIn(
            '<a href="https://example.gov/a.pdf" target="_blank" rel="noopener noreferrer">',
            resultado,
        )
        self.assertTrue(resultado.endswith("</p>"))


class NavegacionEnlacesTests(unittest.TestCase):
    def setUp(self):
        self.database_config_patch = patch.object(
            DevelopmentConfig,
            "SQLALCHEMY_DATABASE_URI",
            "sqlite:///:memory:",
        )
        self.database_config_patch.start()
        self.app = create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()

        self.municipio = Municipio(nombre="Chía", slug="chia")
        db.session.add(self.municipio)
        db.session.flush()
        self.articulo = Articulo(
            titulo="Noticia de prueba",
            slug="noticia-de-prueba",
            resumen="Fuente: www.example.org/noticia.",
            contenido=(
                "Fuente oficial: https://example.gov/noticia.pdf).\n\n"
                "Ruta local: /municipios/chia.\n"
                "No enlazar: javascript:alert(1)"
            ),
            categoria="noticia",
            publicado=True,
            municipio=self.municipio,
        )
        self.guia = GuiaConsumo(
            titulo="Guía de prueba",
            resumen="Consulta https://example.gov/guia.pdf.",
            contenido="Referencia: ../documentos/guia.pdf.",
            nivel_riesgo="todos",
            publicada=True,
        )
        self.indicador = IndicadorMunicipio(
            municipio=self.municipio,
            nombre="Calidad de agua",
            valor="Sin dato",
            periodo="2024",
            fuente="https://www.ins.gov.co/reporte.pdf",
        )
        db.session.add_all([self.articulo, self.guia, self.indicador])
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()
        self.database_config_patch.stop()

    def _enlaces(self, respuesta):
        parser = EnlacesParser()
        parser.feed(respuesta.get_data(as_text=True))
        return parser.enlaces

    def test_rutas_internas_de_articulos_y_guias_se_resuelven(self):
        noticias = self.client.get("/noticias")
        enlaces_noticias = self._enlaces(noticias)
        ruta_articulo = next(
            enlace["href"]
            for enlace in enlaces_noticias
            if enlace.get("href") == "/noticias/noticia-de-prueba"
        )
        self.assertEqual(self.client.get(ruta_articulo).status_code, 200)

        aprende = self.client.get("/aprende")
        self.assertIn("/aprende/guias/1", [enlace.get("href") for enlace in self._enlaces(aprende)])
        self.assertEqual(self.client.get("/aprende/guias/1").status_code, 200)

    def test_fuentes_de_articulos_guias_e_indicadores_son_enlaces_seguros(self):
        respuesta_articulo = self.client.get("/noticias/noticia-de-prueba")
        html_articulo = respuesta_articulo.get_data(as_text=True)
        enlaces_articulo = self._enlaces(respuesta_articulo)
        self.assertIn("https://example.gov/noticia.pdf", html_articulo)
        self.assertIn("/municipios/chia", html_articulo)
        self.assertIn("javascript:alert(1)", html_articulo)

        respuesta_guia = self.client.get("/aprende/guias/1")
        respuesta_municipio = self.client.get("/municipios/chia")
        enlaces = (
            enlaces_articulo
            + self._enlaces(respuesta_guia)
            + self._enlaces(respuesta_municipio)
        )
        externos = [
            enlace
            for enlace in enlaces
            if (enlace.get("href") or "").startswith(("http://", "https://"))
        ]
        self.assertTrue(any(enlace["href"] == "https://example.gov/noticia.pdf" for enlace in externos))
        self.assertTrue(any(enlace["href"] == "https://example.gov/guia.pdf" for enlace in externos))
        self.assertTrue(any(enlace["href"] == "https://www.ins.gov.co/reporte.pdf" for enlace in externos))
        for enlace in externos:
            self.assertEqual(enlace.get("target"), "_blank")
            self.assertEqual(enlace.get("rel"), "noopener noreferrer")

    def test_paginacion_no_renderiza_enlaces_sin_destino(self):
        db.session.add_all(
            Articulo(
                titulo=f"Noticia adicional {indice}",
                slug=f"noticia-adicional-{indice}",
                contenido="Contenido de prueba.",
                categoria="noticia",
                publicado=True,
            )
            for indice in range(9)
        )
        db.session.commit()

        respuesta = self.client.get("/noticias")
        html = respuesta.get_data(as_text=True)

        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn('href="#"', html)
        self.assertIn('aria-disabled="true">Anterior</span>', html)
