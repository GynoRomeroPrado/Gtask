"""
Router de Tareas — CRUD completo con filtros avanzados.
Soporta: filtrado por lista, estado, prioridad, fecha, búsqueda por texto.
"""
import uuid
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models.task import Task, TaskStatus, TaskPriority, TaskDependency
from app.models.tag import Tag
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse

router = APIRouter(prefix="/tasks", tags=["Tareas"])


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(data: TaskCreate, db: Session = Depends(get_db)):
    """Crear una nueva tarea."""
    # Extraer tag_ids y crear la tarea sin ellos
    tag_ids = data.tag_ids
    task_data = data.model_dump(exclude={"tag_ids"})
    task = Task(**task_data)

    # Asociar tags si se proporcionaron
    if tag_ids:
        tags = db.query(Tag).filter(Tag.id.in_(tag_ids)).all()
        task.tags = tags

    db.add(task)
    db.commit()
    db.refresh(task)
    return _build_task_response(task)


@router.get("/", response_model=list[TaskResponse])
def get_tasks(
    list_id: uuid.UUID | None = None,
    status_filter: TaskStatus | None = Query(None, alias="status"),
    priority: TaskPriority | None = None,
    due_before: date | None = None,
    due_after: date | None = None,
    search: str | None = None,
    parent_id: uuid.UUID | None = None,
    include_completed: bool = False,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Listar tareas con filtros avanzados.
    
    Filtros disponibles:
    - list_id: Filtrar por lista
    - status: Filtrar por estado (pending, in_progress, completed, cancelled, deferred)
    - priority: Filtrar por prioridad (1=urgent, 2=high, 3=medium, 4=low)
    - due_before/due_after: Rango de fechas
    - search: Búsqueda en título y descripción
    - parent_id: Solo subtareas de una tarea específica
    """
    query = db.query(Task).options(joinedload(Task.tags))

    # Solo tareas raíz por defecto (no subtareas)
    if parent_id is not None:
        query = query.filter(Task.parent_id == parent_id)
    else:
        query = query.filter(Task.parent_id.is_(None))

    if list_id:
        query = query.filter(Task.list_id == list_id)

    if status_filter:
        query = query.filter(Task.status == status_filter)
    elif not include_completed:
        query = query.filter(Task.status.notin_([
            TaskStatus.COMPLETED, TaskStatus.CANCELLED
        ]))

    if priority:
        query = query.filter(Task.priority == priority)

    if due_before:
        query = query.filter(Task.due_date <= due_before)

    if due_after:
        query = query.filter(Task.due_date >= due_after)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            Task.title.ilike(search_term) | Task.description.ilike(search_term)
        )

    tasks = (
        query
        .order_by(Task.priority, Task.due_date.nullslast(), Task.position)
        .limit(limit)
        .offset(offset)
        .all()
    )

    return [_build_task_response(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: uuid.UUID, db: Session = Depends(get_db)):
    """Obtener una tarea por su ID con subtareas y tags."""
    task = (
        db.query(Task)
        .options(joinedload(Task.tags), joinedload(Task.subtasks))
        .filter(Task.id == task_id)
        .first()
    )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tarea {task_id} no encontrada",
        )
    return _build_task_response(task)


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: uuid.UUID,
    data: TaskUpdate,
    db: Session = Depends(get_db),
):
    """Actualizar una tarea existente."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tarea {task_id} no encontrada",
        )

    update_data = data.model_dump(exclude_unset=True)

    # Manejar tags separadamente
    if "tag_ids" in update_data:
        tag_ids = update_data.pop("tag_ids")
        if tag_ids is not None:
            tags = db.query(Tag).filter(Tag.id.in_(tag_ids)).all()
            task.tags = tags

    # Marcar como completada si el status cambia a COMPLETED
    if "status" in update_data and update_data["status"] == TaskStatus.COMPLETED:
        task.mark_completed()
        update_data.pop("status")  # Ya se actualizó en mark_completed()

    for field, value in update_data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return _build_task_response(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: uuid.UUID, db: Session = Depends(get_db)):
    """Eliminar una tarea y sus subtareas."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tarea {task_id} no encontrada",
        )
    db.delete(task)
    db.commit()


# === Acciones Especiales ===

@router.post("/{task_id}/complete", response_model=TaskResponse)
def complete_task(task_id: uuid.UUID, db: Session = Depends(get_db)):
    """Marcar una tarea como completada."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tarea {task_id} no encontrada",
        )
    task.mark_completed()
    db.commit()
    db.refresh(task)
    return _build_task_response(task)


@router.post("/{task_id}/defer", response_model=TaskResponse)
def defer_task(
    task_id: uuid.UUID,
    new_due_date: date = Query(..., description="Nueva fecha de vencimiento"),
    db: Session = Depends(get_db),
):
    """Postergar una tarea a una nueva fecha."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tarea {task_id} no encontrada",
        )
    task.defer(new_due_date)
    db.commit()
    db.refresh(task)
    return _build_task_response(task)


# === Helpers ===

def _build_task_response(task: Task) -> TaskResponse:
    """Construir respuesta de tarea con conteo de subtareas."""
    response = TaskResponse.model_validate(task)
    response.subtask_count = len(task.subtasks) if task.subtasks else 0
    return response
