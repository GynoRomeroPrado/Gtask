"""
Router de Alertas Financieras — Cerebro Operativo

Gestión de pagos recurrentes con alertas preventivas.
Ej: BBVA vencimiento día 2 → alerta día 28-30 del mes anterior.
"""
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.event import FinancialAlert, Event
from app.schemas.event import (
    FinancialAlertCreate, FinancialAlertUpdate, FinancialAlertResponse,
)

router = APIRouter(prefix="/financial-alerts", tags=["Alertas Financieras"])


def calculate_next_dates(alert: FinancialAlert) -> dict:
    """Calcula las próximas fechas de vencimiento y alerta."""
    today = date.today()
    year, month = today.year, today.month

    # Próximo vencimiento
    try:
        next_due = date(year, month, alert.due_day_of_month)
    except ValueError:
        # Si el día no existe en el mes (ej: feb 30), usar último día
        next_month = date(year, month, 1) + relativedelta(months=1)
        next_due = next_month - timedelta(days=1)

    # Si ya pasó este mes, ir al siguiente
    if next_due <= today:
        try:
            next_date = date(year, month, 1) + relativedelta(months=1)
            next_due = date(next_date.year, next_date.month, alert.due_day_of_month)
        except ValueError:
            next_month2 = next_date + relativedelta(months=1)
            next_due = next_month2 - timedelta(days=1)

    next_alert = next_due - timedelta(days=alert.alert_days_before)
    days_until = (next_due - today).days

    return {
        "next_due_date": next_due,
        "next_alert_date": next_alert,
        "days_until_due": days_until,
    }


def enrich_response(alert: FinancialAlert) -> dict:
    """Enriquece la respuesta con campos calculados."""
    data = {c.name: getattr(alert, c.name) for c in alert.__table__.columns}
    dates = calculate_next_dates(alert)
    data.update(dates)
    return data


# === CRUD ===

@router.post("/", response_model=FinancialAlertResponse, status_code=status.HTTP_201_CREATED)
def create_financial_alert(data: FinancialAlertCreate, db: Session = Depends(get_db)):
    """Crear una alerta financiera recurrente."""
    alert = FinancialAlert(**data.model_dump())
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return enrich_response(alert)


@router.get("/", response_model=list[FinancialAlertResponse])
def list_financial_alerts(
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    """Listar alertas financieras con fechas calculadas."""
    query = db.query(FinancialAlert)
    if active_only:
        query = query.filter(FinancialAlert.is_active == True)

    alerts = query.order_by(FinancialAlert.due_day_of_month).all()
    return [enrich_response(a) for a in alerts]


@router.get("/{alert_id}", response_model=FinancialAlertResponse)
def get_financial_alert(alert_id: str, db: Session = Depends(get_db)):
    """Obtener detalle de una alerta financiera."""
    alert = db.query(FinancialAlert).filter(FinancialAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    return enrich_response(alert)


@router.put("/{alert_id}", response_model=FinancialAlertResponse)
def update_financial_alert(
    alert_id: str, data: FinancialAlertUpdate, db: Session = Depends(get_db),
):
    """Actualizar una alerta financiera."""
    alert = db.query(FinancialAlert).filter(FinancialAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(alert, field, value)

    alert.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(alert)
    return enrich_response(alert)


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_financial_alert(alert_id: str, db: Session = Depends(get_db)):
    """Eliminar una alerta financiera."""
    alert = db.query(FinancialAlert).filter(FinancialAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    db.delete(alert)
    db.commit()


@router.post("/{alert_id}/mark-paid", response_model=FinancialAlertResponse)
def mark_as_paid(alert_id: str, db: Session = Depends(get_db)):
    """Marcar una alerta como pagada este mes."""
    alert = db.query(FinancialAlert).filter(FinancialAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")

    alert.last_paid_date = date.today()
    alert.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(alert)
    return enrich_response(alert)


@router.post("/generate-events")
def generate_alert_events(db: Session = Depends(get_db)):
    """
    Genera eventos de calendario para todas las alertas financieras activas.
    Crea eventos de tipo 'financial_alert' para los próximos 2 meses.
    """
    alerts = db.query(FinancialAlert).filter(FinancialAlert.is_active == True).all()
    created = 0

    for alert in alerts:
        dates = calculate_next_dates(alert)
        alert_date = dates["next_alert_date"]
        due_date = dates["next_due_date"]

        # Verificar si ya existe un evento para esta alerta y fecha
        existing = (
            db.query(Event)
            .filter(
                Event.event_type == "financial_alert",
                Event.event_date == alert_date,
                Event.title.contains(alert.name),
            )
            .first()
        )

        if not existing:
            event = Event(
                title=f"⚠️ {alert.name} — vence en {alert.alert_days_before} días",
                description=(
                    f"Vencimiento: {due_date.strftime('%d/%m/%Y')}\n"
                    f"Monto: {alert.amount or 'No especificado'} {alert.currency}"
                ),
                event_type="financial_alert",
                event_date=alert_date,
                all_day=True,
                alert_minutes_before=60 * 24,  # 1 día antes del evento
                color=alert.color,
                icon=alert.icon,
            )
            db.add(event)
            created += 1

    db.commit()
    return {
        "message": f"Se generaron {created} eventos de alerta financiera",
        "alerts_processed": len(alerts),
        "events_created": created,
    }
