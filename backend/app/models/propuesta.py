import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Integer, Numeric, ForeignKey, DateTime, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class PropuestaAhorro(Base):
    """
    Modelo para propuestas de ahorro (nuevas oportunidades).
    Cada análisis puede tener múltiples opciones de abono adicional.
    Las 3 opciones son definidas por el usuario según su capacidad de pago.
    """
    __tablename__ = "propuestas_ahorro"
    __table_args__ = (
        Index("ix_propuesta_analisis_opcion", "analisis_id", "numero_opcion"),
    )

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
    
    # ═══════════════════════════════════════════════════════════════════
    # IDENTIFICACIÓN DE LA OPCIÓN
    # ═══════════════════════════════════════════════════════════════════
    numero_opcion: Mapped[int] = mapped_column(Integer)  # 1, 2, 3
    nombre_opcion: Mapped[str | None] = mapped_column(String(50))  # "1a Elección", "2a Elección", etc.
    
    # ═══════════════════════════════════════════════════════════════════
    # DATOS DE ENTRADA (Definidos por usuario/admin)
    # ═══════════════════════════════════════════════════════════════════
    abono_adicional_mensual: Mapped[Decimal] = mapped_column(Numeric(15, 2))  # Lo que el usuario aporta extra
    
    # ═══════════════════════════════════════════════════════════════════
    # RESULTADOS CALCULADOS - TIEMPO
    # ═══════════════════════════════════════════════════════════════════
    cuotas_nuevas: Mapped[int | None] = mapped_column(Integer)  # 140, 128, 116
    tiempo_restante_anios: Mapped[int | None] = mapped_column(Integer)  # 11, 10, 9
    tiempo_restante_meses: Mapped[int | None] = mapped_column(Integer)  # 8, 8, 8 (adicional a años)
    
    cuotas_reducidas: Mapped[int | None] = mapped_column(Integer)  # Cuotas ahorradas vs actual
    tiempo_ahorrado_anios: Mapped[int | None] = mapped_column(Integer)  # 16, 17, 18
    tiempo_ahorrado_meses: Mapped[int | None] = mapped_column(Integer)
    
    # ═══════════════════════════════════════════════════════════════════
    # RESULTADOS CALCULADOS - DINERO
    # ═══════════════════════════════════════════════════════════════════
    nuevo_valor_cuota: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))  # Cuota actual + abono
    total_por_pagar_aprox: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))  # $106,086,696
    valor_ahorrado_intereses: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))  # $142,349,052
    
    # Veces que se paga el valor prestado inicial
    veces_pagado: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))  # 1.95, 1.83, 1.72
    
    # ═══════════════════════════════════════════════════════════════════
    # HONORARIOS Y REQUISITOS
    # ═══════════════════════════════════════════════════════════════════
    honorarios_calculados: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))  # 3% del ahorro
    honorarios_con_iva: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))  # Honorarios + 19% IVA
    ingreso_minimo_requerido: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))  # 30% de nueva cuota
    
    # ═══════════════════════════════════════════════════════════════════
    # METADATA
    # ═══════════════════════════════════════════════════════════════════
    origen: Mapped[str] = mapped_column(
        String(20), 
        server_default=text("'USER'")
    )  # USER (propuesta inicial), ADMIN (ajustada)
    es_opcion_seleccionada: Mapped[bool | None] = mapped_column(default=False)  # La que eligió el cliente
    
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=text("now()"))
