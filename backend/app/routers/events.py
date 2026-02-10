"""
Router de Eventos — Cerebro Operativo

CRUD de eventos del calendario interno + motor de alertas.
"""
from datetime import date, timedelta, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.event import Event
from app.schemas.event import EventCreate, EventUpdate, EventResponse

router = APIRouter(prefix="/events", tags=["Eventos / Calendario"])


# === CRUD ===

@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(data: EventCreate, db: Session = Depends(get_db)):
    """Crear un evento en el calendario."""
    event = Event(**data.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/", response_model=list[EventResponse])
def list_events(
    start_date: Optional[date] = Query(None, description="Fecha inicio del rango"),
    end_date: Optional[date] = Query(None, description="Fecha fin del rango"),
    event_type: Optional[str] = Query(None, description="Filtrar por tipo"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Mes específico"),
    year: Optional[int] = Query(None, description="Año específico"),
    db: Session = Depends(get_db),
):
    """Listar eventos con filtros de fecha y tipo."""
    query = db.query(Event)

    # Filtro por rango de fechas
    if start_date and end_date:
        query = query.filter(Event.event_date >= start_date, Event.event_date <= end_date)
    elif month and year:
        # Filtrar por mes/año
        first_day = date(year, month, 1)
        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)
        query = query.filter(Event.event_date >= first_day, Event.event_date <= last_day)
    elif not start_date and not end_date:
        # Por defecto: próximos 30 días
        today = date.today()
        query = query.filter(
            Event.event_date >= today,
            Event.event_date <= today + timedelta(days=30),
        )

    if event_type:
        query = query.filter(Event.event_type == event_type)

    return query.order_by(Event.event_date, Event.start_time).all()


@router.get("/{event_id}", response_model=EventResponse)
def get_event(event_id: str, db: Session = Depends(get_db)):
    """Obtener detalle de un evento."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    return event


@router.put("/{event_id}", response_model=EventResponse)
def update_event(event_id: str, data: EventUpdate, db: Session = Depends(get_db)):
    """Actualizar un evento."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(event, field, value)

    event.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: str, db: Session = Depends(get_db)):
    """Eliminar un evento."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    db.delete(event)
    db.commit()


# === Endpoints especiales ===

@router.get("/today/summary")
def today_summary(db: Session = Depends(get_db)):
    """Resumen del día: eventos de hoy + alertas próximas."""
    today = date.today()
    events_today = (
        db.query(Event)
        .filter(Event.event_date == today)
        .order_by(Event.start_time)
        .all()
    )
    upcoming_alerts = (
        db.query(Event)
        .filter(
            Event.event_type == "financial_alert",
            Event.event_date >= today,
            Event.event_date <= today + timedelta(days=7),
            Event.alert_sent == False,
        )
        .order_by(Event.event_date)
        .all()
    )

    return {
        "date": today.isoformat(),
        "events_count": len(events_today),
        "events": [EventResponse.model_validate(e) for e in events_today],
        "upcoming_alerts": [EventResponse.model_validate(a) for a in upcoming_alerts],
    }
