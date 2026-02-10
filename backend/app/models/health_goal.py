"""
HealthGoal — Modelo de metas de bienestar

Tipos de metas:
- gym: Rutina de ejercicio
- water: Hidratación diaria
- sleep: Horas de sueño
- meditation: Meditación / mindfulness
- nutrition: Alimentación saludable
- breaks: Pausas activas durante trabajo
"""
import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Date, Text
from app.database import Base


class HealthGoal(Base):
    __tablename__ = "health_goals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)  # gym, water, sleep, meditation, nutrition, breaks
    description = Column(Text, nullable=True)

    # Configuración de la meta
    target_value = Column(Float, nullable=False)      # Ej: 8 (vasos), 7 (horas), 3 (sesiones/semana)
    target_unit = Column(String(30), nullable=False)   # vasos, horas, sesiones, minutos
    frequency = Column(String(20), default="daily")    # daily, weekly
    current_value = Column(Float, default=0)           # Progreso actual del período

    # Estado
    is_active = Column(Boolean, default=True)
    streak_days = Column(Integer, default=0)           # Racha actual
    best_streak = Column(Integer, default=0)           # Mejor racha
    total_completions = Column(Integer, default=0)     # Total de veces completada
    last_completed = Column(Date, nullable=True)

    # Alertas
    reminder_time = Column(String(5), nullable=True)   # HH:MM — hora de recordatorio
    color = Column(String(7), default="#10B981")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
