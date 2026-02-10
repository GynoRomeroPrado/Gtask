"""
Router de salud — Health check para verificar que el servidor y la DB están operativos.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Verifica el estado del servidor y la conexión a PostgreSQL.
    Retorna status 'ok' si todo funciona correctamente.
    """
    try:
        # Verificar conexión a la base de datos
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "database": db_status,
        "version": "0.1.0",
    }
