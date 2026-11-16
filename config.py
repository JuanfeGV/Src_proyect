import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _url_base_de_datos():
    """Lee DATABASE_URL; si no existe, usa SQLite en la carpeta instance/."""
    url = os.environ.get("DATABASE_URL", "sqlite:///portal.db")
    # Algunos hostings entregan "postgres://", que SQLAlchemy ya no acepta.
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    NOMBRE_SITIO = "Sabana Centro AguaComunidad"
    SECRET_KEY = os.environ.get("SECRET_KEY", "clave-solo-para-desarrollo")
    SQLALCHEMY_DATABASE_URI = _url_base_de_datos()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SMTP_SERVER = os.environ.get("SMTP_SERVER")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "1") == "1"
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
    SMTP_SENDER = os.environ.get("SMTP_SENDER")
    EMAIL_REPORTS_TO = os.environ.get("EMAIL_REPORTS_TO", "aguacomunidadsabana@gmail.com")
    IMAP_USERNAME = os.environ.get("IMAP_USERNAME")
    IMAP_PASSWORD = os.environ.get("IMAP_PASSWORD")
    IMAP_SERVER = os.environ.get("IMAP_SERVER", "imap.gmail.com")
    IMAP_PORT = int(os.environ.get("IMAP_PORT", "993"))
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB máximo por subida (las imágenes se reducen al guardarlas)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE") == "1"
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    # La cookie de "mantener sesión iniciada" sigue las mismas reglas.
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_por_entorno = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}