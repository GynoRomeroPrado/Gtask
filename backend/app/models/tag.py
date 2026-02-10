"""
Modelo Tag — Etiquetas para clasificar tareas transversalmente.
Una tarea puede tener múltiples tags (many-to-many).
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Tag(Base):
    """Etiqueta para tareas (ej: urgente, financiero, BBVA, Newmont)."""

    __tablename__ = "tags"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    color: Mapped[str] = mapped_column(String(7), default="#8B5CF6")  # Hex color

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relación many-to-many con tareas
    tasks: Mapped[list["Task"]] = relationship(
        "Task",
        secondary="task_tags",
        back_populates="tags",
    )

    def __repr__(self) -> str:
        return f"<Tag(id={self.id}, name='{self.name}')>"
