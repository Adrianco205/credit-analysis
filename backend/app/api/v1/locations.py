from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List

from app.api.deps import get_db
from app.models.location import Ciudad, Departamento
from pydantic import BaseModel

router = APIRouter()


class CiudadResponse(BaseModel):
    id: int
    nombre: str
    departamento: str

    class Config:
        from_attributes = True


@router.get("/cities", response_model=List[CiudadResponse])
def buscar_ciudades(
    q: str | None = Query(None, description="Buscar ciudades por nombre"),
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db)
):
    """
    Busca ciudades de Colombia por nombre.
    Retorna máximo 50 resultados ordenados alfabéticamente.
    """
    query = db.query(Ciudad, Departamento).join(
        Departamento, Ciudad.departamento_id == Departamento.id
    )
    
    if q:
        search_term = f"%{q}%"
        query = query.filter(
            or_(
                Ciudad.nombre.ilike(search_term),
                Departamento.nombre.ilike(search_term)
            )
        )
    
    results = query.order_by(Ciudad.nombre).limit(limit).all()
    
    return [
        CiudadResponse(
            id=ciudad.id,
            nombre=ciudad.nombre,
            departamento=departamento.nombre
        )
        for ciudad, departamento in results
    ]
