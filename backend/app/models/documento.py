import uuid
from datetime import datetime
from sqlalchemy import String, BigInteger, Boolean, DateTime, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class DocumentoS3(Base):
    """
    Modelo para documentos PDF almacenados en S3 (o localmente).
    Almacena metadata del archivo y su estado de procesamiento.
    """
    __tablename__ = "documentos_s3"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=text("gen_random_uuid()")
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("usuarios.id", ondelete="CASCADE"), 
        nullable=False
    )
    banco_id: Mapped[int | None] = mapped_column(
        ForeignKey("bancos.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Metadata del archivo
    s3_key: Mapped[str | None] = mapped_column(Text, nullable=True)  # Ruta en S3 o filesystem
    original_filename: Mapped[str | None] = mapped_column(String(255))
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    mime_type: Mapped[str | None] = mapped_column(String(50))
    
    # Seguridad y validación
    pdf_encrypted: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))  # Hash del archivo
    
    # Estado del procesamiento
    status: Mapped[str] = mapped_column(
        String(20), 
        server_default=text("'UPLOADED'")
    )  # UPLOADED, PROCESSING, COMPLETED, FAILED
    
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
        server_default=text("now()")
    )
