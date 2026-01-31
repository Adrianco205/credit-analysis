# 🤖 EcoFinanzas - AI Coding Agent Instructions

## Project Overview
**EcoFinanzas** is a mortgage credit analysis platform with AI-powered insights. Full-stack: FastAPI backend (Python) + Next.js frontend (TypeScript) + PostgreSQL database.

---

## 🏗️ Architecture Essentials

### Backend (FastAPI)
- **Location**: `backend/app/`
- **Core Pattern**: Layered architecture (Routers → Services → Repositories → Models)
- **Key Stack**: FastAPI 0.115, SQLAlchemy 2.0, PostgreSQL 16, JWT auth, APScheduler for background jobs
- **Database Access**: Custom `Session` dependency injected via `Depends(get_db)` in endpoints
  - Repositories pattern: `UsersRepo`, `OtpRepo`, etc. in `repositories/`
  - Models use SQLAlchemy 2.0 with `Mapped` types: [user.py](backend/app/models/user.py), [analisis.py](backend/app/models/analisis.py)

### Frontend (Next.js)
- **Location**: `frontend/app/`
- **Design System**: Green eco-palette (see [DESIGN_SYSTEM.md](frontend/DESIGN_SYSTEM.md))
  - 29 CSS variables in [globals.css](frontend/app/globals.css)
  - Custom components: [Button](frontend/components/ui/button.tsx), [Input](frontend/components/ui/input.tsx), [Card](frontend/components/ui/card.tsx)
- **API Communication**: Proxy through next.config.ts rewrites to `/api/v1`

### Data Flow
1. Frontend → POST/GET to `/api/v1/*` (proxied to backend via `next.config.ts`)
2. Backend validates with Pydantic schemas, processes, accesses DB via repos
3. Background jobs run via APScheduler (e.g., cleanup PENDING users every 10 mins)

---

## 🔑 Critical Workflows

### Local Development (Docker)
```bash
cd project-root/
docker compose up -d --build   # Spins up: postgres(5434), backend(8001), frontend(3000)
docker compose logs -f         # Monitor all services
docker compose down -v         # Reset database
```

### API Testing
- **Swagger UI**: http://localhost:8001/docs
- **Frontend**: http://localhost:3000
- **Auth Flow**: Register → OTP verification → Login → Dashboard

### Database Management
- **Migrations**: Alembic setup ready but versions/ currently empty
- **Init Script**: `docker/postgres/init.sql` seeds roles table
- **Session Pattern**: Always use `Depends(get_db)` for database access, never create sessions manually

### Python Environment
- Python 3.11+ required
- Virtual environment: `backend/venv`
- Test files: `backend/app/tests/` (conftest.py, test_auth.py, test_admin_filters.py, test_upload.py)

---

## 📋 Project-Specific Patterns

### Authentication & Authorization
- **JWT-based**: `create_access_token()` in [security.py](backend/app/core/security.py)
- **Current User**: `get_current_user()` dependency in [deps.py](backend/app/api/deps.py) validates Bearer token
- **Roles**: Every user gets a default role via `ensure_role_assignment()` in `UsersRepo`
- **CORS**: Currently open (`allow_origins=["*"]`) in [main.py](backend/app/main.py) — restrict in production

### OTP Flow (Email Verification)
1. User registers → OTP created, email sent (background task)
2. `VerificacionOTP` stored with PENDING status, 10-min expiry
3. User receives email, enters code → verified, user status changes to ACTIVE
4. OTP expires after 10 mins or if marked VERIFIED/EXPIRED
5. **Key Classes**: [VerificacionOTP](backend/app/models/otp.py), [EmailOtpService](backend/app/services/email_otp_service.py), [OtpRepo](backend/app/repositories/otp_repo.py)

### Repositories (Data Access Layer)
- All DB queries via Repository classes (e.g., [UsersRepo](backend/app/repositories/users_repo.py))
- Standard methods: `get_by_*()`, `create_*()`, `save()`, `delete_*()`
- Use SQLAlchemy 2.0 `.select()` syntax, not legacy Query API
- Example: `self.db.execute(select(Usuario).where(Usuario.email == email)).scalar_one_or_none()`

### Exception Handling
- Centralized handlers in [exceptions.py](backend/app/core/exceptions.py): `IntegrityError`, `OperationalError`, `DataError`, `ValidationError`
- Standardized error response: `ErrorResponse.format(error_type, message, detail, status_code)`
- Always return consistent JSON structure for frontend parsing

