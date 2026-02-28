from datetime import date, datetime, time
from typing import Any

from sqlalchemy import and_, asc, desc, func, literal, or_, select
from sqlalchemy.orm import Session

from app.models.analisis import AnalisisHipotecario
from app.models.banco import Banco
from app.models.user import Usuario


class AdminAnalysesRepo:
	"""Consultas para historial administrativo de análisis."""

	def __init__(self, db: Session):
		self.db = db

	def list_analyses(
		self,
		*,
		page: int,
		page_size: int,
		customer_id_number: str | None = None,
		customer_name: str | None = None,
		credit_number: str | None = None,
		bank_id: int | None = None,
		uploaded_from: date | datetime | None = None,
		uploaded_to: date | datetime | None = None,
		sort_by: str = "uploaded_at",
		sort_dir: str = "desc",
	) -> tuple[list[dict[str, Any]], int]:
		"""Retorna (filas, total) para la tabla admin de análisis."""
		offset = (page - 1) * page_size

		base_stmt = (
			select(
				AnalisisHipotecario.id.label("analysis_id"),
				AnalisisHipotecario.created_at.label("uploaded_at"),
				AnalisisHipotecario.documento_id.label("document_id"),
				AnalisisHipotecario.numero_credito.label("credit_number"),
				AnalisisHipotecario.status.label("status"),
				AnalisisHipotecario.campos_manuales.label("campos_manuales"),
				Usuario.id.label("user_id"),
				Usuario.nombres.label("nombres"),
				Usuario.primer_apellido.label("primer_apellido"),
				Usuario.segundo_apellido.label("segundo_apellido"),
				Usuario.identificacion.label("id_number"),
				Banco.id.label("bank_id"),
				Banco.nombre.label("bank_name"),
			)
			.select_from(AnalisisHipotecario)
			.join(Usuario, Usuario.id == AnalisisHipotecario.usuario_id)
			.outerjoin(Banco, Banco.id == AnalisisHipotecario.banco_id)
		)

		filters = []

		if customer_id_number:
			filters.append(Usuario.identificacion.ilike(f"%{customer_id_number.strip()}%"))

		if customer_name:
			name_pattern = f"%{customer_name.strip()}%"
			full_name = func.concat(
				func.coalesce(Usuario.nombres, ""),
				literal(" "),
				func.coalesce(Usuario.primer_apellido, ""),
				literal(" "),
				func.coalesce(Usuario.segundo_apellido, ""),
			)
			filters.append(
				or_(
					Usuario.nombres.ilike(name_pattern),
					Usuario.primer_apellido.ilike(name_pattern),
					Usuario.segundo_apellido.ilike(name_pattern),
					full_name.ilike(name_pattern),
				)
			)

		if credit_number:
			filters.append(AnalisisHipotecario.numero_credito.ilike(f"%{credit_number.strip()}%"))

		if bank_id:
			filters.append(AnalisisHipotecario.banco_id == bank_id)

		if uploaded_from:
			if isinstance(uploaded_from, date) and not isinstance(uploaded_from, datetime):
				uploaded_from = datetime.combine(uploaded_from, time.min)
			filters.append(AnalisisHipotecario.created_at >= uploaded_from)

		if uploaded_to:
			if isinstance(uploaded_to, date) and not isinstance(uploaded_to, datetime):
				uploaded_to = datetime.combine(uploaded_to, time.max)
			filters.append(AnalisisHipotecario.created_at <= uploaded_to)

		if filters:
			base_stmt = base_stmt.where(and_(*filters))

		count_stmt = select(func.count()).select_from(base_stmt.subquery())
		total = self.db.execute(count_stmt).scalar() or 0

		sort_map = {
			"uploaded_at": AnalisisHipotecario.created_at,
			"customer_name": Usuario.nombres,
			"bank_name": Banco.nombre,
			"credit_number": AnalisisHipotecario.numero_credito,
		}
		sort_column = sort_map.get(sort_by, AnalisisHipotecario.created_at)
		sort_fn = asc if sort_dir == "asc" else desc

		rows = self.db.execute(
			base_stmt.order_by(sort_fn(sort_column), desc(AnalisisHipotecario.created_at))
			.offset(offset)
			.limit(page_size)
		).mappings().all()

		return [dict(row) for row in rows], total

	def get_bank_options(self) -> list[dict[str, Any]]:
		"""Obtiene listado de bancos para filtros."""
		rows = self.db.execute(
			select(Banco.id, Banco.nombre)
			.where(Banco.activo.is_(True))
			.order_by(Banco.nombre.asc())
		).all()
		return [{"id": row[0], "name": row[1]} for row in rows]
