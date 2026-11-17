import json
import re
import unittest
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import IndicadorMunicipio, Municipio
from app.services.consultas import (
    FUENTE_COBERTURA_URL,
    NOMBRE_INDICADOR_RECURRENCIA,
    evaluar_cobertura_municipal,
    evaluar_recurrencia_municipal,
)
from app.services.semilla import MUNICIPIOS
from app.utils.texto import crear_slug
from config import DevelopmentConfig


class EvaluacionMunicipalTests(unittest.TestCase):
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

    def agregar_indicador(self, municipio, nombre, valor, fuente=None):
        db.session.add(
            IndicadorMunicipio(
                municipio=municipio,
                nombre=nombre,
                valor=valor,
                periodo="2024",
                fuente=fuente,
            )
        )

    def test_prioridad_respeta_los_limites_incluidos(self):
        casos = [
            ("79.999", "alta"),
            ("80", "media"),
            ("94.999", "media"),
            ("95", "baja"),
        ]
        for valor, prioridad_esperada in casos:
            municipio = Municipio(
                nombre="Municipio de prueba",
                slug="municipio-de-prueba",
                indicadores=[
                    IndicadorMunicipio(
                        nombre="Cobertura acueducto rural (serie tratada)",
                        valor=valor,
                        periodo="2024",
                    )
                ],
            )

            evaluacion = evaluar_cobertura_municipal(municipio)

            self.assertEqual(evaluacion["prioridad"], prioridad_esperada)

    def test_valores_ausentes_o_invalidos_quedan_sin_evaluar(self):
        for valor in (None, "", "texto", "NaN", "-1", "100.01"):
            municipio = Municipio(
                nombre="Municipio de prueba",
                slug="municipio-de-prueba",
                indicadores=[
                    IndicadorMunicipio(
                        nombre="Cobertura acueducto rural (serie tratada)",
                        valor=valor,
                        periodo="2024",
                    )
                ],
            )

            evaluacion = evaluar_cobertura_municipal(municipio)

            self.assertIsNone(evaluacion["rural"])
            self.assertEqual(evaluacion["prioridad_texto"], "Sin evaluar")

    def test_diferencia_urbana_menos_rural_y_fuente_oficial(self):
        municipio = Municipio(
            nombre="Municipio de prueba",
            slug="municipio-de-prueba",
            indicadores=[
                IndicadorMunicipio(
                    nombre="Cobertura acueducto urbana (serie tratada)",
                    valor="90,5",
                    periodo="2024",
                    fuente=FUENTE_COBERTURA_URL,
                ),
                IndicadorMunicipio(
                    nombre="Cobertura acueducto rural (serie tratada)",
                    valor="70,25",
                    periodo="2024",
                ),
            ],
        )

        evaluacion = evaluar_cobertura_municipal(municipio)

        self.assertEqual(evaluacion["urbana_texto"], "90,5")
        self.assertEqual(evaluacion["rural_texto"], "70,25")
        self.assertEqual(evaluacion["diferencia_texto"], "20,25")
        self.assertEqual(evaluacion["prioridad"], "alta")
        self.assertEqual(evaluacion["fuente_url"], FUENTE_COBERTURA_URL)

    def test_fuente_no_oficial_no_se_convierte_en_enlace(self):
        municipio = Municipio(
            nombre="Municipio de prueba",
            slug="municipio-de-prueba",
            indicadores=[
                IndicadorMunicipio(
                    nombre="Cobertura acueducto rural (serie tratada)",
                    valor="70",
                    periodo="2024",
                    fuente="javascript:alert(1)",
                )
            ],
        )

        evaluacion = evaluar_cobertura_municipal(municipio)

        self.assertEqual(evaluacion["fuente_url"], FUENTE_COBERTURA_URL)

    def test_recurrencia_solo_usa_registro_exactamente_periodado_y_clasificado(self):
        municipio = Municipio(
            nombre="Municipio de prueba",
            slug="municipio-de-prueba",
            indicadores=[
                IndicadorMunicipio(
                    nombre=NOMBRE_INDICADOR_RECURRENCIA,
                    valor="Alta",
                    periodo="2022",
                ),
                IndicadorMunicipio(
                    nombre=NOMBRE_INDICADOR_RECURRENCIA,
                    valor="Baja",
                    periodo="ENA 2022",
                    fuente=(
                        "https://www.ideam.gov.co/sites/default/files/"
                        "anexo-ena-2022"
                    ),
                ),
            ],
        )

        evaluacion = evaluar_recurrencia_municipal(municipio)

        self.assertEqual(evaluacion["nivel"], "baja")
        self.assertEqual(evaluacion["texto"], "Baja")
        self.assertEqual(evaluacion["periodo"], "ENA 2022")
        self.assertTrue(evaluacion["fuente_url"].startswith("https://www.ideam.gov.co/"))

    def test_ausencia_de_recurrencia_no_se_interpreta_como_baja(self):
        municipio = Municipio(nombre="Municipio de prueba", slug="municipio-de-prueba")

        evaluacion = evaluar_recurrencia_municipal(municipio)

        self.assertIsNone(evaluacion["nivel"])
        self.assertEqual(evaluacion["texto"], "Sin clasificación documentada")
        self.assertIsNone(evaluacion["fuente_url"])

    def test_comparacion_muestra_los_once_municipios_aun_sin_indicadores(self):
        respuesta = self.client.get("/municipios")
        html = respuesta.get_data(as_text=True)

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(html.count('class="fila-comparacion-cobertura"'), 11)
        self.assertEqual(html.count('data-prioridad="sin-evaluar"'), 11)
        self.assertEqual(html.count('class="municipio-acordeon__toggle"'), 11)
        self.assertEqual(
            len(
                re.findall(
                    r'class="municipio-acordeon__toggle"[^>]*aria-expanded="false"'
                    r'[^>]*aria-controls="municipio-',
                    html,
                )
            ),
            11,
        )
        self.assertEqual(html.count('class="municipio-acordeon__panel"'), 11)
        self.assertIn('id="alternar-todos-municipios"', html)
        self.assertIn('aria-controls="municipios-acordeon"', html)
        self.assertIn("Sin evaluar", html)

    def test_porcentajes_de_tarjetas_y_tabla_usan_dos_decimales_espanoles(self):
        chia = Municipio.query.filter_by(slug="chia").one()
        self.agregar_indicador(
            chia,
            "Cobertura acueducto rural (serie tratada)",
            "98.815",
        )
        self.agregar_indicador(
            chia,
            "Cobertura acueducto urbana (serie tratada)",
            "99.93",
        )
        db.session.commit()

        respuesta = self.client.get("/municipios")
        html = respuesta.get_data(as_text=True)

        self.assertEqual(respuesta.status_code, 200)
        self.assertGreaterEqual(html.count("98,82 %"), 2)
        self.assertGreaterEqual(html.count("99,93 %"), 1)

    def test_filtro_de_prioridad_conserva_mapa_y_nivel_de_riesgo(self):
        chia = Municipio.query.filter_by(slug="chia").one()
        chia.nivel_riesgo = "medio"
        self.agregar_indicador(
            chia,
            "Cobertura acueducto rural (serie tratada)",
            "98.815",
        )
        self.agregar_indicador(
            chia,
            "Cobertura acueducto urbana (serie tratada)",
            "99.93",
        )
        db.session.commit()

        respuesta = self.client.get("/municipios?prioridad_cobertura=baja")
        html = respuesta.get_data(as_text=True)
        match = re.search(
            r'<script type="application/json" id="mapa-municipios-datos">(.*?)</script>',
            html,
            re.S,
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(html.count('class="fila-comparacion-cobertura"'), 1)
        self.assertIn("Chía", html)
        self.assertIsNotNone(match)
        puntos = json.loads(match.group(1))
        self.assertEqual(len(puntos), 1)
        self.assertEqual(puntos[0]["nivel"], "medio")
        self.assertEqual(Municipio.query.filter_by(slug="chia").one().nivel_riesgo, "medio")

    def test_ficha_muestra_cobertura_prioridad_riesgo_y_fuente(self):
        chia = Municipio.query.filter_by(slug="chia").one()
        chia.nivel_riesgo = "medio"
        self.agregar_indicador(
            chia,
            "Cobertura acueducto urbana (serie tratada)",
            "90",
            FUENTE_COBERTURA_URL,
        )
        self.agregar_indicador(
            chia,
            "Cobertura acueducto rural (serie tratada)",
            "70",
        )
        db.session.commit()

        respuesta = self.client.get("/municipios/chia")
        html = respuesta.get_data(as_text=True)

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("Cobertura urbana", html)
        self.assertIn("90 %", html)
        self.assertIn("70 %", html)
        self.assertIn("20 pp", html)
        self.assertIn("corresponde a prioridad alta", html)
        self.assertIn("Riesgo de desabastecimiento:", html)
        self.assertIn("Anexo 1 de Superservicios (2024)", html)
        self.assertIn(FUENTE_COBERTURA_URL, html)
        self.assertEqual(Municipio.query.filter_by(slug="chia").one().nivel_riesgo, "medio")


if __name__ == "__main__":
    unittest.main()
