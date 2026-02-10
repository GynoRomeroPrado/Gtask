"""
Bio-Optimización — Cerebro Operativo

Gestión de metas de bienestar y salud:
- CRUD de HealthGoals
- Registrar progreso diario
- Calcular rachas
- Resumen del día
"""
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.health_goal import HealthGoal

router = APIRouter(prefix="/bio", tags=["Bio-Optimización"])


# === Schemas ===

class HealthGoalCreate(BaseModel):
    name: str
    category: str  # gym, water, sleep, meditation, nutrition, breaks
    description: Optional[str] = None
    target_value: float
    target_unit: str
    frequency: str = "daily"
    reminder_time: Optional[str] = None
    color: str = "#10B981"


class HealthGoalUpdate(BaseModel):
    current_value: Optional[float] = None
    is_active: Optional[bool] = None
    name: Optional[str] = None
    target_value: Optional[float] = None
    reminder_time: Optional[str] = None


class ProgressLog(BaseModel):
    value: float  # Valor a agregar (ej: 1 vaso, 0.5 horas)


# === Endpoints ===

@router.get("/goals")
def list_health_goals(db: Session = Depends(get_db)):
    """Lista todas las metas de bienestar."""
    goals = db.query(HealthGoal).filter(HealthGoal.is_active == True).all()
    return [_goal_to_dict(g) for g in goals]


@router.post("/goals")
def create_health_goal(data: HealthGoalCreate, db: Session = Depends(get_db)):
    """Crea una nueva meta de bienestar."""
    goal = HealthGoal(
        name=data.name,
        category=data.category,
        description=data.description,
        target_value=data.target_value,
        target_unit=data.target_unit,
        frequency=data.frequency,
        reminder_time=data.reminder_time,
        color=data.color,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return _goal_to_dict(goal)


@router.post("/goals/{goal_id}/log")
def log_progress(goal_id: str, log: ProgressLog, db: Session = Depends(get_db)):
    """Registra progreso en una meta."""
    goal = db.query(HealthGoal).filter(HealthGoal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Meta no encontrada")

    today = date.today()
    goal.current_value = (goal.current_value or 0) + log.value

    # Verificar si la meta se cumplió
    if goal.current_value >= goal.target_value:
        goal.total_completions = (goal.total_completions or 0) + 1

        # Calcular racha
        if goal.last_completed:
            days_since = (today - goal.last_completed).days
            if days_since <= 1:
                goal.streak_days = (goal.streak_days or 0) + 1
            else:
                goal.streak_days = 1
        else:
            goal.streak_days = 1

        if goal.streak_days > (goal.best_streak or 0):
            goal.best_streak = goal.streak_days

        goal.last_completed = today
        completed = True
    else:
        completed = False

    db.commit()
    db.refresh(goal)

    return {
        **_goal_to_dict(goal),
        "completed": completed,
        "message": f"🎉 ¡Meta cumplida! Racha: {goal.streak_days} días" if completed
                   else f"📈 Progreso: {goal.current_value}/{goal.target_value} {goal.target_unit}",
    }


@router.post("/goals/{goal_id}/reset")
def reset_daily_progress(goal_id: str, db: Session = Depends(get_db)):
    """Reinicia el progreso diario de una meta."""
    goal = db.query(HealthGoal).filter(HealthGoal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Meta no encontrada")

    goal.current_value = 0
    db.commit()
    db.refresh(goal)
    return _goal_to_dict(goal)


@router.delete("/goals/{goal_id}")
def delete_health_goal(goal_id: str, db: Session = Depends(get_db)):
    """Desactiva una meta."""
    goal = db.query(HealthGoal).filter(HealthGoal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Meta no encontrada")

    goal.is_active = False
    db.commit()
    return {"message": "Meta desactivada"}


@router.get("/today")
def bio_today_summary(db: Session = Depends(get_db)):
    """Resumen de bio-optimización del día."""
    goals = db.query(HealthGoal).filter(HealthGoal.is_active == True).all()

    category_icons = {
        "gym": "🏋️", "water": "💧", "sleep": "😴",
        "meditation": "🧘", "nutrition": "🥗", "breaks": "☕",
    }

    summary = []
    total_goals = len(goals)
    completed_goals = 0

    for g in goals:
        pct = min(round((g.current_value or 0) / max(g.target_value, 0.01) * 100), 100)
        is_done = pct >= 100
        if is_done:
            completed_goals += 1

        summary.append({
            "id": g.id,
            "name": g.name,
            "category": g.category,
            "icon": category_icons.get(g.category, "🎯"),
            "current": g.current_value or 0,
            "target": g.target_value,
            "unit": g.target_unit,
            "percent": pct,
            "completed": is_done,
            "streak": g.streak_days or 0,
            "color": g.color,
        })

    wellness_score = round(completed_goals / max(total_goals, 1) * 100)

    return {
        "date": str(date.today()),
        "wellness_score": wellness_score,
        "total_goals": total_goals,
        "completed_goals": completed_goals,
        "goals": summary,
    }


def _goal_to_dict(g):
    """Convierte HealthGoal a dict serializable."""
    pct = min(round((g.current_value or 0) / max(g.target_value, 0.01) * 100), 100)
    return {
        "id": g.id,
        "name": g.name,
        "category": g.category,
        "description": g.description,
        "target_value": g.target_value,
        "target_unit": g.target_unit,
        "frequency": g.frequency,
        "current_value": g.current_value or 0,
        "percent": pct,
        "streak_days": g.streak_days or 0,
        "best_streak": g.best_streak or 0,
        "total_completions": g.total_completions or 0,
        "last_completed": str(g.last_completed) if g.last_completed else None,
        "reminder_time": g.reminder_time,
        "color": g.color,
        "is_active": g.is_active,
    }
