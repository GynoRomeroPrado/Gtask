"""
Modelo Task — Tarea principal del sistema.
Soporta: prioridades, estados custom, subtareas, dependencias, tags,
recurrencia y sincronización con Google Tasks.

PostgreSQL es el source of truth para toda la lógica avanzada
que Google Tasks API no soporta (prioridades, dependencias, estados custom).
"""
import uuid
import enum
from datetime import datetime, date, timezone
from sqlalchemy import (
    String, Text, Integer, Boolean, Date, DateTime,
    ForeignKey, Table, Column, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


# === Enums ===

class TaskStatus(str, enum.Enum):
    """Estados posibles de una tarea."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DEFERRED = "deferred"  # Postergada — útil para analítica


class TaskPriority(int, enum.Enum):
    """Prioridades numéricas (menor = más urgente)."""
    URGENT = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


# === Tabla intermedia Task <-> Tag (many-to-many) ===

task_tags = Table(
    "task_tags",
    Base.metadata,
    Column("task_id", ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


# === Modelo Principal ===

class Task(Base):
    """
    Tarea del sistema Cerebro Operativo.
    
    Campos clave:
    - status/priority: Gestionados en PostgreSQL (Google Tasks no los soporta)
    - parent_id: Subtareas (self-referencing)
    - google_task_id: Enlace para sincronización con Google Tasks
    - is_recurring + recurrence_rule: Sistema de tareas recurrentes
    """

    __tablename__ = "tasks"

    # --- Identificación ---
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Estado y Prioridad (PostgreSQL como source of truth) ---
    status: Mapped[str] = mapped_column(
        String(20),
        default=TaskStatus.PENDING.value,
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        default=TaskPriority.MEDIUM.value,
    )

    # --- Fechas ---
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # --- Relación con Lista ---
    list_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("task_lists.id", ondelete="SET NULL"),
        nullable=True,
    )
    task_list: Mapped["TaskList | None"] = relationship(
        "TaskList", back_populates="tasks",
    )

    # --- Subtareas (self-referencing) ---
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=True,
        comment="Tarea padre para subtareas",
    )
    subtasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    parent: Mapped["Task | None"] = relationship(
        "Task",
        back_populates="subtasks",
        remote_side="Task.id",
    )

    # --- Tags (many-to-many) ---
    tags: Mapped[list["Tag"]] = relationship(
        "Tag",
        secondary=task_tags,
        back_populates="tasks",
    )

    # --- Recurrencia ---
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    recurrence_rule: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
        comment="Regla iCal RRULE (ej: FREQ=WEEKLY;BYDAY=MO,WE,FR)",
    )

    # --- Sincronización con Google Tasks ---
    google_task_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True,
        comment="ID de la tarea en Google Tasks para sync",
    )
    google_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Última sincronización exitosa con Google Tasks",
    )

    # --- Notas adicionales ---
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0, comment="Orden dentro de la lista")

    # --- Timestamps ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title='{self.title}', status={self.status.value})>"

    def mark_completed(self) -> None:
        """Marca la tarea como completada con timestamp."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)

    def defer(self, new_due_date: date) -> None:
        """Posterga la tarea a una nueva fecha."""
        self.status = TaskStatus.DEFERRED
        self.due_date = new_due_date


# === Dependencias entre Tareas ===

class DependencyType(str, enum.Enum):
    """Tipo de dependencia entre tareas."""
    BLOCKS = "blocks"          # La tarea A bloquea a la tarea B
    REQUIRED_BY = "required_by"  # La tarea A es requerida por B


class TaskDependency(Base):
    """
    Dependencia entre dos tareas.
    Ejemplo: "Revisar reporte" BLOCKS "Enviar resumen al cliente"
    """

    __tablename__ = "task_dependencies"
    __table_args__ = (
        UniqueConstraint("task_id", "depends_on_id", name="uq_task_dependency"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    depends_on_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    dependency_type: Mapped[str] = mapped_column(
        String(20),
        default=DependencyType.BLOCKS.value,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<TaskDependency(task={self.task_id} {self.dependency_type.value} {self.depends_on_id})>"
