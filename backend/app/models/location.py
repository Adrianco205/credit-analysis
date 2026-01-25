from sqlalchemy import String, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Departamento(Base):
    __tablename__ = "departamentos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

class Ciudad(Base):
    __tablename__ = "ciudades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    departamento_id: Mapped[int] = mapped_column(ForeignKey("departamentos.id"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)