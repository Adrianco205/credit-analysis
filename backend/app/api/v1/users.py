from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_role
from app.core.security import hash_password, verify_password
from app.models.user import Usuario
from app.schemas.user import UserProfileResponse, UpdatePasswordRequest

router = APIRouter()


@router.get("/me", response_model=UserProfileResponse)
def get_my_profile(current_user: Usuario = Depends(get_current_user)):
    """
    Obtiene el perfil del usuario autenticado.
    
    Retorna información básica: cédula, nombre completo, género, email.
    """
    return UserProfileResponse(
        id=str(current_user.id),
        identificacion=current_user.identificacion or "",
        nombres=current_user.nombres or "",
        primer_apellido=current_user.primer_apellido or "",
        segundo_apellido=current_user.segundo_apellido,
        genero=current_user.genero,
        email=current_user.email or "",
        telefono=current_user.telefono,
        status=current_user.status,
        email_verificado=current_user.email_verificado
    )


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
