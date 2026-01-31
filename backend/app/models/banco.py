from sqlalchemy import String, Integer, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Banco(Base):
    """Modelo para entidades bancarias colombianas"""
    __tablename__ = "bancos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    codigo_superintendencia: Mapped[str | None] = mapped_column(String(10))  # Código SFC
    nit: Mapped[str | None] = mapped_column(String(20))
    
    # Para identificar formato del extracto PDF
    patron_identificacion: Mapped[str | None] = mapped_column(Text)  # Regex o texto clave
    soporta_uvr: Mapped[bool] = mapped_column(Boolean, server_default="true")
    soporta_frech: Mapped[bool] = mapped_column(Boolean, server_default="true")
    
    activo: Mapped[bool] = mapped_column(Boolean, server_default="true")
