# 🤖 PerFinanzas — Copilot Instructions (Stack Estricto)

> **Objetivo**: asegurar consistencia técnica, mantenibilidad y calidad en todo cambio generado por IA para PerFinanzas.  
> **Stack oficial**:
- **Backend**: Python + FastAPI + Pydantic
- **Frontend**: Next.js + Tailwind CSS + TypeScript estricto
- **Base de Datos**: SQL Server
- **Infraestructura**: Docker

---

## 1) Reglas globales (obligatorias)

1. No generar código fuera del stack oficial.
2. Priorizar cambios pequeños, claros y reversibles.
3. Mantener compatibilidad con arquitectura por capas.
4. Toda lógica de negocio debe ser testeable.
5. No hardcodear secretos ni credenciales.
6. Si se modifica contrato API, actualizar tipos del frontend y documentación.
7. Evitar duplicación: reutilizar utilidades, componentes y servicios existentes.

---

## 2) Convenciones de nomenclatura

## Backend (Python)
- **Archivos/módulos**: `snake_case.py`
- **Variables y funciones**: `snake_case`
- **Clases**: `PascalCase`
- **Constantes**: `UPPER_SNAKE_CASE`
- **Rutas**: nombres REST en plural (`/users`, `/analyses`)
- **Pydantic DTOs**: sufijos claros:
  - `CreateXRequest`, `UpdateXRequest`, `XResponse`, `XListResponse`

## Frontend (TypeScript/Next.js)
- **Variables/funciones**: `camelCase`
- **Componentes/Tipos/Interfaces**: `PascalCase`
- **Hooks**: `useXxx`
- **Archivos de componentes**: `PascalCase.tsx`
- **Utilidades y servicios**: `kebab-case.ts` o `camelCase.ts` (consistente por carpeta)
- **Rutas App Router**: carpetas en `kebab-case`

## Base de datos (SQL Server)
- Tablas y columnas con convención consistente (recomendado `snake_case`).
- PK estándar por entidad (UUID o IDENTITY, según decisión de proyecto).
- Índices y constraints con prefijos: `pk_`, `fk_`, `uq_`, `ix_`, `ck_`.

---

## 3) Arquitectura backend (FastAPI)

Estructura obligatoria:
- `api/` → endpoints (sin lógica de negocio compleja)
- `schemas/` → validación y contratos (Pydantic)
- `services/` → casos de uso y reglas de negocio
- `repositories/` → acceso a datos
- `models/` → entidades ORM

Reglas:
1. Endpoints delgados: validar entrada, invocar servicio, responder.
2. Servicios sin dependencias de framework cuando sea posible.
3. Repositorios encapsulan queries SQLAlchemy.
4. No mezclar acceso DB directamente en routers.
5. Usar tipado explícito en todas las funciones públicas.

---

## 4) Validaciones con Pydantic (obligatorio)

1. Definir `Request` y `Response` para cada endpoint.
2. Validar rangos, formatos y campos opcionales correctamente.
3. Rechazar campos extra en payload cuando aplique (`extra="forbid"`).
4. Mensajes de error comprensibles para frontend.
5. Normalizar tipos financieros (`Decimal`) para valores monetarios.

---

## 5) Manejo consistente de errores y respuestas HTTP

Formato estándar de error (backend):
```json
{
  "error": "error_type",
  "message": "Mensaje legible",
  "status_code": 400,
  "detail": {}
}
```

Reglas:
1. Usar códigos HTTP correctos:
   - `200` OK (consulta/actualización)
   - `201` Created
   - `204` No Content
   - `400` Bad Request
   - `401` Unauthorized
   - `403` Forbidden
   - `404` Not Found
   - `409` Conflict
   - `422` Validation Error
   - `500` Internal Server Error
   - `503` Service Unavailable
2. No exponer trazas internas al cliente.
3. Registrar errores en logs estructurados con contexto.
4. Mantener un manejador global de excepciones en FastAPI.
5. Frontend debe mapear errores API a mensajes de UI consistentes.

