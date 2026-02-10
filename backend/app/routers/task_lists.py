"""
Router de Listas de Tareas — CRUD completo para TaskList.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.task_list import TaskList
from app.models.task import Task
from app.schemas.task_list import (
    TaskListCreate, TaskListUpdate, TaskListResponse, TaskListSummary
)

router = APIRouter(prefix="/lists", tags=["Listas de Tareas"])


@router.post("/", response_model=TaskListResponse, status_code=status.HTTP_201_CREATED)
def create_list(data: TaskListCreate, db: Session = Depends(get_db)):
    """Crear una nueva lista de tareas."""
    task_list = TaskList(**data.model_dump())
    db.add(task_list)
    db.commit()
    db.refresh(task_list)
    return task_list


@router.get("/", response_model=list[TaskListSummary])
def get_all_lists(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
):
    """Obtener todas las listas con conteo de tareas."""
    query = db.query(
        TaskList,
        func.count(Task.id).label("task_count"),
    ).outerjoin(Task, Task.list_id == TaskList.id)

    if not include_inactive:
        query = query.filter(TaskList.is_active == True)

    results = query.group_by(TaskList.id).order_by(TaskList.position).all()

    response = []
    for task_list, task_count in results:
        item = TaskListSummary.model_validate(task_list)
        item.task_count = task_count
        response.append(item)

    return response


@router.get("/{list_id}", response_model=TaskListResponse)
def get_list(list_id: uuid.UUID, db: Session = Depends(get_db)):
    """Obtener una lista por su ID."""
    task_list = db.query(TaskList).filter(TaskList.id == list_id).first()
    if not task_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lista {list_id} no encontrada",
        )
    return task_list


@router.put("/{list_id}", response_model=TaskListResponse)
def update_list(
    list_id: uuid.UUID,
    data: TaskListUpdate,
    db: Session = Depends(get_db),
):
    """Actualizar una lista existente."""
    task_list = db.query(TaskList).filter(TaskList.id == list_id).first()
    if not task_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lista {list_id} no encontrada",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task_list, field, value)

    db.commit()
    db.refresh(task_list)
    return task_list


@router.delete("/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_list(list_id: uuid.UUID, db: Session = Depends(get_db)):
    """Eliminar una lista y todas sus tareas."""
    task_list = db.query(TaskList).filter(TaskList.id == list_id).first()
    if not task_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lista {list_id} no encontrada",
        )
    db.delete(task_list)
    db.commit()
