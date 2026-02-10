"""
Modelo de Conversación — Cerebro Operativo

Almacena el historial de conversaciones con el asistente de IA
para mantener contexto entre sesiones.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer
from app.database import Base


class Conversation(Base):
    """Mensaje individual en una conversación con el asistente."""
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), nullable=False, index=True)  # Agrupa mensajes
    role = Column(String(20), nullable=False)  # "user", "assistant", "system"
    content = Column(Text, nullable=False)
    tokens_used = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
