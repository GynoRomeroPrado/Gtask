"""
Modelo TaskList — Listas de tareas (Trabajo, INTIMIQ, Salud, Personal, etc.)
Cada lista agrupa tareas por contexto/categoría.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class TaskList(Base):
    """Lista de tareas (ej: Trabajo, INTIMIQ, Salud, Personal)."""

    __tablename__ = "task_lists"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    color: Mapped[str] = mapped_column(String(7), default="#6366F1")  # Hex color
    icon: Mapped[str] = mapped_column(String(50), default="📋")
    google_list_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True,
        comment="ID de la lista en Google Tasks para sincronización"
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    position: Mapped[int] = mapped_column(default=0, comment="Orden de visualización")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relación con tareas
    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="task_list", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<TaskList(id={self.id}, name='{self.name}')>"
