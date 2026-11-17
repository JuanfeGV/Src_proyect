"""Consultas que usan las páginas públicas (solo lectura).

Las páginas públicas nunca muestran borradores: los artículos deben estar
publicados y las guías deben estar marcadas como publicadas.
"""
import math
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

from flask import url_for

from ..models import Articulo, GuiaConsumo, Municipio, NodoArbol
from ..models.constantes import NIVELES_RIESGO
from ..utils.texto import normalizar
from .semilla import MUNICIPIOS

LARGO_MAXIMO_BUSQUEDA = 100
LARGO_MINIMO_BUSQUEDA = 2
MAXIMO_PALABRAS = 6

PERIODO_COBERTURA = "2024"
INDICADORES_COBERTURA = {
    "urbana": "Cobertura acueducto urbana (serie tratada)",
    "rural": "Cobertura acueducto rural (serie tratada)",
}
FUENTE_COBERTURA_URL = (
    "https://www.superservicios.gov.co/sites/default/files/2025-12/"
    "Anexo-1-Base-de-informacion-2024.xlsx"
)
ETIQUETAS_PRIORIDAD_COBERTURA = {
    "alta": "Alta",
    "media": "Media",
    "baja": "Baja",
}
NOMBRE_INDICADOR_RECURRENCIA = (
    "Recurrencia histórica desabastecimiento en temporada de lluvia "
    "(IDEAM ENA 2022)"
)
PERIODO_RECURRENCIA = "ENA 2022"
ETIQUETAS_RECURRENCIA = {
    "baja": "Baja",
    "media": "Media",
    "alta": "Alta",
}


def _porcentaje_valido(valor):
    if valor is None:
        return None
    try:
        porcentaje = Decimal(str(valor).strip().replace(",", "."))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not porcentaje.is_finite() or not Decimal("0") <= porcentaje <= Decimal("100"):
        return None
    return porcentaje


def _formatear_decimal(valor):
    if valor == 0:
        return "0"
    return format(valor.normalize(), "f").replace(".", ",")


def _formatear_porcentaje(valor):
    return format(valor, ".2f").replace(".", ",") if valor is not None else None


def _url_oficial_de_dominio(indicadores, dominio):
    for indicador in indicadores:
        fuente = (indicador.fuente or "").strip()
        try:
            parsed = urlparse(fuente)
        except ValueError:
            continue
        host = (parsed.hostname or "").lower()
        if (
            parsed.scheme == "https"
            and parsed.username is None
            and parsed.password is None
            and (host == dominio or host.endswith("." + dominio))
        ):
            return fuente
    return None


def _url_oficial_cobertura(indicadores):
    fuente = _url_oficial_de_dominio(indicadores, "superservicios.gov.co")
    if fuente:
        return fuente
    return FUENTE_COBERTURA_URL


def evaluar_cobertura_municipal(municipio):
    """Calcula la prioridad académica a partir de los indicadores registrados."""
    indicadores = [
        indicador
        for indicador in municipio.indicadores
        if indicador.periodo == PERIODO_COBERTURA
    ]

    def obtener_indicador(tipo):
        coincidencias = [
            indicador
            for indicador in indicadores
            if indicador.nombre == INDICADORES_COBERTURA[tipo]
        ]
        if len(coincidencias) != 1:
            return None, None
        indicador = coincidencias[0]
        return _porcentaje_valido(indicador.valor), indicador

    urbana, indicador_urbano = obtener_indicador("urbana")
    rural, indicador_rural = obtener_indicador("rural")
    diferencia = urbana - rural if urbana is not None and rural is not None else None

    if rural is None:
        prioridad = None
        interpretacion = (
            "No hay un valor único y válido de cobertura rural para 2024; "
            "no se asigna una prioridad de atención."
        )
    elif rural < Decimal("80"):
        prioridad = "alta"
        interpretacion = (
            "La cobertura rural corresponde a prioridad alta según los umbrales "
            "académicos propuestos."
        )
    elif rural < Decimal("95"):
        prioridad = "media"
        interpretacion = (
            "La cobertura rural corresponde a prioridad media según los umbrales "
            "académicos propuestos."
        )
    else:
        prioridad = "baja"
        interpretacion = (
            "La cobertura rural corresponde a prioridad baja según los umbrales "
            "académicos propuestos."
        )

    if diferencia is not None:
        interpretacion += (
            " La diferencia urbana-rural es de "
            f"{_formatear_decimal(diferencia)} puntos porcentuales."
        )

    fuentes = [indicador_rural, indicador_urbano]
    fuentes = [indicador for indicador in fuentes if indicador is not None]
    return {
        "urbana": float(urbana) if urbana is not None else None,
        "urbana_texto": _formatear_decimal(urbana) if urbana is not None else None,
        "urbana_porcentaje_texto": _formatear_porcentaje(urbana),
        "rural": float(rural) if rural is not None else None,
        "rural_texto": _formatear_decimal(rural) if rural is not None else None,
        "rural_porcentaje_texto": _formatear_porcentaje(rural),
        "diferencia": float(diferencia) if diferencia is not None else None,
        "diferencia_texto": (
            _formatear_decimal(diferencia) if diferencia is not None else None
        ),
        "prioridad": prioridad,
        "prioridad_texto": ETIQUETAS_PRIORIDAD_COBERTURA.get(
            prioridad, "Sin evaluar"
        ),
        "interpretacion": interpretacion,
        "periodo": PERIODO_COBERTURA,
        "fuente_url": _url_oficial_cobertura(fuentes),
    }


