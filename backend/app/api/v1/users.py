"""
Endpoints de Usuario - Dashboard y Perfil.

Incluye:
- Perfil completo del usuario (con rol, ciudad, tipo identificación)
- Actualización de perfil (teléfono, ciudad)
- Cambio de contraseña
- Gestión de referencias personales/familiares
- Historial de estudios/análisis
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.security import hash_password, verify_password
from app.models.user import Usuario
from app.models.role import UsuarioRole, Role
from app.models.location import Ciudad, Departamento
from app.models.analisis import AnalisisHipotecario
from app.models.documento import DocumentoS3
from app.models.banco import Banco
from app.models.referencia import ReferenciaUsuario
from app.repositories.referencias_repo import ReferenciasRepo
from app.schemas.user import (
    UserProfileResponse,
    UpdatePasswordRequest,
    UpdateProfileRequest,
    ReferenciaCreate,
    ReferenciaUpdate,
    ReferenciaResponse,
    ReferenciasListResponse,
    EstudioHistorialItem,
    EstudiosHistorialResponse,
)

router = APIRouter()


# ==========================================
# PERFIL DE USUARIO
# ==========================================

@router.get("/me", response_model=UserProfileResponse)
def get_my_profile(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene el perfil completo del usuario autenticado.
    
    Retorna información completa incluyendo:
    - Datos personales (nombre, cédula, tipo identificación, género)
    - Datos de contacto (email, teléfono)
    - Ubicación (ciudad, departamento)
    - Rol del usuario (ADMIN, CLIENT)
    """
    # Obtener ciudad y departamento
    ciudad_nombre = None
    departamento_nombre = None
    if current_user.ciudad_id:
        stmt = select(Ciudad, Departamento).join(
            Departamento, Ciudad.departamento_id == Departamento.id
        ).where(Ciudad.id == current_user.ciudad_id)
        result = db.execute(stmt).first()
        if result:
            ciudad_nombre = result[0].nombre
            departamento_nombre = result[1].nombre

    # Obtener rol del usuario
    rol = None
    stmt = select(Role.code).join(
        UsuarioRole, UsuarioRole.role_id == Role.id
    ).where(UsuarioRole.user_id == current_user.id)
    role_result = db.execute(stmt).scalar_one_or_none()
    if role_result:
        rol = role_result

    return UserProfileResponse(
        id=str(current_user.id),
        identificacion=current_user.identificacion or "",
        tipo_identificacion=current_user.tipo_identificacion,
        nombres=current_user.nombres or "",
        primer_apellido=current_user.primer_apellido or "",
        segundo_apellido=current_user.segundo_apellido,
        genero=current_user.genero,
        email=current_user.email or "",
        telefono=current_user.telefono,
        status=current_user.status,
        email_verificado=current_user.email_verificado,
        ciudad_id=current_user.ciudad_id,
        ciudad_nombre=ciudad_nombre,
        departamento_nombre=departamento_nombre,
        rol=rol
    )


@router.patch("/me", response_model=UserProfileResponse)
def update_my_profile(
    payload: UpdateProfileRequest,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Actualiza el perfil del usuario autenticado.
    
    Permite actualizar:
    - Teléfono
    - Ciudad
    """
    # Validar ciudad si se proporciona
    if payload.ciudad_id is not None:
        stmt = select(Ciudad).where(Ciudad.id == payload.ciudad_id)
        ciudad = db.execute(stmt).scalar_one_or_none()
        if not ciudad:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La ciudad seleccionada no existe"
            )
        current_user.ciudad_id = payload.ciudad_id

    # Actualizar teléfono si se proporciona
    if payload.telefono is not None:
        current_user.telefono = payload.telefono

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    # Retornar perfil actualizado
    return get_my_profile(current_user, db)


@router.patch("/me/password")
def update_password(
    payload: UpdatePasswordRequest,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Actualiza la contraseña del usuario autenticado.
    
    Requiere proporcionar la contraseña actual para verificar identidad.
    """
    # Verificar contraseña actual
    if not current_user.password_hash or not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta"
        )
    
    # Validar que la nueva contraseña sea diferente
    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nueva contraseña debe ser diferente a la actual"
        )
    
    # Actualizar contraseña
    current_user.password_hash = hash_password(payload.new_password)
    db.add(current_user)
    db.commit()
    
    return {
        "message": "Contraseña actualizada exitosamente"
    }


# ==========================================
# REFERENCIAS DEL USUARIO
# ==========================================

@router.get("/me/referencias", response_model=ReferenciasListResponse)
def get_my_referencias(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene las referencias personales y familiares del usuario.
    
    Cada usuario puede tener máximo una referencia familiar y una personal.
    """
    repo = ReferenciasRepo(db)
    referencias = repo.get_by_usuario(current_user.id)
    
    familiar = None
    personal = None
    
    for ref in referencias:
        ref_response = ReferenciaResponse(
            id=str(ref.id),
            tipo_referencia=ref.tipo_referencia,
            nombre_completo=ref.nombre_completo,
            celular=ref.celular,
            parentesco=ref.parentesco,
            created_at=ref.created_at
        )
        if ref.tipo_referencia == "FAMILIAR":
            familiar = ref_response
        elif ref.tipo_referencia == "PERSONAL":
            personal = ref_response
    
    return ReferenciasListResponse(familiar=familiar, personal=personal)


@router.post("/me/referencias", response_model=ReferenciaResponse, status_code=status.HTTP_201_CREATED)
def create_referencia(
    payload: ReferenciaCreate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Crea una referencia para el usuario.
    
    Solo puede existir una referencia por tipo (FAMILIAR o PERSONAL).
    Si ya existe una del mismo tipo, se debe usar PUT para actualizar.
    """
    repo = ReferenciasRepo(db)
    
    # Verificar si ya existe una referencia del mismo tipo
    existing = repo.get_by_usuario_y_tipo(current_user.id, payload.tipo_referencia)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una referencia de tipo {payload.tipo_referencia}. Use PUT para actualizarla."
        )
    
    # Validar parentesco para referencias familiares
    if payload.tipo_referencia == "FAMILIAR" and not payload.parentesco:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El parentesco es obligatorio para referencias familiares"
        )
    
    # Crear referencia
    referencia = repo.create(
        usuario_id=current_user.id,
        tipo_referencia=payload.tipo_referencia,
        nombre_completo=payload.nombre_completo,
        celular=payload.celular,
        parentesco=payload.parentesco if payload.tipo_referencia == "FAMILIAR" else None
    )
    
    return ReferenciaResponse(
        id=str(referencia.id),
        tipo_referencia=referencia.tipo_referencia,
        nombre_completo=referencia.nombre_completo,
        celular=referencia.celular,
        parentesco=referencia.parentesco,
        created_at=referencia.created_at
    )


