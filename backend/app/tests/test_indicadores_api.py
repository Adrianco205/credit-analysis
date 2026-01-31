"""
Tests para los endpoints de Indicadores Financieros.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.indicadores import router as indicadores_router


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def app():
    """App de pruebas aislada (sin dependencias de main.py)"""
    test_app = FastAPI()
    test_app.include_router(indicadores_router, prefix="/api/v1")
    return test_app


@pytest.fixture
def client(app):
    """Cliente de pruebas para FastAPI"""
    return TestClient(app)


@pytest.fixture
def mock_uvr_response():
    """Mock de respuesta UVR"""
    from app.services.indicadores_service import ValorUVR, FuenteDatos
    return ValorUVR(
        fecha=date.today(),
        valor=Decimal("385.4521"),
        fuente=FuenteDatos.SOCRATA
    )


@pytest.fixture
def mock_ipc_response():
    """Mock de respuesta IPC"""
    from app.services.indicadores_service import ValorIPC, FuenteDatos
    return ValorIPC(
        fecha=date(2025, 12, 31),
        valor=Decimal("158.50"),
        variacion_mensual=Decimal("0.45"),
        variacion_anual=Decimal("5.80"),
        fuente=FuenteDatos.SOCRATA
    )


@pytest.fixture
def mock_dtf_response():
    """Mock de respuesta DTF"""
    from app.services.indicadores_service import ValorDTF, FuenteDatos
    return ValorDTF(
        fecha=date.today(),
        valor=Decimal("10.50"),
        fuente=FuenteDatos.SOCRATA
    )


@pytest.fixture
def mock_ibr_response():
    """Mock de respuesta IBR"""
    from app.services.indicadores_service import ValorIBR, FuenteDatos
    return ValorIBR(
        fecha=date.today(),
        overnight=Decimal("9.75"),
        un_mes=Decimal("9.80"),
        tres_meses=Decimal("9.90"),
        fuente=FuenteDatos.MANUAL
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestEndpointUVR:
    """Tests para /api/v1/indicadores/uvr"""
    
    def test_get_uvr_actual(self, client, mock_uvr_response):
        """GET /indicadores/uvr sin fecha retorna UVR de hoy"""
        with patch('app.api.v1.indicadores.obtener_servicio_indicadores') as mock_service:
            mock_instance = MagicMock()
            mock_instance.obtener_uvr_actual = AsyncMock(return_value=mock_uvr_response)
            mock_service.return_value = mock_instance
            
            response = client.get("/api/v1/indicadores/uvr")
            
            assert response.status_code == 200
            data = response.json()
            assert "fecha" in data
            assert "valor" in data
            assert "fuente" in data
            assert data["fuente"] == "SOCRATA"
    
    def test_get_uvr_fecha_especifica(self, client, mock_uvr_response):
        """GET /indicadores/uvr?fecha=2025-01-15 retorna UVR de esa fecha"""
        with patch('app.api.v1.indicadores.obtener_servicio_indicadores') as mock_service:
            mock_instance = MagicMock()
            mock_instance.obtener_uvr = AsyncMock(return_value=mock_uvr_response)
            mock_service.return_value = mock_instance
            
            response = client.get("/api/v1/indicadores/uvr?fecha=2025-01-15")
            
            assert response.status_code == 200
            data = response.json()
            assert "valor" in data


class TestEndpointIPC:
    """Tests para /api/v1/indicadores/ipc"""
    
    def test_get_ipc_actual(self, client, mock_ipc_response):
        """GET /indicadores/ipc retorna IPC más reciente"""
        with patch('app.api.v1.indicadores.obtener_servicio_indicadores') as mock_service:
            mock_instance = MagicMock()
            mock_instance.obtener_ipc_actual = AsyncMock(return_value=mock_ipc_response)
            mock_service.return_value = mock_instance
            
            response = client.get("/api/v1/indicadores/ipc")
            
            assert response.status_code == 200
            data = response.json()
            assert "valor" in data
            assert "variacion_mensual" in data
            assert "variacion_anual" in data
    
    def test_get_ipc_mes_especifico(self, client, mock_ipc_response):
        """GET /indicadores/ipc?anio=2025&mes=6 retorna IPC de ese mes"""
        with patch('app.api.v1.indicadores.obtener_servicio_indicadores') as mock_service:
            mock_instance = MagicMock()
            mock_instance.obtener_ipc = AsyncMock(return_value=mock_ipc_response)
            mock_service.return_value = mock_instance
            
            response = client.get("/api/v1/indicadores/ipc?anio=2025&mes=6")
            
            assert response.status_code == 200


class TestEndpointDTF:
    """Tests para /api/v1/indicadores/dtf"""
    
    def test_get_dtf_actual(self, client, mock_dtf_response):
        """GET /indicadores/dtf retorna DTF vigente"""
        with patch('app.api.v1.indicadores.obtener_servicio_indicadores') as mock_service:
            mock_instance = MagicMock()
            mock_instance.obtener_dtf_actual = AsyncMock(return_value=mock_dtf_response)
            mock_service.return_value = mock_instance
            
            response = client.get("/api/v1/indicadores/dtf")
            
            assert response.status_code == 200
            data = response.json()
            assert "valor" in data
            assert float(data["valor"]) > 0


class TestEndpointIBR:
    """Tests para /api/v1/indicadores/ibr"""
    
    def test_get_ibr_actual(self, client, mock_ibr_response):
        """GET /indicadores/ibr retorna IBR vigente"""
        with patch('app.api.v1.indicadores.obtener_servicio_indicadores') as mock_service:
            mock_instance = MagicMock()
            mock_instance.obtener_ibr_actual = AsyncMock(return_value=mock_ibr_response)
            mock_service.return_value = mock_instance
            
            response = client.get("/api/v1/indicadores/ibr")
            
            assert response.status_code == 200
            data = response.json()
            assert "overnight" in data
            assert "un_mes" in data
            assert "tres_meses" in data


class TestEndpointConsolidado:
    """Tests para /api/v1/indicadores/consolidados"""
    
    def test_get_todos_indicadores(self, client):
        """GET /indicadores/consolidados retorna todos los indicadores"""
        from app.services.indicadores_service import IndicadoresFinancieros
        
        mock_indicadores = IndicadoresFinancieros(
            fecha=date.today(),
            uvr=Decimal("385.45"),
            dtf=Decimal("10.50"),
            ibr_overnight=Decimal("9.75"),
            ipc_anual=Decimal("5.80")
        )
        
        with patch('app.api.v1.indicadores.obtener_servicio_indicadores') as mock_service:
            mock_instance = MagicMock()
            mock_instance.obtener_indicadores_hoy = AsyncMock(return_value=mock_indicadores)
            mock_service.return_value = mock_instance
            
            response = client.get("/api/v1/indicadores/consolidados")
            
            assert response.status_code == 200
            data = response.json()
            assert "uvr" in data
            assert "dtf" in data
            assert "ibr_overnight" in data
            assert "ipc_anual" in data


class TestEndpointHistorico:
    """Tests para /api/v1/indicadores/uvr/historico"""
    
    def test_get_historico_uvr(self, client, mock_uvr_response):
        """GET /indicadores/uvr/historico retorna lista de UVR"""
        historico = [mock_uvr_response for _ in range(7)]
        
        with patch('app.api.v1.indicadores.obtener_servicio_indicadores') as mock_service:
            mock_instance = MagicMock()
            mock_instance.obtener_historico_uvr = AsyncMock(return_value=historico)
            mock_service.return_value = mock_instance
            
            fecha_inicio = (date.today() - timedelta(days=7)).isoformat()
            fecha_fin = date.today().isoformat()
            
            response = client.get(
                f"/api/v1/indicadores/uvr/historico?fecha_inicio={fecha_inicio}&fecha_fin={fecha_fin}"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "datos" in data
            assert "total_registros" in data
            assert data["total_registros"] == 7
    
    def test_historico_rango_maximo(self, client):
        """Histórico no permite más de 365 días"""
        fecha_inicio = (date.today() - timedelta(days=400)).isoformat()
        fecha_fin = date.today().isoformat()
        
        response = client.get(
            f"/api/v1/indicadores/uvr/historico?fecha_inicio={fecha_inicio}&fecha_fin={fecha_fin}"
        )
        
        assert response.status_code == 400
        assert "365" in response.json()["detail"]
    
    def test_historico_fecha_inicio_requerida(self, client):
        """Histórico requiere fecha_inicio"""
        response = client.get("/api/v1/indicadores/uvr/historico")
        
        assert response.status_code == 422  # Validation error


class TestEndpointConversiones:
    """Tests para /api/v1/indicadores/uvr/convertir"""
    
    def test_convertir_uvr_a_pesos(self, client, mock_uvr_response):
        """POST /indicadores/uvr/convertir - UVR a pesos"""
        with patch('app.api.v1.indicadores.obtener_servicio_indicadores') as mock_service:
            mock_instance = MagicMock()
            mock_instance.obtener_uvr_actual = AsyncMock(return_value=mock_uvr_response)
            mock_instance.convertir_uvr_a_pesos = MagicMock(return_value=Decimal("38545210.00"))
            mock_service.return_value = mock_instance
            
            response = client.post(
                "/api/v1/indicadores/uvr/convertir",
                json={
                    "monto": 100000,
                    "direccion": "uvr_a_pesos"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "monto_convertido" in data
            assert data["direccion"] == "uvr_a_pesos"
    
    def test_convertir_pesos_a_uvr(self, client, mock_uvr_response):
        """POST /indicadores/uvr/convertir - Pesos a UVR"""
        with patch('app.api.v1.indicadores.obtener_servicio_indicadores') as mock_service:
            mock_instance = MagicMock()
            mock_instance.obtener_uvr_actual = AsyncMock(return_value=mock_uvr_response)
            mock_instance.convertir_pesos_a_uvr = MagicMock(return_value=Decimal("259.44"))
            mock_service.return_value = mock_instance
            
            response = client.post(
                "/api/v1/indicadores/uvr/convertir",
                json={
                    "monto": 100000,
                    "direccion": "pesos_a_uvr"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["direccion"] == "pesos_a_uvr"
    
    def test_convertir_direccion_invalida(self, client, mock_uvr_response):
        """POST /indicadores/uvr/convertir con dirección inválida"""
        # El endpoint real valida la dirección y retorna 400
        # Con el mock, necesitamos simular el servicio completo
        response = client.post(
            "/api/v1/indicadores/uvr/convertir",
            json={
                "monto": 100000,
                "direccion": "invalida"
            }
        )
        
        # El endpoint retorna 400 o 500 dependiendo de dónde falle
        # Lo importante es que NO retorne 200
        assert response.status_code in [400, 500]
        assert response.status_code != 200


class TestEndpointProyeccion:
    """Tests para /api/v1/indicadores/uvr/proyectar"""
    
    def test_proyectar_uvr(self, client, mock_uvr_response):
        """POST /indicadores/uvr/proyectar"""
        with patch('app.api.v1.indicadores.obtener_servicio_indicadores') as mock_service:
            mock_instance = MagicMock()
            mock_instance.obtener_uvr_actual = AsyncMock(return_value=mock_uvr_response)
            mock_instance.proyectar_uvr = MagicMock(return_value=Decimal("408.58"))
            mock_service.return_value = mock_instance
            
            response = client.post(
                "/api/v1/indicadores/uvr/proyectar",
                json={
                    "meses": 12,
                    "inflacion_anual": 0.06
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "uvr_inicial" in data
            assert "uvr_proyectado" in data
            assert "incremento_absoluto" in data
            assert "incremento_porcentual" in data
    
    def test_proyectar_uvr_meses_invalidos(self, client):
        """POST /indicadores/uvr/proyectar con meses > 360"""
        response = client.post(
            "/api/v1/indicadores/uvr/proyectar",
            json={
                "meses": 500,
                "inflacion_anual": 0.06
            }
        )
        
        assert response.status_code == 422  # Validation error


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSchemas:
    """Tests para los schemas de Pydantic"""
    
    def test_uvr_response_schema(self):
        """UVRResponse schema"""
        from app.api.v1.indicadores import UVRResponse
        
        response = UVRResponse(
            fecha=date.today(),
            valor=Decimal("385.4521"),
            fuente="SOCRATA"
        )
        
        assert response.fecha == date.today()
        assert response.valor == Decimal("385.4521")
    
    def test_conversion_request_schema(self):
        """ConversionUVRRequest schema"""
        from app.api.v1.indicadores import ConversionUVRRequest
        
        request = ConversionUVRRequest(
            monto=Decimal("100000"),
            direccion="uvr_a_pesos"
        )
        
        assert request.monto == Decimal("100000")
        assert request.valor_uvr is None  # Opcional
    
    def test_proyeccion_request_schema(self):
        """ProyeccionUVRRequest schema"""
        from app.api.v1.indicadores import ProyeccionUVRRequest
        
        request = ProyeccionUVRRequest(
            meses=12
        )
        
        assert request.meses == 12
        assert request.inflacion_anual == Decimal("0.06")  # Default
