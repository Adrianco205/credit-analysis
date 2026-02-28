from datetime import datetime
from math import ceil
from uuid import UUID

from pydantic import BaseModel, Field


class AdminAnalysisCustomer(BaseModel):
    user_id: UUID
    full_name: str
    id_number: str | None = None


class AdminAnalysisBank(BaseModel):
    id: int | None = None
    name: str | None = None


class AdminAnalysisActions(BaseModel):
    can_view_summary: bool = False
    can_view_detail: bool = False
    can_view_pdf: bool = False


class AdminAnalysisItem(BaseModel):
    analysis_id: UUID
    uploaded_at: datetime | None = None
    customer: AdminAnalysisCustomer
    bank: AdminAnalysisBank
    credit_number: str | None = None
    document_id: UUID | None = None
    status: str
    extracted_manually: bool = False
    actions: AdminAnalysisActions


class AdminAnalysisPagination(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class AdminBankOption(BaseModel):
    id: int
    name: str


class AdminAnalysisFilters(BaseModel):
    bank_options: list[AdminBankOption] = Field(default_factory=list)


class AdminAnalysesListResponse(BaseModel):
    data: list[AdminAnalysisItem]
    pagination: AdminAnalysisPagination
    filters: AdminAnalysisFilters


class AdminAnalysesParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)
    customer_id_number: str | None = None
    customer_name: str | None = None
    credit_number: str | None = None
    bank_id: int | None = None
    uploaded_from: datetime | None = None
    uploaded_to: datetime | None = None
    sort_by: str = "uploaded_at"
    sort_dir: str = "desc"

    @property
    def normalized_sort_by(self) -> str:
        allowed = {"uploaded_at", "customer_name", "bank_name", "credit_number"}
        if self.sort_by not in allowed:
            return "uploaded_at"
        return self.sort_by

    @property
    def normalized_sort_dir(self) -> str:
        return "asc" if self.sort_dir == "asc" else "desc"


class AdminPaginationFactory:
    @staticmethod
    def build(page: int, page_size: int, total: int) -> AdminAnalysisPagination:
        total_pages = ceil(total / page_size) if total > 0 else 1
        return AdminAnalysisPagination(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )
