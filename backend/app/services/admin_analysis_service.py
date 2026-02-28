from app.repositories.admin_repo import AdminAnalysesRepo
from app.schemas.admin_analysis import (
    AdminAnalysesListResponse,
    AdminAnalysesParams,
    AdminAnalysisActions,
    AdminAnalysisBank,
    AdminAnalysisCustomer,
    AdminAnalysisFilters,
    AdminAnalysisItem,
    AdminBankOption,
    AdminPaginationFactory,
)


class AdminAnalysisService:
    """Lógica de negocio para historial de análisis en panel admin."""

    SUMMARY_ENABLED_STATUSES = {
        "COMPLETED",
        "EXTRACTED",
        "NAME_MISMATCH",
        "PENDING_MANUAL",
    }

    def __init__(self, repo: AdminAnalysesRepo):
        self.repo = repo

    def list_analyses(self, params: AdminAnalysesParams) -> AdminAnalysesListResponse:
        rows, total = self.repo.list_analyses(
            page=params.page,
            page_size=params.page_size,
            customer_id_number=params.customer_id_number,
            customer_name=params.customer_name,
            credit_number=params.credit_number,
            bank_id=params.bank_id,
            uploaded_from=params.uploaded_from,
            uploaded_to=params.uploaded_to,
            sort_by=params.normalized_sort_by,
            sort_dir=params.normalized_sort_dir,
        )

        data = []
        for row in rows:
            full_name = " ".join(
                [
                    (row.get("nombres") or "").strip(),
                    (row.get("primer_apellido") or "").strip(),
                    (row.get("segundo_apellido") or "").strip(),
                ]
            ).strip()

            status = row.get("status") or ""
            document_id = row.get("document_id")

            actions = AdminAnalysisActions(
                can_view_summary=status in self.SUMMARY_ENABLED_STATUSES,
                can_view_detail=True,
                can_view_pdf=document_id is not None,
            )

            data.append(
                AdminAnalysisItem(
                    analysis_id=row["analysis_id"],
                    uploaded_at=row.get("uploaded_at"),
                    customer=AdminAnalysisCustomer(
                        user_id=row["user_id"],
                        full_name=full_name or "Usuario sin nombre",
                        id_number=row.get("id_number"),
                    ),
                    bank=AdminAnalysisBank(
                        id=row.get("bank_id"),
                        name=row.get("bank_name"),
                    ),
                    credit_number=row.get("credit_number"),
                    document_id=document_id,
                    status=status,
                    extracted_manually=bool(row.get("campos_manuales") and len(row.get("campos_manuales")) > 0),
                    actions=actions,
                )
            )

        pagination = AdminPaginationFactory.build(
            page=params.page,
            page_size=params.page_size,
            total=total,
        )

        bank_options = [AdminBankOption(**option) for option in self.repo.get_bank_options()]

        return AdminAnalysesListResponse(
            data=data,
            pagination=pagination,
            filters=AdminAnalysisFilters(bank_options=bank_options),
        )
