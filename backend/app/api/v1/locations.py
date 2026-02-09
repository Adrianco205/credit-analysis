from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import get_db
from app.models.banco import Banco
from pydantic import BaseModel

router = APIRouter()


# ==========================================
# CIUDADES (Lista estática de Colombia)
# ==========================================

CIUDADES_COLOMBIA = [
    {"nombre": "Barranquilla", "departamento": "Atlántico"},
    {"nombre": "Soledad", "departamento": "Atlántico"},
    {"nombre": "Malambo", "departamento": "Atlántico"},
    {"nombre": "Sabanalarga", "departamento": "Atlántico"},
    {"nombre": "Bogotá", "departamento": "Bogotá D.C."},
    {"nombre": "Medellín", "departamento": "Antioquia"},
    {"nombre": "Envigado", "departamento": "Antioquia"},
    {"nombre": "Bello", "departamento": "Antioquia"},
    {"nombre": "Itagüí", "departamento": "Antioquia"},
    {"nombre": "Rionegro", "departamento": "Antioquia"},
    {"nombre": "Sabaneta", "departamento": "Antioquia"},
    {"nombre": "Apartadó", "departamento": "Antioquia"},
    {"nombre": "Turbo", "departamento": "Antioquia"},
    {"nombre": "Caucasia", "departamento": "Antioquia"},
    {"nombre": "Cali", "departamento": "Valle del Cauca"},
    {"nombre": "Palmira", "departamento": "Valle del Cauca"},
    {"nombre": "Buenaventura", "departamento": "Valle del Cauca"},
    {"nombre": "Tuluá", "departamento": "Valle del Cauca"},
    {"nombre": "Cartago", "departamento": "Valle del Cauca"},
    {"nombre": "Buga", "departamento": "Valle del Cauca"},
    {"nombre": "Cartagena", "departamento": "Bolívar"},
    {"nombre": "Magangué", "departamento": "Bolívar"},
    {"nombre": "Turbaco", "departamento": "Bolívar"},
    {"nombre": "Bucaramanga", "departamento": "Santander"},
    {"nombre": "Floridablanca", "departamento": "Santander"},
    {"nombre": "Girón", "departamento": "Santander"},
    {"nombre": "Piedecuesta", "departamento": "Santander"},
    {"nombre": "Barrancabermeja", "departamento": "Santander"},
    {"nombre": "Cúcuta", "departamento": "Norte de Santander"},
    {"nombre": "Ocaña", "departamento": "Norte de Santander"},
    {"nombre": "Pamplona", "departamento": "Norte de Santander"},
    {"nombre": "Pereira", "departamento": "Risaralda"},
    {"nombre": "Dosquebradas", "departamento": "Risaralda"},
    {"nombre": "Santa Marta", "departamento": "Magdalena"},
    {"nombre": "Ciénaga", "departamento": "Magdalena"},
    {"nombre": "Manizales", "departamento": "Caldas"},
    {"nombre": "Villamaría", "departamento": "Caldas"},
    {"nombre": "La Dorada", "departamento": "Caldas"},
    {"nombre": "Ibagué", "departamento": "Tolima"},
    {"nombre": "Espinal", "departamento": "Tolima"},
    {"nombre": "Neiva", "departamento": "Huila"},
    {"nombre": "Pitalito", "departamento": "Huila"},
    {"nombre": "Villavicencio", "departamento": "Meta"},
    {"nombre": "Acacías", "departamento": "Meta"},
    {"nombre": "Granada", "departamento": "Meta"},
    {"nombre": "Armenia", "departamento": "Quindío"},
    {"nombre": "Calarcá", "departamento": "Quindío"},
    {"nombre": "Montería", "departamento": "Córdoba"},
    {"nombre": "Lorica", "departamento": "Córdoba"},
    {"nombre": "Cereté", "departamento": "Córdoba"},
    {"nombre": "Popayán", "departamento": "Cauca"},
    {"nombre": "Santander de Quilichao", "departamento": "Cauca"},
    {"nombre": "Pasto", "departamento": "Nariño"},
    {"nombre": "Ipiales", "departamento": "Nariño"},
    {"nombre": "Tumaco", "departamento": "Nariño"},
    {"nombre": "Valledupar", "departamento": "Cesar"},
    {"nombre": "Aguachica", "departamento": "Cesar"},
    {"nombre": "Tunja", "departamento": "Boyacá"},
    {"nombre": "Duitama", "departamento": "Boyacá"},
    {"nombre": "Sogamoso", "departamento": "Boyacá"},
    {"nombre": "Chiquinquirá", "departamento": "Boyacá"},
    {"nombre": "Sincelejo", "departamento": "Sucre"},
    {"nombre": "Corozal", "departamento": "Sucre"},
    {"nombre": "Riohacha", "departamento": "La Guajira"},
    {"nombre": "Maicao", "departamento": "La Guajira"},
    {"nombre": "Quibdó", "departamento": "Chocó"},
    {"nombre": "Florencia", "departamento": "Caquetá"},
    {"nombre": "Yopal", "departamento": "Casanare"},
    {"nombre": "Aguazul", "departamento": "Casanare"},
    {"nombre": "Arauca", "departamento": "Arauca"},
    {"nombre": "Mocoa", "departamento": "Putumayo"},
    {"nombre": "Leticia", "departamento": "Amazonas"},
    {"nombre": "San José del Guaviare", "departamento": "Guaviare"},
    {"nombre": "Mitú", "departamento": "Vaupés"},
    {"nombre": "Puerto Carreño", "departamento": "Vichada"},
    {"nombre": "Inírida", "departamento": "Guainía"},
    {"nombre": "San Andrés", "departamento": "San Andrés y Providencia"},
    {"nombre": "Providencia", "departamento": "San Andrés y Providencia"},
    {"nombre": "Zipaquirá", "departamento": "Cundinamarca"},
    {"nombre": "Facatativá", "departamento": "Cundinamarca"},
    {"nombre": "Chía", "departamento": "Cundinamarca"},
    {"nombre": "Soacha", "departamento": "Cundinamarca"},
    {"nombre": "Fusagasugá", "departamento": "Cundinamarca"},
    {"nombre": "Girardot", "departamento": "Cundinamarca"},
    {"nombre": "Mosquera", "departamento": "Cundinamarca"},
    {"nombre": "Madrid", "departamento": "Cundinamarca"},
    {"nombre": "Funza", "departamento": "Cundinamarca"},
    {"nombre": "Cajicá", "departamento": "Cundinamarca"},
    {"nombre": "La Calera", "departamento": "Cundinamarca"},
    {"nombre": "Cota", "departamento": "Cundinamarca"},
    {"nombre": "Sopó", "departamento": "Cundinamarca"},
    {"nombre": "Tocancipá", "departamento": "Cundinamarca"},
]


class CiudadDepartamentoResponse(BaseModel):
    valor: str  # "Ciudad, Departamento"
    ciudad: str
    departamento: str


@router.get("/cities", response_model=List[CiudadDepartamentoResponse])
def listar_ciudades():
    """
    Lista todas las ciudades de Colombia con su departamento.
    Retorna lista ordenada para usar en un dropdown/select.
    """
    result = []
    for c in sorted(CIUDADES_COLOMBIA, key=lambda x: x["nombre"]):
        result.append(CiudadDepartamentoResponse(
            valor=f"{c['nombre']}, {c['departamento']}",
            ciudad=c["nombre"],
            departamento=c["departamento"]
        ))
    return result


# ==========================================
# BANCOS
# ==========================================

class BancoResponse(BaseModel):
    id: int
    nombre: str

    class Config:
        from_attributes = True


@router.get("/banks", response_model=List[BancoResponse])
def listar_bancos(
    db: Session = Depends(get_db)
):
    """
    Lista todos los bancos disponibles.
    Retorna lista ordenada alfabéticamente.
    """
    bancos = db.query(Banco).filter(Banco.activo == True).order_by(Banco.nombre).all()
    return [BancoResponse(id=b.id, nombre=b.nombre) for b in bancos]
