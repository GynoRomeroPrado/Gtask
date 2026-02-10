"""
Conexión a la base de datos con SQLAlchemy 2.0 (modo síncrono).
Soporta SQLite (desarrollo) y PostgreSQL (producción).
Provee el engine, SessionLocal, y Base para los modelos.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import get_settings


settings = get_settings()

# Configuración según el tipo de base de datos
is_sqlite = settings.database_url.startswith("sqlite")

if is_sqlite:
    engine = create_engine(
        settings.database_url,
        echo=settings.app_env == "development",
        connect_args={"check_same_thread": False},  # Necesario para SQLite + FastAPI
    )
else:
    engine = create_engine(
        settings.database_url,
        echo=settings.app_env == "development",
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )

# Fábrica de sesiones
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    """Clase base para todos los modelos SQLAlchemy."""
    pass


def get_db():
    """
    Dependency de FastAPI que provee una sesión de DB.
    Se cierra automáticamente al terminar el request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
