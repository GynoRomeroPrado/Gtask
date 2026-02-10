"""
Router de IA — Cerebro Operativo

Endpoint para interacción conversacional con el asistente de IA.
"""
import uuid
from pydantic import BaseModel, Field
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.ai.engine import (
    chat_with_ai,
    generate_summary,
    generate_suggestions,
    build_context,
)

router = APIRouter(prefix="/ai", tags=["Asistente IA"])


# === Schemas ===

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    intent: Optional[str] = None


# === Endpoints ===

@router.post("/chat", response_model=ChatResponse)
def ai_chat(req: ChatRequest, db: Session = Depends(get_db)):
    """
    Envía un mensaje al asistente de IA.
    El asistente puede:
    - Responder preguntas sobre tus tareas
    - Crear tareas desde lenguaje natural
    - Dar resúmenes y sugerencias
    - Recordar contexto de la conversación
    """
    session_id = req.session_id or str(uuid.uuid4())

    from app.ai.engine import parse_intent
    intent = parse_intent(req.message)

    response = chat_with_ai(req.message, session_id, db)

    return ChatResponse(
        response=response,
        session_id=session_id,
        intent=intent.get("intent"),
    )


@router.get("/summary")
def ai_summary(db: Session = Depends(get_db)):
    """Resumen rápido del estado actual."""
    return {"summary": generate_summary(db)}


@router.get("/suggestions")
def ai_suggestions(db: Session = Depends(get_db)):
    """Sugerencias inteligentes basadas en el contexto."""
    return {"suggestions": generate_suggestions(db)}


@router.get("/context")
def ai_context(db: Session = Depends(get_db)):
    """Retorna el contexto actual del sistema (debug)."""
    ctx = build_context(db)
    return {
        "today": ctx["today"],
        "pending_tasks": ctx["pending_tasks"],
        "today_tasks": ctx["today_tasks"],
        "overdue_tasks": ctx["overdue_tasks"],
        "financial_alerts": ctx["financial_alerts"],
    }