---

## 6) Estándares frontend (Next.js + Tailwind + TS estricto)

1. TypeScript en modo estricto (`strict: true`).
2. Prohibido `any` salvo justificación técnica documentada.
3. Componentes presentacionales sin lógica de red.
4. Lógica de negocio/UI compleja en hooks o services.
5. Clases Tailwind legibles; extraer patrones repetidos.
6. Accesibilidad mínima:
   - `label` asociado a inputs
   - focus visible
   - contraste adecuado
   - soporte teclado básico
7. Manejar estados de `loading`, `error`, `empty`, `success`.

---

## 7) Componentes modulares (obligatorio)

Arquitectura sugerida:
- `components/ui/` → primitivas reutilizables (Button, Input, Card)
- `components/<feature>/` → componentes de dominio
- `hooks/` → estado y comportamiento reutilizable
- `lib/` o `services/` → cliente API y utilidades

Reglas:
1. Un componente = una responsabilidad clara.
2. Props tipadas explícitamente.
3. Evitar componentes gigantes (>200 líneas) sin motivo.
4. Favorecer composición sobre herencia.
5. Reutilizar primitivas UI antes de crear variantes nuevas.

---

## 8) Base de datos SQL Server (prácticas)

1. Usar SQLAlchemy 2.0 con dialecto SQL Server.
2. Migraciones con Alembic para todo cambio de esquema.
3. Evitar SQL inline en routers/services.
4. Tipos recomendados:
   - dinero: `DECIMAL(p,s)`
   - fechas: `DATETIME2`
   - ids únicos: `UNIQUEIDENTIFIER` (si UUID)
5. Definir índices para filtros frecuentes.
6. Toda constraint crítica también debe validarse en aplicación.

---

## 9) Dockerización (obligatorio)

1. Mantener Dockerfile por servicio (backend/frontend).
2. Usar `.dockerignore` para builds limpios.
3. Variables por entorno con `.env` (sin secretos en git).
4. Contenedores reproducibles y puertos documentados.
5. `docker compose` como estándar local.
6. Healthchecks para servicios críticos (API y DB).

---

## 10) Seguridad mínima

1. JWT y autorización por roles donde aplique.
2. Nunca loggear secretos/tokens completos.
3. Validar inputs en backend siempre (no confiar en frontend).
4. CORS restringido por entorno en producción.
5. Rate limiting en endpoints sensibles (auth/upload).

---

## 11) Testing y calidad

## Backend
- Tests unitarios de servicios.
- Tests de integración para endpoints críticos.
- Casos de error obligatorios (validaciones, permisos, conflicto).

## Frontend
- Tests de componentes clave y utilidades.
- Validar flujos de formularios y estados de error.
- Mantener tipado sin regresiones.

Reglas:
1. Cada bug corregido debe añadir o ajustar test.
2. No mezclar refactor grande con cambio funcional sin necesidad.
3. Mantener lint/format sin warnings críticos.

---

## 12) Definition of Done (DoD)

Un cambio se considera completo si:
- [ ] Respeta nomenclatura y arquitectura por capas
- [ ] Incluye validaciones Pydantic correctas
- [ ] Maneja errores con formato estándar
- [ ] Mantiene TypeScript estricto sin `any` innecesario
- [ ] Usa componentes frontend modulares y reutilizables
- [ ] Incluye/actualiza pruebas
- [ ] Incluye migración si hubo cambio en DB
- [ ] Actualiza documentación técnica si cambia contrato o flujo

---

## 13) Política de generación de código por IA

1. Preferir soluciones simples y mantenibles.
2. No introducir nuevas librerías sin justificación.
3. Explicar supuestos técnicos cuando existan ambigüedades.
4. Si hay conflicto entre estilos, priorizar estas instrucciones.
5. Toda salida debe ser directamente aplicable al repositorio.