def evaluar_recurrencia_municipal(municipio):
    """Devuelve solo la clasificación documental registrada para IDEAM ENA 2022."""
    coincidencias = [
        indicador
        for indicador in municipio.indicadores
        if (
            indicador.nombre == NOMBRE_INDICADOR_RECURRENCIA
            and indicador.periodo == PERIODO_RECURRENCIA
        )
    ]
    indicador = coincidencias[0] if len(coincidencias) == 1 else None
    recurrencia = (
        (indicador.valor or "").strip().lower()
        if indicador is not None
        else None
    )
    if recurrencia not in ETIQUETAS_RECURRENCIA:
        recurrencia = None

    return {
        "nivel": recurrencia,
        "texto": ETIQUETAS_RECURRENCIA.get(
            recurrencia, "Sin clasificación documentada"
        ),
        "periodo": PERIODO_RECURRENCIA,
        "fuente_url": (
            _url_oficial_de_dominio([indicador], "ideam.gov.co")
            if indicador is not None
            else None
        ),
    }


def palabras_busqueda(texto):
    """Divide lo que escribió la persona en palabras normalizadas (sin tildes ni mayúsculas)."""
    normalizado = normalizar((texto or "")[:LARGO_MAXIMO_BUSQUEDA])
    return normalizado.split(" ")[:MAXIMO_PALABRAS] if normalizado else []


def filtrar_por_texto(consulta, modelo, texto):
    """Deja solo los registros que contienen TODAS las palabras buscadas.
    autoescape=True evita que '%' o '_' escritos por la persona actúen como comodines."""
    for palabra in palabras_busqueda(texto):
        consulta = consulta.filter(modelo.texto_busqueda.contains(palabra, autoescape=True))
    return consulta


def articulos_publicados():
    return Articulo.query.filter(Articulo.publicado.is_(True)).order_by(
        Articulo.fecha_publicacion.desc(), Articulo.id.desc()
    )


def guias_publicadas(nivel=None, solo_generales=False):
    """Guías visibles al público.

    - nivel 'bajo', 'medio' o 'alto': las de ese nivel y las que aplican a todos.
    - solo_generales=True: únicamente las que aplican a todos los niveles
      (se usa con municipios todavía sin nivel de riesgo evaluado).
    - sin filtros: todas.
    """
    consulta = GuiaConsumo.query.filter(GuiaConsumo.publicada.is_(True))
    if solo_generales:
        consulta = consulta.filter(GuiaConsumo.nivel_riesgo == "todos")
    elif nivel in NIVELES_RIESGO:
        consulta = consulta.filter(GuiaConsumo.nivel_riesgo.in_([nivel, "todos"]))
    return consulta.order_by(GuiaConsumo.orden, GuiaConsumo.id)


def municipios_ordenados():
    return Municipio.query.order_by(Municipio.nombre)


