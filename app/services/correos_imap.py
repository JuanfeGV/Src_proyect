import imaplib
import logging
import re
import ssl
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timedelta, timezone
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import current_app


try:
    _ZONA_BOGOTA = ZoneInfo("America/Bogota")
except ZoneInfoNotFoundError:
    # Bogotá permanece en UTC-5; esto cubre sistemas sin base IANA instalada.
    _ZONA_BOGOTA = timezone(timedelta(hours=-5))

_LOGGER = logging.getLogger(__name__)
_MAX_MENSAJES = 30
_MAX_BYTES_CONTENIDO = 16 * 1024
_MAX_PARTES_TEXTO = 4
_MAX_BODYSTRUCTURE_BYTES = 64 * 1024
_MAX_ENCABEZADOS_BYTES = 8 * 1024
_TIMEOUT_SEGUNDOS = 10
_TOKEN_BODYSTRUCTURE = re.compile(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+')
_UID_RE = re.compile(rb"\bUID\s+(\d+)\b", re.IGNORECASE)
_FLAGS_RE = re.compile(rb"\bFLAGS\s+\(([^)]*)\)", re.IGNORECASE)
_INTERNALDATE_RE = re.compile(rb'\bINTERNALDATE\s+"([^"]+)"', re.IGNORECASE)


class ErrorCorreoIMAP(RuntimeError):
    """Error IMAP con un mensaje seguro para mostrar al administrador."""


class ConfiguracionIMAPIncompleta(ErrorCorreoIMAP):
    pass


class MensajeNoEncontrado(ErrorCorreoIMAP):
    pass


@dataclass(frozen=True)
class MensajeCorreo:
    uid: int
    remitente: str
    asunto: str
    fecha: str
    leido: bool


@dataclass(frozen=True)
class MensajeCorreoDetalle(MensajeCorreo):
    contenido: str
    truncado: bool


@contextmanager
def _buzon():
    configuracion = current_app.config
    servidor = configuracion.get("IMAP_SERVER")
    puerto = configuracion.get("IMAP_PORT")
    usuario = configuracion.get("IMAP_USERNAME")
    clave = configuracion.get("IMAP_PASSWORD")

    if not servidor or not puerto or not usuario or not clave:
        raise ConfiguracionIMAPIncompleta("La configuración IMAP está incompleta.")
    if not 1 <= int(puerto) <= 65535:
        raise ConfiguracionIMAPIncompleta("El puerto IMAP no es válido.")

    cliente = None
    try:
        cliente = imaplib.IMAP4_SSL(
            servidor,
            int(puerto),
            ssl_context=ssl.create_default_context(),
            timeout=_TIMEOUT_SEGUNDOS,
        )
        estado, _ = cliente.login(usuario, clave)
        if estado != "OK":
            raise ErrorCorreoIMAP("No fue posible iniciar sesión en el buzón.")
        estado, _ = cliente.select("INBOX", readonly=True)
        if estado != "OK":
            raise ErrorCorreoIMAP("No fue posible abrir la bandeja de entrada.")
        yield cliente
    except (imaplib.IMAP4.error, OSError):
        raise ErrorCorreoIMAP("No fue posible consultar la bandeja IMAP.") from None
    finally:
        if cliente is not None:
            try:
                cliente.logout()
            except (imaplib.IMAP4.error, OSError):
                _LOGGER.warning("No se pudo cerrar correctamente la conexión IMAP.")


def listar_mensajes(limite=_MAX_MENSAJES):
    """Devuelve como máximo los mensajes más recientes, sin cambiar su estado."""
    limite = max(1, min(int(limite), _MAX_MENSAJES))
    with _buzon() as cliente:
        estado, datos = cliente.uid("search", None, "ALL")
        if estado != "OK":
            raise ErrorCorreoIMAP("No fue posible buscar mensajes en la bandeja.")

        uids = []
        for bloque in datos or ():
            if isinstance(bloque, bytes):
                uids.extend(int(valor) for valor in bloque.split() if valor.isdigit())

        uids_recientes = uids[-limite:]
        if not uids_recientes:
            return []

        identificadores = ",".join(str(uid) for uid in uids_recientes)
        estado, datos = cliente.uid(
            "fetch",
            identificadores,
            f"(UID FLAGS INTERNALDATE BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)]<0.{_MAX_ENCABEZADOS_BYTES}>)",
        )
        if estado != "OK":
            raise ErrorCorreoIMAP("No fue posible leer los encabezados de los mensajes.")

        mensajes_por_uid = {}
        for metadatos, encabezados in _registros_fetch(datos):
            uid = _extraer_uid(metadatos)
            if uid is not None:
                mensajes_por_uid[uid] = _crear_mensaje(uid, metadatos, encabezados)

        return [
            mensajes_por_uid[uid]
            for uid in reversed(uids_recientes)
            if uid in mensajes_por_uid
        ]


def obtener_mensaje(uid):
    """Lee un mensaje por UID sin obtener archivos adjuntos ni marcarlo como leído."""
    if not isinstance(uid, int) or uid < 1:
        raise MensajeNoEncontrado("El mensaje solicitado no existe.")

    with _buzon() as cliente:
        estado, datos = cliente.uid(
            "fetch",
            str(uid),
            f"(UID FLAGS INTERNALDATE BODYSTRUCTURE BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)]<0.{_MAX_ENCABEZADOS_BYTES}>)",
        )
        if estado != "OK":
            raise ErrorCorreoIMAP("No fue posible leer el mensaje.")

        registros = _registros_fetch(datos)
        registro = next(
            (elemento for elemento in registros if _extraer_uid(elemento[0]) == uid),
            None,
        )
        if registro is None:
            raise MensajeNoEncontrado("El mensaje solicitado no existe.")

        metadatos, encabezados = registro
        mensaje = _crear_mensaje(uid, metadatos, encabezados)
        estructura = _extraer_bodystructure(metadatos)
        partes = _partes_texto_plano(estructura)
        contenido, truncado = _leer_contenido(cliente, uid, partes)
        if not contenido:
            contenido = "Este mensaje no contiene texto plano compatible para mostrar."

        return MensajeCorreoDetalle(
            uid=mensaje.uid,
            remitente=mensaje.remitente,
            asunto=mensaje.asunto,
            fecha=mensaje.fecha,
            leido=mensaje.leido,
            contenido=contenido,
            truncado=truncado,
        )


def _registros_fetch(datos):
    return [
        (elemento[0], elemento[1])
        for elemento in datos or ()
        if isinstance(elemento, tuple)
        and len(elemento) >= 2
        and isinstance(elemento[0], bytes)
        and isinstance(elemento[1], bytes)
    ]


def _extraer_uid(metadatos):
    coincidencia = _UID_RE.search(metadatos)
    return int(coincidencia.group(1)) if coincidencia else None


def _crear_mensaje(uid, metadatos, encabezados):
    parsed = BytesParser(policy=policy.default).parsebytes(encabezados)
    remitente = str(parsed.get("From") or "Remitente desconocido")[:500]
    asunto = str(parsed.get("Subject") or "(Sin asunto)")[:500]
    coincidencia = _INTERNALDATE_RE.search(metadatos)
    fecha_original = (
        coincidencia.group(1).decode("ascii", errors="replace")
        if coincidencia
        else str(parsed.get("Date") or "")
    )
    try:
        fecha_parseada = parsedate_to_datetime(fecha_original)
        if fecha_parseada is None:
            raise ValueError("Fecha vacía")
        if fecha_parseada.tzinfo is None:
            fecha_parseada = fecha_parseada.replace(tzinfo=timezone.utc)
        fecha = fecha_parseada.astimezone(_ZONA_BOGOTA).strftime("%d/%m/%Y %H:%M")
    except (TypeError, ValueError, OverflowError, AttributeError):
        fecha = "Fecha desconocida"

    coincidencia = _FLAGS_RE.search(metadatos)
    leido = bool(coincidencia and re.search(rb"\\Seen\b", coincidencia.group(1), re.IGNORECASE))
    return MensajeCorreo(uid, remitente, asunto, fecha, leido)


def _extraer_bodystructure(metadatos):
    if len(metadatos) > _MAX_BODYSTRUCTURE_BYTES:
        raise ErrorCorreoIMAP("No fue posible interpretar el contenido del mensaje.")
    coincidencia = re.search(rb"\bBODYSTRUCTURE\s+", metadatos, re.IGNORECASE)
    if not coincidencia:
        raise ErrorCorreoIMAP("No fue posible interpretar el contenido del mensaje.")

    inicio = coincidencia.end()
    profundidad = 0
    en_comillas = False
    escapado = False
    fin = None
    for indice in range(inicio, len(metadatos)):
        caracter = metadatos[indice]
        if en_comillas:
            if escapado:
                escapado = False
            elif caracter == ord("\\"):
                escapado = True
            elif caracter == ord('"'):
                en_comillas = False
            continue
        if caracter == ord('"'):
            en_comillas = True
        elif caracter == ord("("):
            profundidad += 1
        elif caracter == ord(")"):
            profundidad -= 1
            if profundidad == 0:
                fin = indice + 1
                break

    if fin is None:
        raise ErrorCorreoIMAP("No fue posible interpretar el contenido del mensaje.")

    texto = metadatos[inicio:fin].decode("ascii", errors="replace")
    tokens = []
    for token in _TOKEN_BODYSTRUCTURE.findall(texto):
        if token.startswith('"'):
            tokens.append(re.sub(r"\\(.)", r"\1", token[1:-1]))
        elif token.upper() == "NIL":
            tokens.append(None)
        else:
            tokens.append(token)

    estructura, siguiente = _parsear_lista(tokens, 0)
    if siguiente != len(tokens) or not isinstance(estructura, list):
        raise ErrorCorreoIMAP("No fue posible interpretar el contenido del mensaje.")
    return estructura


def _parsear_lista(tokens, indice, profundidad=0):
    if profundidad > 30:
        raise ErrorCorreoIMAP("No fue posible interpretar el contenido del mensaje.")
    if indice >= len(tokens) or tokens[indice] != "(":
        raise ErrorCorreoIMAP("No fue posible interpretar el contenido del mensaje.")

    elementos = []
    indice += 1
    while indice < len(tokens) and tokens[indice] != ")":
        if tokens[indice] == "(":
            elemento, indice = _parsear_lista(tokens, indice, profundidad + 1)
            elementos.append(elemento)
        else:
            elementos.append(tokens[indice])
            indice += 1
    if indice >= len(tokens):
        raise ErrorCorreoIMAP("No fue posible interpretar el contenido del mensaje.")
    return elementos, indice + 1


def _partes_texto_plano(estructura, prefijo=""):
    if not isinstance(estructura, list) or not estructura:
        return []

    hijos = []
    if isinstance(estructura[0], list):
        for elemento in estructura:
            if not isinstance(elemento, list):
                break
            hijos.append(elemento)
    if hijos:
        partes = []
        for indice, hijo in enumerate(hijos, start=1):
            seccion = f"{prefijo}.{indice}" if prefijo else str(indice)
            partes.extend(_partes_texto_plano(hijo, seccion))
        return partes

    if len(estructura) < 7 or str(estructura[0]).upper() != "TEXT":
        return []
    if str(estructura[1]).upper() != "PLAIN":
        return []

    parametros = _parametros(estructura[2])
    extension_inicio = 8
    disposicion = estructura[extension_inicio + 1] if len(estructura) > extension_inicio + 1 else None
    parametros_disposicion = disposicion[1] if isinstance(disposicion, list) and len(disposicion) > 1 else None
    disposicion_nombre = disposicion[0] if isinstance(disposicion, list) and disposicion else ""
    if str(disposicion_nombre).upper() == "ATTACHMENT":
        return []
    if any(nombre.lower() == "filename" for nombre, _ in _parametros(parametros_disposicion)):
        return []
    if any(nombre.lower() == "name" for nombre, _ in _parametros(estructura[2])):
        return []

    seccion = prefijo or "TEXT"
    tamano = estructura[6]
    encoding = str(estructura[5] or "7BIT")
    if not re.fullmatch(r"[A-Za-z0-9-]{1,40}", encoding):
        encoding = "7BIT"
    return [
        {
            "seccion": seccion,
            "parametros": parametros,
            "encoding": encoding,
            "tamano": int(tamano) if str(tamano).isdigit() else None,
        }
    ]


def _parametros(valor):
    if not isinstance(valor, list):
        return []
    return [
        (str(valor[indice]), valor[indice + 1])
        for indice in range(0, len(valor) - 1, 2)
        if valor[indice] is not None
    ]


def _leer_contenido(cliente, uid, partes):
    fragmentos = []
    bytes_restantes = _MAX_BYTES_CONTENIDO
    truncado = False

    for parte in partes[:_MAX_PARTES_TEXTO]:
        if bytes_restantes <= 0:
            truncado = True
            break
        limite = min(bytes_restantes, _MAX_BYTES_CONTENIDO)
        estado, datos = cliente.uid(
            "fetch",
            str(uid),
            f"(BODY.PEEK[{parte['seccion']}]<0.{limite}>)",
        )
        if estado != "OK":
            raise ErrorCorreoIMAP("No fue posible leer el texto del mensaje.")

        registro = next(iter(_registros_fetch(datos)), None)
        if registro is None:
            continue
        contenido_crudo = registro[1]
        bytes_restantes -= len(contenido_crudo)
        if parte["tamano"] is not None and parte["tamano"] > len(contenido_crudo):
            truncado = True
        fragmentos.append(_decodificar_parte(parte, contenido_crudo))

    contenido = "\n\n".join(fragmento for fragmento in fragmentos if fragmento).strip()
    if len(contenido) > 12000:
        contenido = contenido[:12000]
        truncado = True
    return contenido, truncado


def _decodificar_parte(parte, contenido_crudo):
    mime = EmailMessage(policy=policy.default)
    mime.set_type("text/plain")
    for nombre, valor in parte["parametros"]:
        if (
            nombre.lower() == "charset"
            and valor
            and re.fullmatch(r"[A-Za-z0-9._-]{1,40}", str(valor))
        ):
            mime.set_param("charset", str(valor))
    mime["Content-Transfer-Encoding"] = parte["encoding"]

    mensaje = BytesParser(policy=policy.default).parsebytes(
        mime.as_bytes() + b"\r\n" + contenido_crudo
    )
    decodificado = mensaje.get_payload(decode=True) or b""
    charset = mensaje.get_content_charset() or "utf-8"
    try:
        texto = decodificado.decode(charset, errors="replace")
    except LookupError:
        texto = decodificado.decode("utf-8", errors="replace")
    return texto.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
