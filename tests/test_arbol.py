import re
import unittest
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import NodoArbol
from app.services.consultas import estructura_arbol
from config import DevelopmentConfig


class ArbolPublicoTests(unittest.TestCase):
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
        self._crear_arbol()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()
        self.database_config_patch.stop()

    def _crear_nodo(self, tipo, titulo, padre=None, descripcion=None, fuente=None):
        nodo = NodoArbol(
            tipo=tipo,
            titulo=titulo,
            descripcion=descripcion,
            fuente=fuente,
            orden=0,
            padre=padre,
        )
        db.session.add(nodo)
        db.session.flush()
        return nodo

    def _crear_arbol(self):
        central = self._crear_nodo(
            "problema_central",
            "Problema hídrico central",
            descripcion="Descripción completa del problema.",
            fuente="Informe oficial, página 10",
        )
        self.nodos = [central]
        for indice in range(2):
            directo = self._crear_nodo(
                "efecto_directo",
                f"Efecto directo {indice}",
                central,
                descripcion="<img src=x onerror=alert(1)>",
                fuente="javascript:alert(1)",
            )
            self.nodos.append(directo)
            for hijo in range(2):
                self.nodos.append(
                    self._crear_nodo(
                        "efecto_indirecto",
                        f"Efecto indirecto {indice}-{hijo}",
                        directo,
                    )
                )
        for indice in range(3):
            directo = self._crear_nodo("causa_directa", f"Causa directa {indice}", central)
            self.nodos.append(directo)
            for hijo in range(2):
                self.nodos.append(
                    self._crear_nodo(
                        "causa_indirecta",
                        f"Causa indirecta {indice}-{hijo}",
                        directo,
                    )
                )
        db.session.commit()

    def test_diagrama_muestra_16_nodos_y_solo_sus_relaciones_guardadas(self):
        estructura = estructura_arbol()

        self.assertEqual(len(estructura["nodos"]), 16)
        self.assertEqual(len(estructura["enlaces"]), 15)
        relaciones_guardadas = {
            (nodo.padre_id, nodo.id) for nodo in self.nodos if nodo.padre_id is not None
        }
        relaciones_dibujadas = {
            (enlace["padre_id"], enlace["hijo_id"]) for enlace in estructura["enlaces"]
        }
        self.assertEqual(relaciones_dibujadas, relaciones_guardadas)

        respuesta = self.client.get("/aprende")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data.count(b'class="arbol-nodo '), 16)
        self.assertEqual(respuesta.data.count(b'class="arbol-conector '), 15)
        self.assertIn(b"efectos indirectos", respuesta.data)
        self.assertIn(b"causas indirectas", respuesta.data)
        self.assertNotIn(b"arbol-leyenda", respuesta.data)
        self.assertNotIn(b"Leyenda del \xc3\xa1rbol", respuesta.data)
        self.assertIn(b"aria-expanded=\"false\"", respuesta.data)
        self.assertIn(b"Expandir efectos indirectos", respuesta.data)
        self.assertIn(b"Expandir causas indirectas", respuesta.data)
        self.assertIn(b'id="efecto-indirecto"', respuesta.data)
        self.assertIn(b'id="causa-indirecta"', respuesta.data)
        self.assertRegex(
            respuesta.data,
            rb'id="efecto-indirecto"[^>]*hidden',
        )
        self.assertRegex(
            respuesta.data,
            rb'id="causa-indirecta"[^>]*hidden',
        )

    def test_relacion_faltante_se_advierte_y_no_se_inventa_conector(self):
        hijo = next(nodo for nodo in self.nodos if nodo.tipo == "efecto_indirecto")
        hijo.padre_id = None
        db.session.commit()

        estructura = estructura_arbol()
        self.assertEqual(len(estructura["nodos"]), 16)
        self.assertEqual(len(estructura["enlaces"]), 14)
        self.assertTrue(any("no tiene una relación padre" in aviso for aviso in estructura["advertencias"]))

        respuesta = self.client.get("/aprende")
        self.assertIn(b"no tiene una relaci\xc3\xb3n padre", respuesta.data)

    def test_contenido_se_escapa_y_controles_y_fuentes_se_muestran(self):
        respuesta = self.client.get("/aprende")

        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn(b"<img src=x onerror=alert(1)>", respuesta.data)
        self.assertIn(b"&lt;img src=x onerror=alert(1)&gt;", respuesta.data)
        self.assertIn(b"javascript:alert(1)", respuesta.data)
        self.assertIn(b"aria-pressed=\"false\"", respuesta.data)
        self.assertIn(b"aria-expanded=\"false\"", respuesta.data)
        self.assertIn(b"Informe oficial, p\xc3\xa1gina 10", respuesta.data)
        self.assertIn(b"arbol.js", respuesta.data)

    def test_aprende_muestra_guias_antes_del_arbol(self):
        respuesta = self.client.get("/aprende")

        self.assertEqual(respuesta.status_code, 200)
        self.assertLess(
            respuesta.data.index(b'<section class="tarjeta-agua" id="guias">'),
            respuesta.data.index(b'<section class="tarjeta-agua mt-4" id="arbol">'),
        )
        self.assertEqual(respuesta.data.count(b'class="arbol-componente"'), 1)

    def test_inicio_no_muestra_ni_carga_el_arbol(self):
        respuesta = self.client.get("/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn(b'class="arbol-componente"', respuesta.data)
        self.assertNotIn(b"js/arbol.js", respuesta.data)
        self.assertIn(b"/aprende#arbol", respuesta.data)
        self.assertIn(b"Reporte ciudadano", respuesta.data)
        self.assertIn(b"Municipios de Sabana Centro", respuesta.data)

    def test_sin_nodos_muestra_estado_vacio(self):
        db.session.query(NodoArbol).delete()
        db.session.commit()

        respuesta = self.client.get("/aprende")

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(b"El \xc3\xa1rbol del problema todav\xc3\xada no ha sido cargado.", respuesta.data)
        self.assertNotIn(b"class=\"arbol-diagrama\"", respuesta.data)


if __name__ == "__main__":
    unittest.main()
