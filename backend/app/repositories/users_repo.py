import uuid  # <--- ESTA ES LA LÍNEA QUE FALTABA
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.user import Usuario
from app.models.role import Role, UsuarioRole

class UsersRepo:
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> Usuario | None:
        return self.db.execute(select(Usuario).where(Usuario.email == email)).scalar_one_or_none()

    def get_by_identificacion(self, identificacion: str) -> Usuario | None:
        return self.db.execute(select(Usuario).where(Usuario.identificacion == identificacion)).scalar_one_or_none()

    def get_by_id(self, user_id) -> Usuario | None:
        return self.db.execute(select(Usuario).where(Usuario.id == user_id)).scalar_one_or_none()

    def create_user(self, user: Usuario) -> Usuario:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def ensure_role_assignment(self, user_id, role_code: str):
        role = self.db.execute(select(Role).where(Role.code == role_code)).scalar_one_or_none()
        if not role:
            raise ValueError(f"Role {role_code} no existe (seed roles).")

        exists = self.db.execute(
            select(UsuarioRole).where(UsuarioRole.user_id == user_id, UsuarioRole.role_id == role.id)
        ).scalar_one_or_none()

        if not exists:
            self.db.add(UsuarioRole(user_id=user_id, role_id=role.id))
            self.db.commit()

    # Función añadida para el flujo de re-intento de registro
    def update_pending_user(self, user_id: uuid.UUID, **kwargs) -> Usuario:
        user = self.get_by_id(user_id)
        if user and user.status == "PENDING":
            for key, value in kwargs.items():
                setattr(user, key, value)
            self.db.commit()
            self.db.refresh(user)
        return user