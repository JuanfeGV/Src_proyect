import json
import re
import unittest
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import IndicadorMunicipio, Municipio
from app.services.consultas import (
    INDICADORES_COBERTURA,
    NOMBRE_INDICADOR_RECURRENCIA,
)
from app.services.semilla import MUNICIPIOS
from app.utils.texto import crear_slug
from config import DevelopmentConfig


class MapaMunicipiosTests(unittest.TestCase):
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
        db.session.add_all(
            Municipio(nombre=nombre, slug=crear_slug(nombre))
            for nombre, _, _ in MUNICIPIOS
        )
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()
        self.database_config_patch.stop()

    def puntos_serializados(self, respuesta):
        match = re.search(
            rb'<script type="application/json" id="mapa-municipios-datos">(.*?)</script>',
            respuesta.data,
            re.S,
        )
        self.assertIsNotNone(match)
        return json.loads(match.group(1))

    def test_portada_usa_coordenadas_semilla_e_incluye_indicadores(self):
        respuesta = self.client.get("/")

        self.assertEqual(respuesta.status_code, 200)
        puntos = self.puntos_serializados(respuesta)
        self.assertEqual(len(puntos), len(MUNICIPIOS))
        self.assertEqual(
            (puntos[0]["lat"], puntos[0]["lng"]),
            MUNICIPIOS[0][1:],
        )
        self.assertTrue(all(not punto["seleccionado"] for punto in puntos))
        self.assertIsNone(puntos[0]["cobertura"]["prioridad"])
        self.assertIsNone(puntos[0]["recurrencia"]["nivel"])
        self.assertIn(b'data-indicadores="true"', respuesta.data)

    def test_inicio_y_municipios_comparten_prioridades_y_recurrencias(self):
        prioridades = {
            "cajica": "alta",
            "chia": "baja",
            "cogua": "media",
            "cota": "alta",
            "gachancipa": "alta",
            "nemocon": "alta",
            "sopo": "baja",
            "tabio": "alta",
            "tenjo": "baja",
            "tocancipa": "baja",
            "zipaquira": "media",
        }
        valores = {"alta": "70", "media": "90", "baja": "98"}
        fuente_ideam = "https://www.ideam.gov.co/sites/default/files/anexo-ena-2022"
        for slug, prioridad in prioridades.items():
            municipio = Municipio.query.filter_by(slug=slug).one()
            db.session.add(
                IndicadorMunicipio(
                    municipio=municipio,
                    nombre=INDICADORES_COBERTURA["rural"],
                    valor=valores[prioridad],
                    periodo="2024",
                )
            )
            if slug in ("chia", "zipaquira"):
                db.session.add(
                    IndicadorMunicipio(
                        municipio=municipio,
                        nombre=NOMBRE_INDICADOR_RECURRENCIA,
                        valor="Baja",
                        periodo="ENA 2022",
                        fuente=fuente_ideam,
                    )
                )
        db.session.commit()

        respuesta_inicio = self.client.get("/")
        respuesta_municipios = self.client.get("/municipios")
        puntos_inicio = {
            punto["slug"]: punto
            for punto in self.puntos_serializados(respuesta_inicio)
        }
        puntos_municipios = {
            punto["slug"]: punto
            for punto in self.puntos_serializados(respuesta_municipios)
        }

        self.assertEqual(respuesta_inicio.status_code, 200)
        self.assertEqual(respuesta_municipios.status_code, 200)
        self.assertEqual(len(puntos_inicio), 11)
        for slug, prioridad in prioridades.items():
            self.assertEqual(
                puntos_inicio[slug]["cobertura"]["prioridad"],
                prioridad,
            )
            self.assertEqual(
                puntos_inicio[slug]["cobertura"]["prioridad"],
                puntos_municipios[slug]["cobertura"]["prioridad"],
            )
            self.assertEqual(
                puntos_inicio[slug]["url"],
                f"/municipios/{slug}",
            )
        for slug in ("chia", "zipaquira"):
            self.assertEqual(
                puntos_inicio[slug]["recurrencia"]["nivel"],
                "baja",
            )
        self.assertTrue(
            all(
                punto["recurrencia"]["nivel"] is None
                for slug, punto in puntos_inicio.items()
                if slug not in ("chia", "zipaquira")
            )
        )
        html_inicio = respuesta_inicio.get_data(as_text=True)
        self.assertEqual(html_inicio.count('class="chip-municipio"'), 11)
        for slug, prioridad in prioridades.items():
            municipio = Municipio.query.filter_by(slug=slug).one()
            patron = (
                re.escape(f"<span>{municipio.nombre}</span>")
                + r'\s*<span class="cobertura-prioridad cobertura-prioridad--'
                + prioridad
                + r'">\s*Prioridad '
                + prioridad
            )
            self.assertRegex(html_inicio, patron)

    def test_municipio_filtrado_se_resalta_en_el_mapa(self):
        respuesta = self.client.get("/municipios?municipio=chia")

        self.assertEqual(respuesta.status_code, 200)
        puntos = self.puntos_serializados(respuesta)
        self.assertEqual(len(puntos), 1)
        self.assertEqual(puntos[0]["nombre"], "Chía")
        self.assertTrue(puntos[0]["seleccionado"])

    def test_coordenadas_invalidas_no_se_incluyen_en_el_mapa(self):
        db.session.add(
            Municipio(nombre="Municipio inválido", slug="municipio-invalido", latitud=95, longitud=-74)
        )
        db.session.commit()

        respuesta = self.client.get("/municipios")

        self.assertEqual(respuesta.status_code, 200)
        puntos = self.puntos_serializados(respuesta)
        self.assertEqual(len(puntos), len(MUNICIPIOS))
        self.assertNotIn("Municipio inválido", [punto["nombre"] for punto in puntos])

    def test_coordenadas_guardadas_validas_tienen_precedencia_sobre_semilla(self):
        municipio = Municipio.query.filter_by(nombre="Chía").one()
        municipio.latitud = 4.5
        municipio.longitud = -73.9
        db.session.commit()

        respuesta = self.client.get("/municipios?municipio=chia")

        punto = self.puntos_serializados(respuesta)[0]
        self.assertEqual((punto["lat"], punto["lng"]), (4.5, -73.9))

    def test_coordenada_parcialmente_ausente_usa_el_par_de_semilla(self):
        municipio = Municipio.query.filter_by(nombre="Chía").one()
        municipio.latitud = 4.8
        municipio.longitud = None
        db.session.commit()

        respuesta = self.client.get("/municipios?municipio=chia")

        punto = self.puntos_serializados(respuesta)[0]
        self.assertEqual((punto["lat"], punto["lng"]), MUNICIPIOS[1][1:])

    def test_mapa_de_municipios_carga_indicadores_sin_inferir_faltantes(self):
        fuente = (
            "https://www.ideam.gov.co/sites/default/files/"
            "anexo-ena-2022"
        )
        for slug in ("chia", "zipaquira"):
            municipio = Municipio.query.filter_by(slug=slug).one()
            db.session.add(
                IndicadorMunicipio(
                    municipio=municipio,
                    nombre=NOMBRE_INDICADOR_RECURRENCIA,
                    valor="Baja",
                    periodo="ENA 2022",
                    fuente=fuente,
                )
            )
        db.session.commit()

        respuesta = self.client.get("/municipios")
        puntos = self.puntos_serializados(respuesta)
        por_slug = {punto["slug"]: punto for punto in puntos}

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(b'data-indicadores="true"', respuesta.data)
        self.assertEqual(len(puntos), 11)
        self.assertEqual(por_slug["chia"]["recurrencia"]["nivel"], "baja")
        self.assertEqual(por_slug["zipaquira"]["recurrencia"]["nivel"], "baja")
        self.assertEqual(por_slug["chia"]["recurrencia"]["periodo"], "ENA 2022")
        self.assertEqual(por_slug["chia"]["recurrencia"]["fuente_url"], fuente)
        self.assertTrue(
            all(
                punto["recurrencia"]["nivel"] is None
                for slug, punto in por_slug.items()
                if slug not in ("chia", "zipaquira")
            )
        )


if __name__ == "__main__":
    unittest.main()
