"""
Documents Repository - Acceso a datos de documentos PDF
========================================================

CRUD para DocumentoS3 usando SQLAlchemy 2.0.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.models.documento import DocumentoS3


class DocumentsRepo:
    """Repositorio para operaciones CRUD de documentos."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CREATE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def create(
        self,
        usuario_id: uuid.UUID,
        original_filename: str,
        file_size: int,
        s3_key: str,
        checksum: str,
        pdf_encrypted: bool = False,
        banco_id: Optional[int] = None,
        mime_type: str = "application/pdf",
        status: str = "UPLOADED"
    ) -> DocumentoS3:
        """
        Crea un nuevo registro de documento.
        
        Args:
            usuario_id: ID del usuario propietario
            original_filename: Nombre original del archivo
            file_size: Tamaño en bytes
            s3_key: Ruta en S3 o filesystem local
            checksum: SHA-256 del archivo
            pdf_encrypted: Si el PDF original estaba encriptado
            banco_id: ID del banco detectado (opcional)
            mime_type: Tipo MIME del archivo
            status: Estado inicial del documento
            
        Returns:
            DocumentoS3 creado
        """
        documento = DocumentoS3(
            usuario_id=usuario_id,
            banco_id=banco_id,
            original_filename=original_filename,
            file_size=file_size,
            mime_type=mime_type,
            s3_key=s3_key,
            pdf_encrypted=pdf_encrypted,
            checksum_sha256=checksum,
            status=status
        )
        
        self.db.add(documento)
        self.db.commit()
        self.db.refresh(documento)
        
        return documento
    
    # ═══════════════════════════════════════════════════════════════════════════
    # READ
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_by_id(self, document_id: uuid.UUID) -> Optional[DocumentoS3]:
        """Obtiene un documento por su ID."""
        return self.db.execute(
            select(DocumentoS3).where(DocumentoS3.id == document_id)
        ).scalar_one_or_none()
    
    def get_by_id_and_user(
        self, 
        document_id: uuid.UUID, 
        usuario_id: uuid.UUID
    ) -> Optional[DocumentoS3]:
        """Obtiene un documento verificando que pertenece al usuario."""
        return self.db.execute(
            select(DocumentoS3).where(
                and_(
                    DocumentoS3.id == document_id,
                    DocumentoS3.usuario_id == usuario_id
                )
            )
        ).scalar_one_or_none()
    
    def get_by_checksum(self, checksum: str) -> Optional[DocumentoS3]:
        """Obtiene un documento por su checksum (para detectar duplicados)."""
        return self.db.execute(
            select(DocumentoS3).where(DocumentoS3.checksum_sha256 == checksum)
        ).scalar_one_or_none()
    
    def get_by_checksum_and_user(
        self, 
        checksum: str, 
        usuario_id: uuid.UUID
    ) -> Optional[DocumentoS3]:
        """Obtiene un documento por checksum y usuario (duplicados del mismo usuario)."""
        return self.db.execute(
            select(DocumentoS3).where(
                and_(
                    DocumentoS3.checksum_sha256 == checksum,
                    DocumentoS3.usuario_id == usuario_id
                )
            )
        ).scalar_one_or_none()
    
    def list_by_user(
        self, 
        usuario_id: uuid.UUID,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> list[DocumentoS3]:
        """
        Lista documentos de un usuario.
        
        Args:
            usuario_id: ID del usuario
            status: Filtrar por status (opcional)
            limit: Máximo de resultados
            offset: Offset para paginación
        """
        query = select(DocumentoS3).where(
            DocumentoS3.usuario_id == usuario_id
        )
        
        if status:
            query = query.where(DocumentoS3.status == status)
        
        query = query.order_by(DocumentoS3.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        return list(self.db.execute(query).scalars().all())
    
    def count_by_user(
        self, 
        usuario_id: uuid.UUID,
        status: Optional[str] = None
    ) -> int:
        """Cuenta documentos de un usuario."""
        from sqlalchemy import func
        
        query = select(func.count(DocumentoS3.id)).where(
            DocumentoS3.usuario_id == usuario_id
        )
        
        if status:
            query = query.where(DocumentoS3.status == status)
        
        return self.db.execute(query).scalar() or 0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # UPDATE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def update_status(
        self, 
        document_id: uuid.UUID, 
        status: str
    ) -> Optional[DocumentoS3]:
        """Actualiza el estado de un documento."""
        documento = self.get_by_id(document_id)
        if documento:
            documento.status = status
            self.db.commit()
            self.db.refresh(documento)
        return documento
    
    def update_banco(
        self, 
        document_id: uuid.UUID, 
        banco_id: int
    ) -> Optional[DocumentoS3]:
        """Actualiza el banco asociado a un documento."""
        documento = self.get_by_id(document_id)
        if documento:
            documento.banco_id = banco_id
            self.db.commit()
            self.db.refresh(documento)
        return documento
    
    def update(self, documento: DocumentoS3) -> DocumentoS3:
        """Guarda cambios en un documento."""
        self.db.commit()
        self.db.refresh(documento)
        return documento
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DELETE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def delete(self, document_id: uuid.UUID) -> bool:
        """Elimina un documento por ID."""
        documento = self.get_by_id(document_id)
        if documento:
            self.db.delete(documento)
            self.db.commit()
            return True
        return False
    
    def delete_by_user(
        self, 
        document_id: uuid.UUID, 
        usuario_id: uuid.UUID
    ) -> bool:
        """Elimina un documento verificando que pertenece al usuario."""
        documento = self.get_by_id_and_user(document_id, usuario_id)
        if documento:
            self.db.delete(documento)
            self.db.commit()
            return True
        return False
