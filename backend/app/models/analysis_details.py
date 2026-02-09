"""
Modelos para datos detallados de análisis hipotecario.
Incluye: Movimientos, Tasas, y datos UVR.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import String, Numeric, Date, DateTime, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class AnalysisMovement(Base):
    """
    Movimientos del período extraídos de la tabla del PDF.
    Cada fila representa un componente del pago (capital, interés, seguros, etc.)
    """
    __tablename__ = "analysis_movements"
    __table_args__ = (
        Index("ix_movements_analisis", "analisis_id"),
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
    
    # Datos del movimiento
    fecha_aplicacion: Mapped[date | None] = mapped_column(Date)
    descripcion: Mapped[str | None] = mapped_column(String(200))
    
    # Componentes monetarios
    capital: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    interes_corriente: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    interes_mora: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    seguro_vida: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    seguro_incendio: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    seguro_terremoto: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    otros_cargos: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    total: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    
    # Metadata de extracción (página, label, confianza)
    source_meta: Mapped[dict | None] = mapped_column(JSONB)
    
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
        server_default=text("now()")
    )


class AnalysisRates(Base):
    """
    Tasas de interés extraídas del PDF.
    Relación 1:1 con análisis.
    """
    __tablename__ = "analysis_rates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=text("gen_random_uuid()")
    )
    analisis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analisis_hipotecario.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )
    
    # Tasas (como decimal: 12.45% = 0.1245)
    tasa_pactada_ea: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    tasa_cobrada_ea: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    tasa_subsidiada_ea: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    tasa_mora_pactada_ea: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    tasa_mora_cobrada_ea: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    
    # Metadata de extracción
    source_meta: Mapped[dict | None] = mapped_column(JSONB)
    
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
        server_default=text("now()")
    )


class AnalysisUVR(Base):
    """
    Datos UVR extraídos del PDF.
    Solo aplica para créditos en sistema UVR.
    Relación 1:1 con análisis.
    """
    __tablename__ = "analysis_uvr"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=text("gen_random_uuid()")
    )
    analisis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analisis_hipotecario.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )
    
    # Valor UVR a la fecha del extracto
    valor_uvr: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    fecha_uvr: Mapped[date | None] = mapped_column(Date)
    
    # Saldos y movimientos en UVR
    saldo_capital_uvr: Mapped[Decimal | None] = mapped_column(Numeric(15, 4))
    movimiento_capital_uvr: Mapped[Decimal | None] = mapped_column(Numeric(15, 4))
    movimiento_interes_uvr: Mapped[Decimal | None] = mapped_column(Numeric(15, 4))
    valor_cuota_uvr: Mapped[Decimal | None] = mapped_column(Numeric(15, 4))
    
    # Metadata de extracción
    source_meta: Mapped[dict | None] = mapped_column(JSONB)
    
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
        server_default=text("now()")
    )
