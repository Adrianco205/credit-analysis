import uuid
from typing import Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import SessionLocal
from app.core.config import settings
from app.models.user import Usuario
from app.models.role import Role, UsuarioRole


security = HTTPBearer()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Usuario:
    """
    Decodifica el JWT del header Authorization, valida el usuario y retorna el Usuario activo.
    
    Raises:
        HTTPException 401: Si el token es inválido, expirado o el usuario no existe
        HTTPException 403: Si el usuario no está ACTIVE
    """
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        
        user_id = uuid.UUID(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception
    
    # Obtener usuario de la base de datos
    user = db.execute(
        select(Usuario).where(Usuario.id == user_id)
    ).scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    # Validar que el usuario esté activo
    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta no está activa. Verifica tu correo para activarla."
        )
    
    return user


def require_role(*allowed_roles: str) -> Callable:
    """
    Dependencia que verifica si el usuario actual tiene uno de los roles permitidos.
    
    Args:
        *allowed_roles: Códigos de roles permitidos (e.g., "CLIENT", "ADMIN")
    
    Returns:
        Función de dependencia que valida el rol del usuario
    
    Example:
        @router.get("/admin/dashboard", dependencies=[Depends(require_role("ADMIN"))])
        async def admin_dashboard():
            ...
    """
    def role_checker(
        current_user: Usuario = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> Usuario:
        # Obtener los roles del usuario
        user_roles = db.execute(
            select(Role.code)
            .join(UsuarioRole, UsuarioRole.role_id == Role.id)
            .where(UsuarioRole.user_id == current_user.id)
        ).scalars().all()
        
        # Verificar si tiene alguno de los roles permitidos
        if not any(role in allowed_roles for role in user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No tienes permisos suficientes. Se requiere uno de estos roles: {', '.join(allowed_roles)}"
            )
        
        return current_user
    
    return role_checker
