"""
Router de Integraciones — Cerebro Operativo

Endpoints para:
- Google OAuth flow
- Google Calendar sync
- Monitoreo de repositorios Git
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.database import get_db
from app.integrations import google_auth, git_monitor

router = APIRouter(prefix="/integrations", tags=["Integraciones"])


# === Google OAuth ===

@router.get("/google/status")
def google_status():
    """Verifica el estado de la integración con Google."""
    configured = google_auth.is_configured()
    authenticated = google_auth.get_credentials() is not None if configured else False
    return {
        "configured": configured,
        "authenticated": authenticated,
        "message": (
            "✅ Conectado a Google" if authenticated
            else "⚙️ Coloca client_secrets.json en backend/credentials/" if not configured
            else "🔑 Requiere autorización — visita /api/integrations/google/auth-url"
        ),
    }


@router.get("/google/auth-url")
def google_auth_url():
    """Genera la URL de autorización de Google OAuth."""
    url = google_auth.get_auth_url()
    if not url:
        raise HTTPException(
            status_code=400,
            detail="Google API no configurado. Coloca client_secrets.json en backend/credentials/",
        )
    return {"auth_url": url}


@router.get("/google/callback")
def google_callback(code: str = Query(...)):
    """Callback de Google OAuth — intercambia código por tokens."""
    success = google_auth.exchange_code(code)
    if success:
        return RedirectResponse(url="/?google_auth=success")
    raise HTTPException(status_code=400, detail="Error al intercambiar código OAuth")


@router.get("/google/calendar/events")
def google_calendar_events(days: int = Query(30, ge=1, le=90)):
    """Obtiene eventos de Google Calendar."""
    events = google_auth.sync_events_from_calendar(days_ahead=days)
    return {"count": len(events), "events": events}


# === Git Monitor ===

class RepoScanRequest(BaseModel):
    path: str


@router.post("/git/scan")
def scan_git_repo(req: RepoScanRequest):
    """Escanea un repositorio Git local."""
    result = git_monitor.scan_repo(req.path)
    if not result:
        raise HTTPException(status_code=400, detail="No se pudo escanear el repositorio")
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/git/activity")
def git_activity(req: RepoScanRequest, days: int = Query(30, ge=1, le=365)):
    """Obtiene el mapa de actividad de commits."""
    result = git_monitor.get_commit_activity(req.path, days=days)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/git/scan-current")
def scan_current_repo():
    """Escanea el repositorio actual del proyecto (Cerebro Operativo)."""
    import os
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent.parent  # backend/../..
    result = git_monitor.scan_repo(str(project_root))
    return result if result else {"error": "No se encontró repositorio"}
