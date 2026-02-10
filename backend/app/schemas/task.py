"""
Schemas Pydantic para Task — validación de request/response.
"""
import uuid
from datetime import datetime, date
from pydantic import BaseModel, Field
from app.models.task import TaskStatus, TaskPriority


# === Sub-Schemas ===

class TagResponse(BaseModel):
    """Tag embebido en respuesta de tarea."""
    id: uuid.UUID
    name: str
    color: str
    model_config = {"from_attributes": True}


# === Request Schemas ===

class TaskCreate(BaseModel):
    """Schema para crear una nueva tarea."""
    title: str = Field(..., min_length=1, max_length=300, examples=["Revisar reporte de Newmont"])
    description: str | None = Field(None, examples=["Analizar métricas Q4 2025"])
    status: TaskStatus = Field(TaskStatus.PENDING)
    priority: TaskPriority = Field(TaskPriority.MEDIUM)
    due_date: date | None = None
    list_id: uuid.UUID | None = None
    parent_id: uuid.UUID | None = None
    is_recurring: bool = False
    recurrence_rule: str | None = None
    notes: str | None = None
    tag_ids: list[uuid.UUID] = Field(default_factory=list)


class TaskUpdate(BaseModel):
    """Schema para actualizar una tarea (todos los campos opcionales)."""
    title: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: date | None = None
    list_id: uuid.UUID | None = None
    parent_id: uuid.UUID | None = None
    is_recurring: bool | None = None
    recurrence_rule: str | None = None
    notes: str | None = None
    position: int | None = None
    tag_ids: list[uuid.UUID] | None = None


# === Response Schemas ===

class TaskResponse(BaseModel):
    """Schema de respuesta completa de una tarea."""
    id: uuid.UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: date | None
    list_id: uuid.UUID | None
    parent_id: uuid.UUID | None
    is_recurring: bool
    recurrence_rule: str | None
    google_task_id: str | None
    notes: str | None
    position: int
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    tags: list[TagResponse] = []
    subtask_count: int = 0

    model_config = {"from_attributes": True}


class TaskBrief(BaseModel):
    """Resumen de tarea para listados rápidos."""
    id: uuid.UUID
    title: str
    status: TaskStatus
    priority: TaskPriority
    due_date: date | None
    list_id: uuid.UUID | None
    tags: list[TagResponse] = []

    model_config = {"from_attributes": True}
