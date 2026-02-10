"""
Router de Tags — CRUD para etiquetas de tareas.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.database import get_db
from app.models.tag import Tag

router = APIRouter(prefix="/tags", tags=["Tags"])


# === Schemas locales ===

class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, examples=["financiero"])
    color: str = Field("#8B5CF6", pattern=r"^#[0-9A-Fa-f]{6}$")


class TagUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=50)
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")


class TagResponse(BaseModel):
    id: uuid.UUID
    name: str
    color: str
    model_config = {"from_attributes": True}


# === Endpoints ===

@router.post("/", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
def create_tag(data: TagCreate, db: Session = Depends(get_db)):
    """Crear un nuevo tag."""
    # Verificar unicidad
    existing = db.query(Tag).filter(Tag.name == data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tag '{data.name}' ya existe",
        )
    tag = Tag(**data.model_dump())
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


@router.get("/", response_model=list[TagResponse])
def get_all_tags(db: Session = Depends(get_db)):
    """Obtener todos los tags."""
    return db.query(Tag).order_by(Tag.name).all()


@router.put("/{tag_id}", response_model=TagResponse)
def update_tag(tag_id: uuid.UUID, data: TagUpdate, db: Session = Depends(get_db)):
    """Actualizar un tag."""
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail=f"Tag {tag_id} no encontrado")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tag, field, value)

    db.commit()
    db.refresh(tag)
    return tag


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(tag_id: uuid.UUID, db: Session = Depends(get_db)):
    """Eliminar un tag."""
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail=f"Tag {tag_id} no encontrado")
    db.delete(tag)
    db.commit()
