"""
Google OAuth 2.0 — Cerebro Operativo

Gestiona la autenticación con Google APIs (Calendar, Gmail, Sheets).
Flujo:
1. GET /api/integrations/google/auth-url → URL de autorización
2. Usuario autoriza en Google → redirect con ?code=xxx
3. GET /api/integrations/google/callback?code=xxx → guarda tokens
4. Tokens se renuevan automáticamente
"""
import os
import json
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

# Google OAuth
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

# Ruta para almacenar tokens
TOKEN_DIR = Path(__file__).parent.parent.parent / "credentials"
TOKEN_FILE = TOKEN_DIR / "google_token.json"
CLIENT_SECRETS_FILE = TOKEN_DIR / "client_secrets.json"

# Scopes necesarios
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]

REDIRECT_URI = "http://localhost:8000/api/integrations/google/callback"


def is_configured() -> bool:
    """Verifica si las credenciales de Google están configuradas."""
    return GOOGLE_AVAILABLE and CLIENT_SECRETS_FILE.exists()


def get_auth_url() -> Optional[str]:
    """Genera la URL de autorización de Google."""
    if not is_configured():
        return None

    flow = Flow.from_client_secrets_file(
        str(CLIENT_SECRETS_FILE),
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url


def exchange_code(code: str) -> bool:
    """Intercambia el código de autorización por tokens."""
    if not is_configured():
        return False

    try:
        flow = Flow.from_client_secrets_file(
            str(CLIENT_SECRETS_FILE),
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
        )
        flow.fetch_token(code=code)
        creds = flow.credentials

        TOKEN_DIR.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

        return True
    except Exception as e:
        print(f"❌ Error en OAuth: {e}")
        return False


def get_credentials() -> Optional[Credentials]:
    """Obtiene credenciales válidas, renovando si es necesario."""
    if not TOKEN_FILE.exists():
        return None

    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        except Exception:
            return None

    return creds if creds and creds.valid else None


def get_calendar_service():
    """Obtiene el servicio de Google Calendar."""
    creds = get_credentials()
    if not creds:
        return None
    return build("calendar", "v3", credentials=creds)


def get_gmail_service():
    """Obtiene el servicio de Gmail."""
    creds = get_credentials()
    if not creds:
        return None
    return build("gmail", "v1", credentials=creds)


def get_sheets_service():
    """Obtiene el servicio de Google Sheets."""
    creds = get_credentials()
    if not creds:
        return None
    return build("sheets", "v4", credentials=creds)


# =============================================================================
# GOOGLE CALENDAR — Operaciones
# =============================================================================

def sync_events_from_calendar(days_ahead: int = 30) -> list:
    """Obtiene eventos de Google Calendar."""
    service = get_calendar_service()
    if not service:
        return []

    now = datetime.utcnow().isoformat() + "Z"
    future = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + "Z"

    try:
        events_result = service.events().list(
            calendarId="primary",
            timeMin=now,
            timeMax=future,
            maxResults=100,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        return events_result.get("items", [])
    except Exception as e:
        print(f"❌ Error al sincronizar calendario: {e}")
        return []


def create_calendar_event(summary: str, start: str, end: str,
                          description: str = None) -> Optional[dict]:
    """Crea un evento en Google Calendar."""
    service = get_calendar_service()
    if not service:
        return None

    event = {
        "summary": summary,
        "start": {"dateTime": start, "timeZone": "America/Lima"},
        "end": {"dateTime": end, "timeZone": "America/Lima"},
    }
    if description:
        event["description"] = description

    try:
        return service.events().insert(
            calendarId="primary", body=event
        ).execute()
    except Exception as e:
        print(f"❌ Error al crear evento: {e}")
        return None
