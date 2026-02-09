from app.models.user import Usuario
from app.models.role import Role, UsuarioRole
from app.models.otp import VerificacionOTP
from app.models.banco import Banco
from app.models.documento import DocumentoS3
from app.models.analisis import AnalisisHipotecario
from app.models.propuesta import PropuestaAhorro
from app.models.referencia import ReferenciaUsuario, TipoReferencia
from app.models.analysis_details import AnalysisMovement, AnalysisRates, AnalysisUVR

__all__ = [
    "Usuario",
    "Role", 
    "UsuarioRole",
    "VerificacionOTP",
    "Banco",
    "DocumentoS3",
    "AnalisisHipotecario",
    "PropuestaAhorro",
    "ReferenciaUsuario",
    "TipoReferencia",
    "AnalysisMovement",
    "AnalysisRates",
    "AnalysisUVR",
]