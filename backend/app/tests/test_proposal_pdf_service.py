from decimal import Decimal

from app.services.proposal_pdf_service import PropuestaPDFGenerator


class TestProposalPdfRateFormatting:
    def test_format_tasa_ea_from_decimal(self):
        generator = PropuestaPDFGenerator()

        value = generator._format_tasa_ea(Decimal("0.0471"))

        assert value == "4.71% E.A."

    def test_format_tasa_ea_from_percentage(self):
        generator = PropuestaPDFGenerator()

        value = generator._format_tasa_ea(Decimal("4.71"))

        assert value == "4.71% E.A."
