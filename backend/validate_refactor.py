"""
Script de validación rápida para verificar imports y estructura.
NO ejecuta el servidor, solo valida sintaxis y dependencias.
"""
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Verifica que todos los módulos se importen correctamente"""
    print("🔍 Validando imports...")
    
    try:
        # Core
        from app.core.config import settings
        from app.core.security import hash_password, verify_password, create_access_token
        from app.core.exceptions import ErrorResponse
        print("✅ Core imports OK")
        
        # Database
        from app.db.base import Base
        from app.db.session import SessionLocal
        print("✅ Database imports OK")
        
        # Models
        from app.models.user import Usuario
        from app.models.otp import VerificacionOTP
        from app.models.role import Role, UsuarioRole
        from app.models.banco import Banco
        from app.models.documento import DocumentoS3
        from app.models.analisis import AnalisisHipotecario
        from app.models.propuesta import PropuestaAhorro
        print("✅ Models imports OK")
        
        # Repositories
        from app.repositories.users_repo import UsersRepo
        from app.repositories.otp_repo import OtpRepo
        print("✅ Repositories imports OK")
        
        # Schemas
        from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
        from app.schemas.user import UserProfileResponse, UpdatePasswordRequest
        print("✅ Schemas imports OK")
        
        # Services (algunos tienen dependencias externas que faltan)
        from app.services.email_otp_service import EmailOtpService
        from app.services.cleanup_service import cleanup_expired_pending_users
        from app.services.gemini_service import GeminiService
        print("✅ Services imports OK (excepto pdf_service - PyPDF2 pendiente)")
        
        # API
        from app.api.deps import get_db, get_current_user, require_role
        from app.api.v1.router import api_router
        print("✅ API imports OK")
        
        # Main app
        from app.main import app
        print("✅ Main app import OK")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_security_functions():
    """Prueba las funciones de seguridad básicas"""
    print("\n🔐 Validando funciones de seguridad...")
    
    try:
        from app.core.security import hash_password, verify_password
        
        # Test hashing
        password = "Test1234!"
        hashed = hash_password(password)
        assert len(hashed) > 0, "Hash vacío"
        assert hashed != password, "Hash no funciona"
        print(f"✅ Hash generado: {hashed[:30]}...")
        
        # Test verification
        assert verify_password(password, hashed), "Verificación falló"
        print("✅ Verificación de password OK")
        
        assert not verify_password("wrong_password", hashed), "Verificación debería fallar"
        print("✅ Rechazo de password incorrecta OK")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en security: {e}")
        return False


def test_error_response():
    """Prueba la estructura de respuestas de error"""
    print("\n⚠️ Validando ErrorResponse...")
    
    try:
        from app.core.exceptions import ErrorResponse
        
        error = ErrorResponse.format(
            error_type="test_error",
            message="Test message",
            detail={"field": "test"},
            status_code=400
        )
        
        assert "error" in error
        assert "message" in error
        assert "status_code" in error
        assert error["error"] == "test_error"
        print("✅ ErrorResponse format OK")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en ErrorResponse: {e}")
        return False


def main():
    print("=" * 60)
    print("🧪 VALIDACIÓN DE REFACTORIZACIÓN - PerFinanzas Backend")
    print("=" * 60)
    
    results = []
    
    # Test 1: Imports
    results.append(("Imports", test_imports()))
    
    # Test 2: Security
    results.append(("Security Functions", test_security_functions()))
    
    # Test 3: Error Response
    results.append(("Error Response", test_error_response()))
    
    # Resumen
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE VALIDACIÓN")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("\n" + "=" * 60)
    print(f"Resultado: {passed}/{total} tests pasaron")
    
    if passed == total:
        print("🎉 ¡VALIDACIÓN EXITOSA! El código está listo.")
        print("\n📝 Notas:")
        print("  - PyPDF2 no instalado (esperado)")
        print("  - Para ejecutar: pip install -r requirements.txt")
        print("  - Luego: uvicorn app.main:app --reload")
    else:
        print("⚠️ Algunos tests fallaron. Revisa los errores arriba.")
    
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