@router.put("/me/referencias/{referencia_id}", response_model=ReferenciaResponse)
def update_referencia(
    referencia_id: UUID,
    payload: ReferenciaUpdate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Actualiza una referencia existente del usuario.
    """
    repo = ReferenciasRepo(db)
    
    # Obtener referencia y verificar propiedad
    referencia = repo.get_by_id(referencia_id)
    if not referencia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referencia no encontrada"
        )
    
    if referencia.usuario_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para modificar esta referencia"
        )
    
    # Actualizar referencia
    referencia = repo.update(
        referencia,
        nombre_completo=payload.nombre_completo,
        celular=payload.celular,
        parentesco=payload.parentesco
    )
    
    return ReferenciaResponse(
        id=str(referencia.id),
        tipo_referencia=referencia.tipo_referencia,
        nombre_completo=referencia.nombre_completo,
        celular=referencia.celular,
        parentesco=referencia.parentesco,
        created_at=referencia.created_at
    )


@router.delete("/me/referencias/{referencia_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_referencia(
    referencia_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Elimina una referencia del usuario.
    """
    repo = ReferenciasRepo(db)
    
    # Obtener referencia y verificar propiedad
    referencia = repo.get_by_id(referencia_id)
    if not referencia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referencia no encontrada"
        )
    
    if referencia.usuario_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para eliminar esta referencia"
        )
    
    repo.delete(referencia_id)
    return None


# ==========================================
# HISTORIAL DE ESTUDIOS/ANÁLISIS
# ==========================================

@router.get("/me/estudios", response_model=EstudiosHistorialResponse)
def get_my_estudios(
    page: int = 1,
    limit: int = 10,
    status: str | None = None,
    banco_id: int | None = None,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene el historial de estudios/análisis del usuario con paginación.
    
    Parámetros de paginación:
    - page: Número de página (default: 1)
    - limit: Cantidad por página (default: 10, max: 50)
    
    Filtros opcionales:
    - status: Filtrar por estado (PENDING, PROCESSING, COMPLETED, ERROR, ID_MISMATCH, etc.)
    - banco_id: Filtrar por ID del banco
    
    Retorna:
    - ID del documento subido
    - Nombre del banco
    - Fecha de subida
    - Estado del análisis
    - Saldo actual del crédito
    - Número de crédito
    """
    # Validar límites
    if page < 1:
        page = 1
    if limit < 1:
        limit = 10
    if limit > 50:
        limit = 50
    
    # Query base
    base_query = (
        select(AnalisisHipotecario)
        .where(AnalisisHipotecario.usuario_id == current_user.id)
    )
    
    # Aplicar filtros
    if status:
        base_query = base_query.where(AnalisisHipotecario.status == status)
    if banco_id:
        base_query = base_query.where(AnalisisHipotecario.banco_id == banco_id)
    
    # Contar total
    from sqlalchemy import func
    count_stmt = select(func.count()).select_from(base_query.subquery())
    total = db.execute(count_stmt).scalar() or 0
    
    # Calcular paginación
    total_pages = (total + limit - 1) // limit if total > 0 else 1
    offset = (page - 1) * limit
    
    # Query con joins y paginación
    stmt = (
        select(
            AnalisisHipotecario,
            DocumentoS3,
            Banco.nombre.label("banco_nombre")
        )
        .outerjoin(DocumentoS3, AnalisisHipotecario.documento_id == DocumentoS3.id)
        .outerjoin(Banco, AnalisisHipotecario.banco_id == Banco.id)
        .where(AnalisisHipotecario.usuario_id == current_user.id)
    )
    
    # Aplicar mismos filtros
    if status:
        stmt = stmt.where(AnalisisHipotecario.status == status)
    if banco_id:
        stmt = stmt.where(AnalisisHipotecario.banco_id == banco_id)
    
    # Ordenar y paginar
    stmt = stmt.order_by(AnalisisHipotecario.created_at.desc()).offset(offset).limit(limit)
    
    results = db.execute(stmt).all()
    
    estudios = []
    for row in results:
        analisis = row[0]
        documento = row[1]
        banco_nombre = row[2]
        
        estudios.append(EstudioHistorialItem(
            analisis_id=str(analisis.id),
            documento_id=str(documento.id) if documento else None,
            banco_nombre=banco_nombre,
            fecha_subida=documento.created_at if documento else analisis.created_at,
            status=analisis.status,
            saldo_actual=float(analisis.saldo_actual) if analisis.saldo_actual else None,
            numero_credito=analisis.numero_credito
        ))
    
    return EstudiosHistorialResponse(
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
        estudios=estudios
    )

