"""
Analítica Avanzada — Cerebro Operativo

Endpoints para analizar patrones de productividad:
- Tareas postergadas: frecuencia y patterns
- Distribución temporal de trabajo
- Horas más productivas
- Tendencias semanales/mensuales
"""
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.task import Task

router = APIRouter(prefix="/analytics", tags=["Analítica"])


@router.get("/postponed-tasks")
def postponed_tasks_analysis(db: Session = Depends(get_db)):
    """Analiza tareas que se postergaron (vencidas o sin fecha)."""
    today = date.today()
    all_tasks = db.query(Task).all()

    pending = [t for t in all_tasks if t.status in ("pending", "in_progress")]
    completed = [t for t in all_tasks if t.status == "completed"]

    # Tareas vencidas
    overdue = [t for t in pending if t.due_date and t.due_date < today]

    # Tareas sin fecha límite (potencialmente procrastinadas)
    no_deadline = [t for t in pending if not t.due_date]

    # Tareas urgentes no atendidas (prioridad 1 pendientes)
    urgent_pending = [t for t in pending if t.priority == 1]

    # Antigüedad promedio de tareas pendientes
    ages = []
    for t in pending:
        try:
            created = datetime.fromisoformat(str(t.created_at))
            age = (datetime.now() - created).days
            ages.append(age)
        except Exception:
            pass

    avg_age = round(sum(ages) / max(len(ages), 1), 1)

    # Distribución por prioridad de las vencidas
    overdue_by_priority = {}
    for t in overdue:
        p = t.priority or 3
        overdue_by_priority[p] = overdue_by_priority.get(p, 0) + 1

    return {
        "total_pending": len(pending),
        "overdue": len(overdue),
        "no_deadline": len(no_deadline),
        "urgent_pending": len(urgent_pending),
        "avg_task_age_days": avg_age,
        "overdue_by_priority": overdue_by_priority,
        "recommendations": _generate_recommendations(
            overdue=len(overdue),
            no_deadline=len(no_deadline),
            urgent=len(urgent_pending),
            avg_age=avg_age,
        ),
    }


@router.get("/productivity-patterns")
def productivity_patterns(
    days: int = Query(30, ge=7, le=180),
    db: Session = Depends(get_db),
):
    """Analiza patrones de productividad por hora y día."""
    cutoff = datetime.now() - timedelta(days=days)

    completed = db.query(Task).filter(
        Task.status == "completed",
        Task.updated_at >= cutoff.isoformat(),
    ).all()

    # Actividad por hora del día
    hour_map = {h: 0 for h in range(24)}
    day_map = {d: 0 for d in range(7)}

    for t in completed:
        try:
            dt = datetime.fromisoformat(str(t.updated_at))
            hour_map[dt.hour] = hour_map.get(dt.hour, 0) + 1
            day_map[dt.weekday()] = day_map.get(dt.weekday(), 0) + 1
        except Exception:
            pass

    # Encontrar hora más productiva
    peak_hour = max(hour_map, key=hour_map.get) if any(hour_map.values()) else None
    peak_day = max(day_map, key=day_map.get) if any(day_map.values()) else None

    day_names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

    return {
        "period_days": days,
        "total_completed": len(completed),
        "peak_hour": peak_hour,
        "peak_hour_label": f"{peak_hour}:00 - {peak_hour + 1}:00" if peak_hour is not None else None,
        "peak_day": day_names[peak_day] if peak_day is not None else None,
        "hourly_distribution": [
            {"hour": h, "label": f"{h:02d}:00", "count": hour_map[h]}
            for h in range(24)
        ],
        "daily_distribution": [
            {"day": day_names[d], "count": day_map[d]}
            for d in range(7)
        ],
    }


@router.get("/weekly-report")
def weekly_report(db: Session = Depends(get_db)):
    """Genera un reporte semanal automatizado."""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    all_tasks = db.query(Task).all()

    # Tareas completadas esta semana
    completed_this_week = []
    for t in all_tasks:
        if t.status == "completed" and t.updated_at:
            try:
                dt = datetime.fromisoformat(str(t.updated_at)).date()
                if week_start <= dt <= week_end:
                    completed_this_week.append({
                        "title": t.title,
                        "priority": t.priority,
                        "completed_at": str(dt),
                    })
            except Exception:
                pass

    # Pendientes
    pending = [t for t in all_tasks if t.status in ("pending", "in_progress")]
    overdue = [t for t in pending if t.due_date and t.due_date < today]

    # Próximas (esta semana)
    upcoming = [
        {"title": t.title, "due_date": str(t.due_date), "priority": t.priority}
        for t in pending
        if t.due_date and week_start <= t.due_date <= week_end
    ]

    # Score de productividad (0-100)
    total = len(completed_this_week) + len(pending)
    score = round(len(completed_this_week) / max(total, 1) * 100) if total else 50

    # Emoji de score
    score_emoji = "🔥" if score >= 80 else "💪" if score >= 60 else "📈" if score >= 40 else "⚠️"

    return {
        "week": f"{week_start.strftime('%d/%m')} - {week_end.strftime('%d/%m/%Y')}",
        "score": score,
        "score_emoji": score_emoji,
        "completed": {
            "count": len(completed_this_week),
            "tasks": completed_this_week[:10],
        },
        "pending": {
            "total": len(pending),
            "overdue": len(overdue),
        },
        "upcoming": upcoming[:5],
        "summary": _build_weekly_summary(
            completed=len(completed_this_week),
            pending=len(pending),
            overdue=len(overdue),
            score=score,
        ),
    }


def _generate_recommendations(overdue, no_deadline, urgent, avg_age):
    """Genera recomendaciones basadas en el análisis."""
    recs = []
    if overdue > 0:
        recs.append(f"⚠️ Tienes {overdue} tarea(s) vencida(s). Revísalas y reprograma o completa.")
    if no_deadline > 3:
        recs.append(f"📅 {no_deadline} tareas sin fecha. Asigna fechas para evitar procrastinación.")
    if urgent > 0:
        recs.append(f"🔴 {urgent} tarea(s) urgente(s) pendiente(s). ¡Atiéndelas primero!")
    if avg_age > 14:
        recs.append(f"🐢 La antigüedad promedio es {avg_age} días. Considera priorizar las más antiguas.")
    if not recs:
        recs.append("✅ ¡Excelente! Tu gestión de tareas está al día.")
    return recs


def _build_weekly_summary(completed, pending, overdue, score):
    """Construye el resumen narrativo de la semana."""
    parts = [f"## 📊 Reporte Semanal\n\n**Score: {score}/100**\n"]
    if completed > 0:
        parts.append(f"✅ Completaste **{completed}** tarea(s) esta semana.")
    if overdue > 0:
        parts.append(f"⚠️ Tienes **{overdue}** tarea(s) vencida(s).")
    if pending < 5:
        parts.append("💪 ¡Carga de trabajo manejable!")
    elif pending > 10:
        parts.append(f"📋 **{pending}** tareas pendientes — considera priorizar.")
    return "\n".join(parts)
