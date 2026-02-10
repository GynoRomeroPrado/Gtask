"""
Schemas Pydantic para TaskList — validación de request/response.
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, Field


# === Request Schemas ===

class TaskListCreate(BaseModel):
    """Schema para crear una nueva lista de tareas."""
    name: str = Field(..., min_length=1, max_length=100, examples=["Trabajo"])
    description: str | None = Field(None, max_length=500)
    color: str = Field("#6366F1", pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: str = Field("📋", max_length=50)


class TaskListUpdate(BaseModel):
    """Schema para actualizar una lista (todos los campos opcionales)."""
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: str | None = Field(None, max_length=50)
    is_active: bool | None = None
    position: int | None = None


# === Response Schemas ===

class TaskListResponse(BaseModel):
    """Schema de respuesta para una lista de tareas."""
    id: uuid.UUID
    name: str
    description: str | None
    color: str
    icon: str
    is_active: bool
    position: int
    google_list_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskListSummary(BaseModel):
    """Resumen de lista con conteo de tareas (para listados)."""
    id: uuid.UUID
    name: str
    color: str
    icon: str
    is_active: bool
    position: int
    task_count: int = 0

    model_config = {"from_attributes": True}
