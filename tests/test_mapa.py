import json
import re
import unittest
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import Municipio
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

    def test_portada_usa_coordenadas_existentes_de_semilla_si_faltan_en_bd(self):
        respuesta = self.client.get("/")

        self.assertEqual(respuesta.status_code, 200)
        puntos = self.puntos_serializados(respuesta)
        self.assertEqual(len(puntos), len(MUNICIPIOS))
        self.assertEqual(
            (puntos[0]["lat"], puntos[0]["lng"]),
            MUNICIPIOS[0][1:],
        )
        self.assertTrue(all(not punto["seleccionado"] for punto in puntos))

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


if __name__ == "__main__":
    unittest.main()
