"""
Schemas Pydantic — Eventos y Alertas Financieras
"""
from datetime import date, time, datetime
from typing import Optional
from pydantic import BaseModel, Field


# === Eventos ===

class EventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    event_type: str = Field(default="custom")  # reminder, financial_alert, meeting, gym, custom
    event_date: date
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    all_day: bool = False
    alert_minutes_before: Optional[int] = None
    color: str = "#8B5CF6"
    icon: str = "📅"
    task_id: Optional[str] = None
    is_recurring: bool = False
    recurrence_rule: Optional[str] = None


class EventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    event_type: Optional[str] = None
    event_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    all_day: Optional[bool] = None
    alert_minutes_before: Optional[int] = None
    alert_sent: Optional[bool] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    task_id: Optional[str] = None


class EventResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    event_type: str
    event_date: date
    start_time: Optional[time]
    end_time: Optional[time]
    all_day: bool
    alert_minutes_before: Optional[int]
    alert_sent: bool
    color: str
    icon: str
    task_id: Optional[str]
    google_event_id: Optional[str]
    is_recurring: bool
    recurrence_rule: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# === Alertas Financieras ===

class FinancialAlertCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    due_day_of_month: int = Field(..., ge=1, le=31)
    alert_days_before: int = Field(default=3, ge=1, le=30)
    amount: Optional[str] = None
    currency: str = "PEN"
    category: str = "tarjeta_credito"
    color: str = "#F59E0B"
    icon: str = "💳"


class FinancialAlertUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    due_day_of_month: Optional[int] = Field(None, ge=1, le=31)
    alert_days_before: Optional[int] = Field(None, ge=1, le=30)
    amount: Optional[str] = None
    currency: Optional[str] = None
    category: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    is_active: Optional[bool] = None


class FinancialAlertResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    due_day_of_month: int
    alert_days_before: int
    amount: Optional[str]
    currency: str
    category: str
    color: str
    icon: str
    is_active: bool
    last_alert_date: Optional[date]
    last_paid_date: Optional[date]
    # Campos calculados
    next_due_date: Optional[date] = None
    next_alert_date: Optional[date] = None
    days_until_due: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
