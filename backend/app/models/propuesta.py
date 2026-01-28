import uuid
from decimal import Decimal
from sqlalchemy import String, Integer, Numeric, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class PropuestaAhorro(Base):
    """
    Modelo para propuestas de ahorro (nuevas oportunidades).
    Cada análisis puede tener múltiples opciones de abono adicional.
    """
    __tablename__ = "propuestas_ahorro"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=text("gen_random_uuid()")
    )
    analisis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analisis_hipotecario.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Identificador de la opción (1ra, 2da, 3ra elección)
    numero_opcion: Mapped[int] = mapped_column(Integer)  # 1, 2, 3, etc.
    
    # Abono adicional propuesto
    abono_adicional: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    
    # Resultados calculados
    cuotas_reducidas: Mapped[int | None] = mapped_column(Integer)
    tiempo_ahorrado_meses: Mapped[int | None] = mapped_column(Integer)
    valor_ahorrado_intereses: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    nuevo_valor_cuota: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    total_por_pagar_aprox: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    
    # Honorarios y requisitos
    honorarios_calculados: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    ingreso_minimo_requerido: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    
    # Metadata
    origen: Mapped[str] = mapped_column(String(20), server_default=text("'USER'"))  # USER, ADMIN