def estructura_arbol():
    """Prepara los nodos y relaciones guardados para el diagrama público."""
    nodos = NodoArbol.query.order_by(NodoArbol.orden, NodoArbol.id).all()
    nodos_por_id = {nodo.id: nodo for nodo in nodos}
    tipos_por_capa = (
        ("efecto_indirecto", "Efectos indirectos"),
        ("efecto_directo", "Efectos directos"),
        ("problema_central", "Problema central"),
        ("causa_directa", "Causas directas"),
        ("causa_indirecta", "Causas indirectas"),
    )
    capas = [
        {
            "id": tipo.replace("_", "-"),
            "tipo": tipo,
            "titulo": titulo,
            "nodos": [nodo for nodo in nodos if nodo.tipo == tipo],
        }
        for tipo, titulo in tipos_por_capa
    ]
    sin_clasificar = [nodo for nodo in nodos if nodo.tipo not in dict(tipos_por_capa)]
    if sin_clasificar:
        capas.append(
            {
                "id": "sin-clasificar",
                "tipo": None,
                "titulo": "Nodos sin clasificar",
                "nodos": sin_clasificar,
            }
        )

    tipo_padre_esperado = {
        "efecto_directo": "problema_central",
        "efecto_indirecto": "efecto_directo",
        "causa_directa": "problema_central",
        "causa_indirecta": "causa_directa",
    }
    enlaces = []
    advertencias = []
    centrales = [nodo for nodo in nodos if nodo.tipo == "problema_central"]
    if not centrales:
        advertencias.append("No se encontró un problema central en los nodos cargados.")
    elif len(centrales) > 1:
        advertencias.append(
            f"Hay {len(centrales)} problemas centrales; se muestran sin descartar registros."
        )
    if sin_clasificar:
        advertencias.append(
            f"Hay {len(sin_clasificar)} nodo(s) con tipo no reconocido; "
            "se muestran sin asignarles una categoría."
        )

    for nodo in nodos:
        padre = nodos_por_id.get(nodo.padre_id)
        if nodo.padre_id is not None and padre is not None:
            enlaces.append(
                {"padre_id": padre.id, "hijo_id": nodo.id, "tipo": nodo.tipo}
            )

        tipo_padre = tipo_padre_esperado.get(nodo.tipo)
        if tipo_padre:
            if nodo.padre_id is None:
                advertencias.append(
                    f"El nodo «{nodo.titulo}» no tiene una relación padre."
                )
            elif padre is None:
                advertencias.append(
                    f"El nodo «{nodo.titulo}» apunta a un padre que no existe."
                )
            elif padre.tipo != tipo_padre:
                advertencias.append(
                    f"El padre registrado para «{nodo.titulo}» no corresponde "
                    "al nivel esperado; se conserva la relación existente."
                )
        elif nodo.tipo == "problema_central" and nodo.padre_id is not None:
            advertencias.append(
                f"El problema central «{nodo.titulo}» tiene un padre registrado."
            )

    return {
        "nodos": nodos,
        "capas": capas,
        "enlaces": enlaces,
        "advertencias": advertencias,
    }


def _coordenadas_validas(latitud, longitud):
    try:
        latitud = float(latitud)
        longitud = float(longitud)
    except (TypeError, ValueError, OverflowError):
        return None

    if not (
        math.isfinite(latitud)
        and math.isfinite(longitud)
        and -90 <= latitud <= 90
        and -180 <= longitud <= 180
    ):
        return None
    return latitud, longitud


_COORDENADAS_SEMILLA = {
    nombre: (latitud, longitud) for nombre, latitud, longitud in MUNICIPIOS
}


def datos_mapa(
    municipios,
    municipio_seleccionado=None,
    incluir_indicadores=False,
):
    """Prepara ubicaciones válidas y usa coordenadas semilla solo si faltan en la BD."""
    puntos = []
    for municipio in municipios:
        if municipio.latitud is None or municipio.longitud is None:
            coordenadas = _COORDENADAS_SEMILLA.get(municipio.nombre)
        else:
            coordenadas = _coordenadas_validas(municipio.latitud, municipio.longitud)

        if coordenadas is None:
            continue

        latitud, longitud = coordenadas
        punto = {
            "nombre": municipio.nombre,
            "slug": municipio.slug,
            "lat": latitud,
            "lng": longitud,
            "nivel": municipio.nivel_riesgo if municipio.nivel_riesgo in NIVELES_RIESGO else None,
            "suministro": municipio.estado_suministro,
            "resumen": municipio.resumen,
            "seleccionado": (
                municipio_seleccionado is not None
                and municipio.id == municipio_seleccionado.id
            ),
            "url": url_for("municipios.ficha", slug=municipio.slug),
        }
        if incluir_indicadores:
            cobertura = evaluar_cobertura_municipal(municipio)
            punto["cobertura"] = {
                "prioridad": cobertura["prioridad"],
                "prioridad_texto": cobertura["prioridad_texto"],
                "rural_texto": cobertura["rural_texto"],
                "rural_porcentaje_texto": cobertura["rural_porcentaje_texto"],
                "periodo": cobertura["periodo"],
                "fuente_url": cobertura["fuente_url"],
            }
            punto["recurrencia"] = evaluar_recurrencia_municipal(municipio)
        puntos.append(punto)
    return puntos