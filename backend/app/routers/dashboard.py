"""
Dashboard de Productividad — Cerebro Operativo

Endpoints para analítica y métricas:
- Resumen general del sistema
- Estadísticas de tareas por período
- Métricas de productividad
- Datos para gráficos del frontend
"""
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.task import Task
from app.models.event import Event, FinancialAlert
from app.models.conversation import Conversation

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/overview")
def dashboard_overview(db: Session = Depends(get_db)):
    """Resumen general del sistema — datos para el dashboard principal."""
    today = date.today()
    today_str = today.isoformat()

    # Tareas
    all_tasks = db.query(Task).all()
    pending = [t for t in all_tasks if t.status in ("pending", "in_progress")]
    completed = [t for t in all_tasks if t.status == "completed"]
    overdue = [t for t in pending if t.due_date and t.due_date < today]
    today_tasks = [t for t in pending if t.due_date and t.due_date.isoformat() == today_str]

    # Prioridades
    by_priority = {}
    for t in pending:
        p = t.priority or 3
        by_priority[p] = by_priority.get(p, 0) + 1

    # Eventos hoy
    today_events = db.query(Event).filter(Event.event_date == today_str).count()

    # Alertas financieras
    active_alerts = db.query(FinancialAlert).filter(
        FinancialAlert.is_active == True
    ).all()
    urgent_alerts = [a for a in active_alerts if _days_until_due(a, today) <= 3]

    # Conversaciones con IA
    ai_sessions = db.query(
        func.count(func.distinct(Conversation.session_id))
    ).scalar()

    return {
        "date": today_str,
        "tasks": {
            "total": len(all_tasks),
            "pending": len(pending),
            "completed": len(completed),
            "overdue": len(overdue),
            "today": len(today_tasks),
            "completion_rate": round(
                len(completed) / max(len(all_tasks), 1) * 100, 1
            ),
            "by_priority": {
                "urgent": by_priority.get(1, 0),
                "high": by_priority.get(2, 0),
                "medium": by_priority.get(3, 0),
                "low": by_priority.get(4, 0),
            },
        },
        "events": {
            "today": today_events,
        },
        "financial": {
            "active_alerts": len(active_alerts),
            "urgent": len(urgent_alerts),
        },
        "ai": {
            "total_sessions": ai_sessions,
        },
    }


@router.get("/task-stats")
def task_statistics(
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
):
    """Estadísticas de tareas para un período dado."""
    cutoff = date.today() - timedelta(days=days)

    # Tareas completadas en el período
    completed = db.query(Task).filter(
        Task.status == "completed",
        Task.updated_at >= cutoff.isoformat(),
    ).all()

    # Tareas creadas en el período
    created = db.query(Task).filter(
        Task.created_at >= cutoff.isoformat(),
    ).all()

    # Actividad por día de la semana (0=lun, 6=dom)
    day_activity = {i: 0 for i in range(7)}
    for t in completed:
        try:
            dt = datetime.fromisoformat(str(t.updated_at))
            dow = dt.weekday()
            day_activity[dow] = day_activity.get(dow, 0) + 1
        except Exception:
            pass

    day_names = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

    return {
        "period_days": days,
        "created": len(created),
        "completed": len(completed),
        "velocity": round(len(completed) / max(days / 7, 1), 1),  # por semana
        "day_activity": [
            {"day": day_names[i], "count": day_activity[i]}
            for i in range(7)
        ],
    }


@router.get("/streaks")
def productivity_streaks(db: Session = Depends(get_db)):
    """Calcula rachas de productividad."""
    today = date.today()

    # Obtener fechas de completar tareas
    completed = db.query(Task).filter(
        Task.status == "completed"
    ).all()

    completion_dates = set()
    for t in completed:
        try:
            dt = datetime.fromisoformat(str(t.updated_at))
            completion_dates.add(dt.date())
        except Exception:
            pass

    # Calcular racha actual
    current_streak = 0
    check_date = today
    while check_date in completion_dates:
        current_streak += 1
        check_date -= timedelta(days=1)

    # Mejor racha
    best_streak = 0
    sorted_dates = sorted(completion_dates)
    if sorted_dates:
        streak = 1
        for i in range(1, len(sorted_dates)):
            if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
                streak += 1
            else:
                best_streak = max(best_streak, streak)
                streak = 1
        best_streak = max(best_streak, streak)

    # Completadas esta semana
    week_start = today - timedelta(days=today.weekday())
    this_week = sum(1 for d in completion_dates if d >= week_start)

    return {
        "current_streak": current_streak,
        "best_streak": best_streak,
        "completed_this_week": this_week,
        "total_days_active": len(completion_dates),
    }


def _days_until_due(alert, today):
    """Helper — calcula días hasta vencimiento de una alerta."""
    try:
        next_due = date(today.year, today.month, alert.due_day_of_month)
        if next_due < today:
            month = today.month + 1
            year = today.year
            if month > 12:
                month = 1
                year += 1
            next_due = date(year, month, alert.due_day_of_month)
        return (next_due - today).days
    except ValueError:
        return 999
