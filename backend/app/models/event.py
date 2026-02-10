"""
Modelo de Eventos — Cerebro Operativo

Eventos del calendario interno. Soporta:
- Eventos con fecha/hora inicio y fin
- Tipos: reminder, financial_alert, meeting, gym, custom
- Relación opcional con tareas
- Campos para futura integración con Google Calendar
"""
import uuid
from datetime import datetime, date, time
from sqlalchemy import (
    Column, String, Text, DateTime, Date, Time,
    Boolean, Integer, ForeignKey, Enum
)
from sqlalchemy.orm import relationship
from app.database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Tipo de evento
    event_type = Column(
        String(30), nullable=False, default="custom"
    )  # reminder, financial_alert, meeting, gym, health, custom

    # Fecha y hora
    event_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    all_day = Column(Boolean, default=False)

    # Alertas
    alert_minutes_before = Column(Integer, nullable=True)  # Minutos antes para alertar
    alert_sent = Column(Boolean, default=False)

    # Color y visual
    color = Column(String(7), default="#8B5CF6")
    icon = Column(String(10), default="📅")

    # Relación con tarea (opcional)
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)

    # Google Calendar sync
    google_event_id = Column(String(255), nullable=True)
    google_calendar_id = Column(String(255), nullable=True)

    # Recurrencia
    is_recurring = Column(Boolean, default=False)
    recurrence_rule = Column(String(255), nullable=True)  # RRULE format

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FinancialAlert(Base):
    """
    Alertas financieras recurrentes.
    Ej: BBVA vence día 2, Scotiabank día 20 — alerta 3 días antes.
    """
    __tablename__ = "financial_alerts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)  # "Pago BBVA", "Pago Scotiabank"
    description = Column(Text, nullable=True)

    # Configuración de vencimiento
    due_day_of_month = Column(Integer, nullable=False)  # Día del mes (1-31)
    alert_days_before = Column(Integer, default=3)       # Días de anticipación

    # Monto y categoría
    amount = Column(String(50), nullable=True)  # Encrypted en producción
    currency = Column(String(3), default="PEN")
    category = Column(String(50), default="tarjeta_credito")  # tarjeta_credito, servicio, préstamo

    # Color y visual
    color = Column(String(7), default="#F59E0B")
    icon = Column(String(10), default="💳")

    # Estado
    is_active = Column(Boolean, default=True)
    last_alert_date = Column(Date, nullable=True)
    last_paid_date = Column(Date, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
