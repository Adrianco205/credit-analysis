from types import SimpleNamespace
from uuid import uuid4
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[2]))
os.chdir(Path(__file__).resolve().parent)

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/test_db")
os.environ.setdefault("SECRET_KEY", "12345678901234567890123456789012")
os.environ.setdefault("SMTP_HOST", "smtp.test.local")
os.environ.setdefault("SMTP_USER", "user@test.local")
os.environ.setdefault("SMTP_PASSWORD", "secret")
os.environ.setdefault("SMTP_FROM_EMAIL", "noreply@test.local")

from app.main import app
from app.api import deps
from app.api.v1 import auth as auth_module


class DummySession:
	def add(self, _obj):
		return None

	def commit(self):
		return None

	def refresh(self, _obj):
		return None

	def rollback(self):
		return None


def test_register_claims_invited_user(monkeypatch):
	captured = {"otp_created": 0, "otp_emails": 0}

	invited_user = SimpleNamespace(
		id=uuid4(),
		nombres="Cliente",
		primer_apellido="Invitado",
		segundo_apellido=None,
		tipo_identificacion="CC",
		identificacion="1234567890",
		email="cliente.invited@example.com",
		telefono="3001234567",
		genero=None,
		ciudad_departamento=None,
		status="INVITED",
		email_verificado=False,
		password_hash=None,
	)

	class FakeUsersRepo:
		def __init__(self, db):
			self.db = db

		def get_by_email(self, email: str):
			if email == invited_user.email:
				return invited_user
			return None

		def get_by_identificacion(self, identificacion: str):
			if identificacion == invited_user.identificacion:
				return invited_user
			return None

		def create_user(self, user):
			return user

		def ensure_role_assignment(self, user_id, role_code: str):
			captured["role_assignment"] = (str(user_id), role_code)

	class FakeOtpRepo:
		def __init__(self, db):
			self.db = db

		def create(self, otp):
			captured["otp_created"] += 1
			captured["otp_user_id"] = str(otp.user_id)
			return otp

	class FakeEmailOtpService:
		@staticmethod
		def send_otp(to_email: str, code: str):
			captured["otp_emails"] += 1
			captured["otp_email"] = to_email
			captured["otp_code_len"] = len(code)

	monkeypatch.setattr(auth_module, "UsersRepo", FakeUsersRepo)
	monkeypatch.setattr(auth_module, "OtpRepo", FakeOtpRepo)
	monkeypatch.setattr(auth_module, "EmailOtpService", FakeEmailOtpService)
	monkeypatch.setattr(auth_module, "hash_password", lambda raw: f"hashed::{raw}")

	app.dependency_overrides[deps.get_db] = lambda: DummySession()
	app.dependency_overrides[auth_module.get_db] = lambda: DummySession()

	client = TestClient(app)

	response = client.post(
		"/api/v1/auth/register",
		json={
			"nombres": "Cliente",
			"primer_apellido": "Final",
			"segundo_apellido": "Prueba",
			"tipo_identificacion": "CC",
			"identificacion": "1234567890",
			"email": "cliente.invited@example.com",
			"telefono": "3000000000",
			"genero": "F",
			"password": "ClaveSegura123",
			"ciudad_departamento": "Bogotá",
		},
	)

	assert response.status_code == 200
	body = response.json()
	assert body["status"] == "PENDING"
	assert body["user_id"] == str(invited_user.id)

	assert invited_user.status == "PENDING"
	assert invited_user.email_verificado is False
	assert invited_user.password_hash is not None
	assert invited_user.primer_apellido == "Final"
	assert invited_user.telefono == "3000000000"
	assert invited_user.genero == "F"
	assert invited_user.ciudad_departamento == "Bogotá"

	assert captured["otp_created"] == 1
	assert captured["otp_user_id"] == str(invited_user.id)
	assert captured["otp_emails"] == 1
	assert captured["otp_email"] == "cliente.invited@example.com"
	assert captured["otp_code_len"] == 6

	app.dependency_overrides = {}