### Background Tasks & Cleanup
- APScheduler runs `cleanup_expired_pending_users()` every 10 mins (in [cleanup_service.py](backend/app/services/cleanup_service.py))
- Removes users with status=PENDING after 40+ mins
- Registered in FastAPI's `lifespan` context manager (lifecycle hooks)

### Email Configuration
- SMTP settings in [config.py](backend/app/core/config.py): `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`
- Environment variables required: `.env` file with `SMTP_*` vars
- Service: [EmailOtpService](backend/app/services/email_otp_service.py) uses `smtplib` with TLS

### Frontend Component System
- **Naming**: Components in `components/ui/` are reusable primitives (button, input, card)
- **Styling**: Tailwind CSS 4 + custom CSS variables (green palette)
- **Auth Layouts**: Two variants (classic, glassmorphism) in `components/auth-layout*.tsx`
- **Type Definitions**: API shapes in [lib/api-client.ts](frontend/lib/api-client.ts) and [types/api.ts](frontend/types/api.ts)

---

## 🔌 Integration Points & External Dependencies

### API Endpoints Structure
- **Routers**: `app/api/v1/{auth,admin,analyses,users,documents,locations}.py`
- **Dependency Injection**: Auth via `HTTPBearer` security scheme in `get_current_user()`
- **Response Models**: Pydantic schemas in `schemas/{auth,user,analisis,documentos,propuestas}.py`

### Email Service Integration
- Currently: SMTP-based OTP sending
- Future: S3 integration (boto3) for PDF uploads, Gemini API for credit analysis
- Placeholder services exist: [s3_service.py](backend/app/services/s3_service.py), [gemini_service.py](backend/app/services/gemini_service.py)

### Frontend API Client
- Base URL: `/api/v1` (via next.config.ts rewrite)
- Method: Fetch API with Authorization header
- Validation: Response shapes typed against `api.ts`

---

## 📚 Key Files for Common Tasks

| Task | Primary File(s) |
|---|---|
| Add auth endpoint | [app/api/v1/auth.py](backend/app/api/v1/auth.py) → update route, add schema in [schemas/auth.py](backend/app/schemas/auth.py) |
| Add user field | [models/user.py](backend/app/models/user.py) → create Alembic migration |
| New database query | Create method in [repositories/](backend/app/repositories/) → call from service |
| Modify UI component | Edit in [components/ui/](frontend/components/ui/) → test via Storybook or directly |
| Update color palette | [frontend/app/globals.css](frontend/app/globals.css) → CSS variables automatically cascade |
| Change OTP timeout | [core/config.py](backend/app/core/config.py) `OTP_EXPIRE_MINUTES` |
| Fix CORS issues | [app/main.py](backend/app/main.py) `CORSMiddleware` config |

---

## ⚠️ Common Pitfalls

1. **Database Access**: Never use `db.query()` (legacy). Always use `db.execute(select(...))` (SQLAlchemy 2.0).
2. **Session Management**: Don't create `SessionLocal()` manually in routes; use `Depends(get_db)` dependency.
3. **JWT Token**: Ensure `SECRET_KEY` in `.env` is 32+ chars; otherwise `jwt.encode()` fails silently.
4. **SMTP Credentials**: Gmail requires App Passwords, not regular password. Ensure `.env` has correct credentials.
5. **Frontend API URL**: Must use `/api/v1` (relative path via proxy), not `http://localhost:8001/api/v1`.
6. **UUID Primary Keys**: All major tables use `UUID` with `gen_random_uuid()` server default—handle properly in queries.

---

## 📖 Documentation References

- **Architecture Details**: [REFACTORING_SUMMARY.md](backend/REFACTORING_SUMMARY.md)
- **API Testing Guide**: [TESTING.md](TESTING.md)
- **Frontend Design**: [frontend/DESIGN_SYSTEM.md](frontend/DESIGN_SYSTEM.md)
- **Admin Features**: [CHECKLIST_IMPLEMENTACION.md](CHECKLIST_IMPLEMENTACION.md)

---

## 🚀 When Implementing Features

1. **Backend**: Route → Schema (Pydantic) → Service → Repository → Model
2. **Database**: Update model, create migration (Alembic), seed if needed
3. **Frontend**: Type in `types/api.ts`, update `api-client.ts`, create page/component, style with design system
4. **Testing**: Add test in `backend/app/tests/` before merging
5. **Documentation**: Update relevant .md file (API endpoints, workflows)

---

Generated: January 28, 2025 | Based on codebase analysis of EcoFinanzas credit analysis platform.
