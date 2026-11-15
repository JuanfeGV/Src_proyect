"""Datos iniciales del portal.

- El árbol del problema sale del documento del proyecto (con las páginas del informe).
- Los municipios son los 11 de Sabana Centro. Las coordenadas son APROXIMADAS
  (centro del casco urbano) y el administrador puede corregirlas.
- Guías y artículos son CONTENIDO DE EJEMPLO para ver el diseño; se reemplazan
  desde el panel de administración.
- Los datos de agua de cada municipio (riesgo, indicadores) NO se inventan:
  los carga el administrador.
"""
from ..extensions import db
from ..models import Articulo, GuiaConsumo, Municipio, NodoArbol
from ..utils.texto import crear_slug

MUNICIPIOS = [
    ("Cajicá", 4.9186, -74.0277),
    ("Chía", 4.8587, -74.0326),
    ("Cogua", 5.0600, -73.9784),
    ("Cota", 4.8100, -74.1020),
    ("Gachancipá", 4.9910, -73.8750),
    ("Nemocón", 5.0678, -73.8786),
    ("Sopó", 4.9057, -73.9411),
    ("Tabio", 4.9170, -74.0970),
    ("Tenjo", 4.8730, -74.1430),
    ("Tocancipá", 4.9650, -73.9120),
    ("Zipaquirá", 5.0225, -74.0046),
]

PROBLEMA_CENTRAL = (
    "¿Cómo articular el crecimiento urbano con la oferta hídrica real en Sabana Centro "
    "para evitar el desabastecimiento y la contaminación ambiental?",
    "Págs. 175, 196",
)

# (efecto directo, fuente, [(efecto indirecto, fuente), ...])
EFECTOS = [
    (
        "Racionamiento y desabastecimiento de agua potable",
        "Págs. 165, 175",
        [
            ("Riesgos sanitarios e incremento del IRCA en zonas urbanas y rurales", "Pág. 187"),
            ("Conflictos socioambientales por el acceso al agua", "Pág. 196"),
            ("Pérdida de biodiversidad en la cuenca alta", "Págs. 196, 201"),
        ],
    ),
    (
        "Deterioro crítico de la calidad del agua en la cuenca del río Bogotá",
        "Págs. 183, 196",
        [
            ("Freno al desarrollo económico por falta de factibilidad hídrica", "Pág. 175"),
            ("Sobrecostos en tarifas por potabilización de agua contaminada", "Pág. 197"),
            ("Vulnerabilidad territorial ante sequías y cambio climático", "Pág. 176"),
        ],
    ),
]

# (causa directa, fuente, [(causa indirecta, fuente), ...])
CAUSAS = [
    (
        "Expansión urbana sin garantía de abastecimiento a largo plazo",
        "Pág. 175",
        [
            ("POT desactualizados e hiperlicenciamiento de vivienda", "Págs. 175, 176"),
            ("Débil articulación entre Municipios, CAR y prestadores", "Págs. 176, 197"),
        ],
    ),
    (
        "Capacidad insuficiente de saneamiento y tratamiento de aguas servidas — PTAR",
        "Págs. 175, 197",
        [
            ("Pérdidas de agua por redes obsoletas — Agua No Contabilizada", "Pág. 175"),
            ("Infraestructura de PTAP y PTAR con capacidad sobrepasada", "Págs. 175, 197"),
        ],
    ),
    (
        "Degradación ambiental de la cuenca alta y zonas de recarga",
        "Págs. 196, 197",
        [
            ("Deforestación y cambio de uso de suelo en rondas hídricas", "Pág. 196"),
            ("Presupuestos municipales limitados para obras hídricas de gran escala", "Pág. 197"),
        ],
    ),
]

EJEMPLO = "(Contenido de ejemplo: reemplazar desde el panel de administración)"

GUIAS = [
    ("Revisa y repara las fugas en casa", "todos",
     "Un grifo o sanitario que gotea desperdicia agua todos los días. Revisa llaves, tuberías y "
     "sanitarios con regularidad y repara cualquier fuga lo antes posible."),
    ("Cierra el grifo mientras no lo uses", "todos",
     "Cierra la llave al cepillarte los dientes, enjabonarte o lavar los platos. "
     "Abre el agua solo cuando la necesites."),
    ("Riega en las horas más frescas", "medio",
     "Riega las plantas temprano en la mañana o al final de la tarde para que el agua "
     "no se evapore con el sol."),
    ("Reutiliza el agua cuando sea posible", "medio",
     "El agua con la que lavaste frutas o verduras puede servir para regar las plantas. "
     "Recoge el agua fría que corre mientras esperas que salga caliente."),
    ("Almacena agua de forma segura", "alto",
     "Si hay racionamiento, guarda agua en recipientes limpios y tapados, y renuévala con "
     "frecuencia para mantenerla en buen estado."),
    ("Prioriza los usos esenciales", "alto",
     "Durante la escasez, reserva el agua para beber, cocinar y la higiene. "
     "Aplaza el lavado de vehículos, patios y otros usos que no sean urgentes."),
]

