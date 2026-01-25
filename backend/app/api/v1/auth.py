import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import Usuario
from app.models.otp import VerificacionOTP
from app.repositories.users_repo import UsersRepo
from app.repositories.otp_repo import OtpRepo
from app.services.email_otp_service import EmailOtpService

router = APIRouter()


@router.post("/register", response_model=dict)
def register(payload, db: Session = Depends(get_db)):
    # Pydantic manual import (para evitar circular en este snippet)
    from app.schemas.auth import RegisterRequest, RegisterResponse

    data = RegisterRequest(**payload) if isinstance(payload, dict) else payload
    users = UsersRepo(db)

    if users.get_by_email(str(data.email)):
        raise HTTPException(status_code=409, detail="El email ya está registrado.")
    if users.get_by_identificacion(data.identificacion):
        raise HTTPException(status_code=409, detail="La identificación ya está registrada.")

    user = Usuario(
        nombres=data.nombres,
        primer_apellido=data.primer_apellido,
        segundo_apellido=data.segundo_apellido,
        tipo_identificacion=data.tipo_identificacion,
        identificacion=data.identificacion,
        email=str(data.email),
        telefono=data.telefono,
        genero=data.genero,
        password_hash=hash_password(data.password),
        ciudad_id=data.ciudad_id,
        status="PENDING",
        email_verificado=False,
    )

    user = users.create_user(user)
    users.ensure_role_assignment(user.id, "CLIENT")

    # Crear OTP
    code = f"{secrets.randbelow(1000000):06d}"
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

    # Enviar email
    try:
        EmailOtpService().send_otp(to_email=str(data.email), code=code)
    except Exception:
        # No reveles detalles internos
        raise HTTPException(status_code=500, detail="No se pudo enviar el OTP al correo.")

    return RegisterResponse(
        user_id=str(user.id),
        status=user.status,
        message="Usuario creado en estado PENDING. Verifica el OTP enviado al correo para activar tu cuenta.",
    ).model_dump()


@router.post("/verify-otp", response_model=dict)
def verify_otp(payload, db: Session = Depends(get_db)):
    from app.schemas.auth import VerifyOtpRequest

    data = VerifyOtpRequest(**payload) if isinstance(payload, dict) else payload

    users = UsersRepo(db)
    otp_repo = OtpRepo(db)

    try:
        import uuid
        user_id = uuid.UUID(data.user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="user_id inválido.")

    user = users.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no existe.")

    otp = otp_repo.get_pending(user_id=user.id, tipo="EMAIL")
    if not otp:
        raise HTTPException(status_code=400, detail="No hay OTP pendiente para este usuario.")

    now = datetime.now(timezone.utc)
    if otp.expires_at and now > otp.expires_at:
        otp.status = "EXPIRED"
        otp_repo.save(otp)
        raise HTTPException(status_code=400, detail="OTP expirado. Solicita uno nuevo.")

    if not otp.code_hash or not verify_password(data.code, otp.code_hash):
        raise HTTPException(status_code=400, detail="OTP incorrecto.")

    otp.status = "VERIFIED"
    otp.used_at = now
    otp_repo.save(otp)

    user.email_verificado = True
    user.status = "ACTIVE"
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "Cuenta verificada. Ya puedes iniciar sesión.", "status": user.status}


@router.post("/login", response_model=dict)
def login(payload, db: Session = Depends(get_db)):
    from app.schemas.auth import LoginRequest, TokenResponse

    data = LoginRequest(**payload) if isinstance(payload, dict) else payload

    users = UsersRepo(db)
    user = users.get_by_identificacion(data.identificacion)

    if not user or not user.password_hash or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas.")

    if user.status != "ACTIVE" or not user.email_verificado:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta no activa. Verifica tu correo con OTP.",
        )

    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token).model_dump()
