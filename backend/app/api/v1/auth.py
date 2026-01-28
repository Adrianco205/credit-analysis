import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.deps import get_db
from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import Usuario
from app.models.otp import VerificacionOTP
from app.repositories.users_repo import UsersRepo
from app.repositories.otp_repo import OtpRepo
from app.services.email_otp_service import EmailOtpService
from app.schemas.auth import (
    RegisterRequest,
    RegisterResponse,
    VerifyOtpRequest,
    LoginRequest,
    TokenResponse,
)

router = APIRouter()



@router.post("/register", response_model=dict)
def register(
    payload: RegisterRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Registra un nuevo usuario y envía código OTP por email.
    
    - Si el usuario ya existe y está ACTIVE, devuelve error 409
    - Si existe pero está PENDING, reutiliza el registro y actualiza datos
    - El envío de email se ejecuta en background para no bloquear la respuesta
    """
    users = UsersRepo(db)
    
    try:
        # 1. Buscar si el usuario ya existe (por email o identificación)
        existing_user = users.get_by_email(str(payload.email)) or \
                        users.get_by_identificacion(payload.identificacion)

        if existing_user:
            # Si ya está activo, lanzamos el error de conflicto
            if existing_user.status == "ACTIVE":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, 
                    detail="El usuario ya se encuentra registrado y activo."
                )
            
            # SI ESTÁ PENDING: Lo reutilizamos. Actualizamos sus datos por si cambió algo.
            user = existing_user
            user.nombres = payload.nombres
            user.primer_apellido = payload.primer_apellido
            user.segundo_apellido = payload.segundo_apellido
            user.password_hash = hash_password(payload.password)
            user.telefono = payload.telefono
            user.ciudad_id = payload.ciudad_id
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # SI NO EXISTE: Creamos el nuevo registro
            user = Usuario(
                nombres=payload.nombres,
                primer_apellido=payload.primer_apellido,
                segundo_apellido=payload.segundo_apellido,
                tipo_identificacion=payload.tipo_identificacion,
                identificacion=payload.identificacion,
                email=str(payload.email),
                telefono=payload.telefono,
                genero=payload.genero,
                password_hash=hash_password(payload.password),
                ciudad_id=payload.ciudad_id,
                status="PENDING",
                email_verificado=False,
            )
            user = users.create_user(user)
            # Asignar rol por primera vez
            users.ensure_role_assignment(user.id, "CLIENT")

        # 2. Lógica de OTP (Se genera uno nuevo independientemente de si es nuevo o re-intento)
        code = f"{secrets.randbelow(1_000_000):06d}"
        expires = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

        otp_repo = OtpRepo(db)
        otp = VerificacionOTP(
            user_id=user.id,
            code_hash=hash_password(code),
            tipo="EMAIL",
            status="PENDING",
            expires_at=expires,
            used_at=None,
        )
        otp_repo.create(otp)

        # 3. Enviar email en background (no bloqueante)
        background_tasks.add_task(
            EmailOtpService.send_otp,
            to_email=str(payload.email),
            code=code
        )

        return RegisterResponse(
            user_id=str(user.id),
            status=user.status,
            message="Código de verificación enviado. Revisa tu correo para activar tu cuenta.",
        ).model_dump()
    
    except IntegrityError as e:
        db.rollback()
        # Manejar violación de constraints (email/identificación duplicada)
        if "email" in str(e.orig):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El correo electrónico ya está registrado"
            )
        elif "identificacion" in str(e.orig):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El número de identificación ya está registrado"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al crear el usuario. Intenta nuevamente."
            )


@router.post("/verify-otp", response_model=dict)
def verify_otp(payload: VerifyOtpRequest, db: Session = Depends(get_db)):
    users = UsersRepo(db)
    otp_repo = OtpRepo(db)

    try:
        user_id = uuid.UUID(payload.user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de usuario no válido.")

    user = users.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="El usuario no existe.")

    # Obtenemos el último OTP pendiente
    otp = otp_repo.get_pending(user_id=user.id, tipo="EMAIL")
    if not otp:
        raise HTTPException(status_code=400, detail="No tienes códigos de verificación pendientes.")

    now = datetime.now(timezone.utc)

    # Verificar expiración
    if otp.expires_at and now > otp.expires_at:
        otp.status = "EXPIRED"
        db.add(otp)
        db.commit()
        raise HTTPException(status_code=400, detail="El código ha expirado. Regístrate de nuevo para recibir uno nuevo.")

    # Verificar validez del código
    if not verify_password(payload.code, otp.code_hash):
        raise HTTPException(status_code=400, detail="Código incorrecto.")

    # Marcar como verificado y activar usuario
    otp.status = "VERIFIED"
    otp.used_at = now
    db.add(otp)

    user.email_verificado = True
    user.status = "ACTIVE"
    db.add(user)
    
    db.commit()
    db.refresh(user)

    return {"message": "¡Cuenta activada con éxito! Ya puedes iniciar sesión.", "status": user.status}


@router.post("/login", response_model=dict)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    users = UsersRepo(db)
    user = users.get_by_identificacion(payload.identificacion)

    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Cédula o contraseña incorrectas.")

    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta aún no está activa. Por favor verifica tu correo con el código OTP."
        )

    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token).model_dump()