ARTICULOS = [
    (
        "¿Por qué hay racionamiento en Sabana Centro?",
        "Las causas del racionamiento según el árbol del problema del proyecto.",
        "Según el árbol del problema, el racionamiento y desabastecimiento de agua potable se "
        "relaciona con tres causas directas: la expansión urbana sin garantía de abastecimiento "
        "a largo plazo, la capacidad insuficiente de saneamiento y tratamiento de aguas servidas "
        "(PTAR), y la degradación ambiental de la cuenca alta y las zonas de recarga.\n\n"
        "A su vez, estas causas se explican por POT desactualizados, débil articulación entre "
        "municipios, CAR y prestadores, pérdidas de agua en redes obsoletas, infraestructura con "
        "capacidad sobrepasada, deforestación en rondas hídricas y presupuestos municipales limitados.",
    ),
    (
        "El río Bogotá y la calidad del agua",
        "El deterioro de la calidad del agua en la cuenca del río Bogotá.",
        "El deterioro crítico de la calidad del agua en la cuenca del río Bogotá es uno de los dos "
        "efectos directos del problema central. El informe regional consultado (págs. 182 a 184) "
        "clasifica el Índice de Calidad del Agua (ICA) del río como \"malo/regular\".\n\n"
        "Entre sus consecuencias se identifican sobrecostos en las tarifas por la potabilización "
        "de agua contaminada y riesgos sanitarios por el aumento del IRCA.",
    ),
]


def _crear_nodo(tipo, titulo, fuente, orden, padre=None):
    nodo = NodoArbol(tipo=tipo, titulo=titulo, fuente=fuente, orden=orden, padre=padre)
    db.session.add(nodo)
    return nodo


def sembrar_municipios():
    creados = 0
    for nombre, lat, lon in MUNICIPIOS:
        if Municipio.query.filter_by(nombre=nombre).first():
            continue
        db.session.add(
            Municipio(
                nombre=nombre,
                slug=crear_slug(nombre),
                latitud=lat,
                longitud=lon,
                resumen="Los datos de este municipio están pendientes de carga por el administrador.",
            )
        )
        creados += 1
    return creados


def sembrar_arbol():
    if NodoArbol.query.first():
        return 0  # ya existe: no se duplica
    titulo, fuente = PROBLEMA_CENTRAL
    central = _crear_nodo("problema_central", titulo, fuente, 0)
    total = 1
    for i, (efecto, fuente_e, indirectos) in enumerate(EFECTOS, start=1):
        directo = _crear_nodo("efecto_directo", efecto, fuente_e, i, central)
        total += 1
        for j, (texto, fuente_i) in enumerate(indirectos, start=1):
            _crear_nodo("efecto_indirecto", texto, fuente_i, j, directo)
            total += 1
    for i, (causa, fuente_c, indirectas) in enumerate(CAUSAS, start=1):
        directa = _crear_nodo("causa_directa", causa, fuente_c, i, central)
        total += 1
        for j, (texto, fuente_i) in enumerate(indirectas, start=1):
            _crear_nodo("causa_indirecta", texto, fuente_i, j, directa)
            total += 1
    return total


def sembrar_guias():
    creadas = 0
    for orden, (titulo, nivel, contenido) in enumerate(GUIAS, start=1):
        if GuiaConsumo.query.filter_by(titulo=titulo).first():
            continue
        db.session.add(
            GuiaConsumo(titulo=titulo, nivel_riesgo=nivel, contenido=contenido, resumen=EJEMPLO, orden=orden)
        )
        creadas += 1
    return creadas


def sembrar_articulos():
    creados = 0
    for titulo, resumen, contenido in ARTICULOS:
        slug = crear_slug(titulo)
        if Articulo.query.filter_by(slug=slug).first():
            continue
        db.session.add(
            Articulo(
                titulo=titulo,
                slug=slug,
                resumen=f"{resumen} {EJEMPLO}"[:300],
                contenido=contenido,
                categoria="articulo",
                publicado=True,
            )
        )
        creados += 1
    return creados


def sembrar_todo():
    """Carga los datos iniciales. Se puede ejecutar varias veces sin duplicar."""
    resultado = {
        "municipios": sembrar_municipios(),
        "nodos del árbol": sembrar_arbol(),
        "guías": sembrar_guias(),
        "artículos": sembrar_articulos(),
    }
    db.session.commit()
    return resultado