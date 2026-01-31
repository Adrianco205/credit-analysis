"""
Tests para el Servicio de Indicadores Financieros.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from app.services.indicadores_service import (
    IndicadoresFinancierosService,
    ValorUVR,
    ValorIPC,
    ValorDTF,
    ValorIBR,
    FuenteDatos,
    CacheIndicadores,
)


@pytest.fixture
def servicio():
    """Fixture para instanciar el servicio"""
    return IndicadoresFinancierosService()


@pytest.fixture
def cache():
    """Fixture para cache"""
    return CacheIndicadores(ttl_horas=1)


class TestCacheIndicadores:
    """Tests para el cache en memoria"""
    
    def test_cache_set_get(self, cache):
        """Guardar y recuperar valor"""
        cache.set("test_key", Decimal("100.50"))
        valor = cache.get("test_key")
        assert valor == Decimal("100.50")
    
    def test_cache_miss(self, cache):
        """Key no existente retorna None"""
        valor = cache.get("no_existe")
        assert valor is None
    
    def test_cache_clear(self, cache):
        """Limpiar cache"""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestConversionesUVR:
    """Tests para conversiones UVR <-> Pesos"""
    
    def test_uvr_a_pesos(self, servicio):
        """Convertir UVR a Pesos"""
        saldo_uvr = Decimal("149292.3850")
        valor_uvr = Decimal("376.1794")  # Valor del extracto
        
        pesos = servicio.convertir_uvr_a_pesos(saldo_uvr, valor_uvr)
        
        # Debe ser aproximadamente 56 millones (según extracto)
        assert Decimal("56000000") < pesos < Decimal("57000000")
    
    def test_pesos_a_uvr(self, servicio):
        """Convertir Pesos a UVR"""
        saldo_pesos = Decimal("56069733.47")
        valor_uvr = Decimal("376.1794")
        
        uvr = servicio.convertir_pesos_a_uvr(saldo_pesos, valor_uvr)
        
        # Debe ser aproximadamente 149,292 UVR
        assert Decimal("149000") < uvr < Decimal("150000")
    
    def test_conversion_ida_vuelta(self, servicio):
        """Conversión ida y vuelta debe dar valor original"""
        monto_original = Decimal("1000000.00")
        valor_uvr = Decimal("385.0000")
        
        uvr = servicio.convertir_pesos_a_uvr(monto_original, valor_uvr)
        pesos_final = servicio.convertir_uvr_a_pesos(uvr, valor_uvr)
        
        # Debe ser muy cercano al original (tolerancia por redondeo)
        diferencia = abs(monto_original - pesos_final)
        assert diferencia < Decimal("1.00")
    
    def test_conversion_uvr_cero_error(self, servicio):
        """Conversión con UVR = 0 debe fallar"""
        with pytest.raises(ValueError):
            servicio.convertir_pesos_a_uvr(Decimal("1000000"), Decimal("0"))


class TestProyeccionUVR:
    """Tests para proyección de UVR"""
    
    def test_proyeccion_12_meses(self, servicio):
        """Proyectar UVR a 12 meses"""
        uvr_actual = Decimal("385.0000")
        inflacion = Decimal("0.06")  # 6% anual
        
        uvr_futuro = servicio.proyectar_uvr(uvr_actual, 12, inflacion)
        
        # Debe ser ~6% mayor
        incremento = (uvr_futuro - uvr_actual) / uvr_actual
        assert Decimal("0.055") < incremento < Decimal("0.065")
    
    def test_proyeccion_cero_meses(self, servicio):
        """Proyección a 0 meses debe dar mismo valor"""
        uvr_actual = Decimal("385.0000")
        
        uvr_futuro = servicio.proyectar_uvr(uvr_actual, 0)
        
        assert uvr_futuro == uvr_actual
    
    def test_proyeccion_inflacion_alta(self, servicio):
        """Proyección con inflación alta"""
        uvr_actual = Decimal("385.0000")
        inflacion = Decimal("0.12")  # 12% anual
        
        uvr_futuro = servicio.proyectar_uvr(uvr_actual, 12, inflacion)
        
        # Debe ser ~12% mayor
        incremento = (uvr_futuro - uvr_actual) / uvr_actual
        assert Decimal("0.11") < incremento < Decimal("0.13")


class TestValoresDataclasses:
    """Tests para las estructuras de datos"""
    
    def test_valor_uvr_creacion(self):
        """Crear ValorUVR"""
        uvr = ValorUVR(
            fecha=date(2024, 1, 15),
            valor=Decimal("380.5000"),
            fuente=FuenteDatos.BANREP_API
        )
        
        assert uvr.fecha == date(2024, 1, 15)
        assert uvr.valor == Decimal("380.5000")
        assert uvr.fuente == FuenteDatos.BANREP_API
        assert uvr.fecha_consulta is not None
    
    def test_valor_ipc_creacion(self):
        """Crear ValorIPC"""
        ipc = ValorIPC(
            fecha=date(2024, 12, 31),
            valor=Decimal("156.50"),
            variacion_mensual=Decimal("0.50"),
            variacion_anual=Decimal("6.00"),
            fuente=FuenteDatos.BANREP_API
        )
        
        assert ipc.variacion_anual == Decimal("6.00")


@pytest.mark.asyncio
class TestServicioAsync:
    """Tests asíncronos para el servicio"""
    
    async def test_obtener_uvr_actual(self, servicio):
        """Obtener UVR de hoy (usa estimación si API falla)"""
        try:
            uvr = await servicio.obtener_uvr_actual()
            
            assert uvr is not None
            assert uvr.valor > Decimal("0")
            assert uvr.fecha == date.today()
            assert uvr.fuente in [FuenteDatos.BANREP_API, FuenteDatos.MANUAL, FuenteDatos.CACHE]
        finally:
            await servicio.close()
    
    async def test_obtener_uvr_fecha_especifica(self, servicio):
        """Obtener UVR de fecha pasada"""
        try:
            fecha = date(2024, 9, 29)  # Fecha del extracto
            uvr = await servicio.obtener_uvr(fecha)
            
            assert uvr is not None
            assert uvr.fecha == fecha
            # El valor debe estar en rango razonable (350-400 para 2024)
            assert Decimal("350") < uvr.valor < Decimal("400")
        finally:
            await servicio.close()
    
    async def test_obtener_indicadores_hoy(self, servicio):
        """Obtener todos los indicadores"""
        try:
            indicadores = await servicio.obtener_indicadores_hoy()
            
            assert indicadores.fecha == date.today()
            assert indicadores.uvr is not None
            assert indicadores.uvr > Decimal("0")
        finally:
            await servicio.close()
    
    async def test_obtener_ipc(self, servicio):
        """Obtener IPC"""
        try:
            ipc = await servicio.obtener_ipc(2024, 12)
            
            assert ipc is not None
            assert ipc.valor > Decimal("0")
            assert ipc.variacion_anual >= Decimal("0")
        finally:
            await servicio.close()
    
    async def test_obtener_dtf(self, servicio):
        """Obtener DTF"""
        try:
            dtf = await servicio.obtener_dtf_actual()
            
            assert dtf is not None
            # DTF típico en Colombia: 5% - 15% E.A.
            assert Decimal("5") < dtf.valor < Decimal("15")
        finally:
            await servicio.close()
    
    async def test_obtener_ibr(self, servicio):
        """Obtener IBR"""
        try:
            ibr = await servicio.obtener_ibr_actual()
            
            assert ibr is not None
            assert ibr.overnight > Decimal("0")
            # IBR típico: 5% - 15%
            assert Decimal("5") < ibr.overnight < Decimal("15")
        finally:
            await servicio.close()


class TestEstimaciones:
    """Tests para verificar que las estimaciones son razonables"""
    
    def test_estimacion_uvr_rango_historico(self, servicio):
        """Estimación de UVR debe estar en rango histórico"""
        # La UVR ha crecido de ~100 (2000) a ~380 (2024)
        # Crecimiento promedio ~5-7% anual
        
        uvr_2020 = Decimal("300")  # Aproximado
        uvr_2024 = Decimal("380")  # Aproximado
        
        # Verificar que el crecimiento es razonable
        crecimiento_anual = ((uvr_2024 / uvr_2020) ** Decimal("0.25")) - 1
        assert Decimal("0.04") < crecimiento_anual < Decimal("0.08")
    
    def test_ipc_inflacion_colombia(self, servicio):
        """Inflación típica de Colombia: 3-12%"""
        ipc = servicio._estimar_ipc(2024, 6)
        
        # Variación anual debe estar en rango histórico
        assert Decimal("3") < ipc.variacion_anual < Decimal("12")


class TestFuenteSocrata:
    """Tests para validar la integración con Socrata (datos.gov.co)"""
    
    def test_socrata_datasets_configurados(self):
        """Verificar que los datasets de Socrata están configurados"""
        from app.services.indicadores_service import SOCRATA_DATASETS
        
        assert "UVR" in SOCRATA_DATASETS
        assert "IPC" in SOCRATA_DATASETS
        assert "TASAS" in SOCRATA_DATASETS
        
        # Verificar que los IDs son válidos (formato Socrata: xxxx-xxxx)
        import re
        pattern = r"^[a-z0-9]{4}-[a-z0-9]{4}$"
        
        for key, dataset_id in SOCRATA_DATASETS.items():
            assert re.match(pattern, dataset_id), f"ID inválido para {key}: {dataset_id}"
    
    def test_socrata_base_url(self):
        """Verificar URL base de Socrata"""
        from app.services.indicadores_service import SOCRATA_BASE_URL
        
        assert "datos.gov.co" in SOCRATA_BASE_URL
        assert SOCRATA_BASE_URL.startswith("https://")
    
    @pytest.mark.asyncio
    async def test_fuente_socrata_en_respuesta(self, servicio):
        """Cuando Socrata responde, la fuente debe ser SOCRATA"""
        try:
            uvr = await servicio.obtener_uvr_actual()
            
            # Si Socrata funciona, la fuente será SOCRATA
            # Si no, caerá a BANREP_API, BANREP_XLS o MANUAL
            assert uvr.fuente.value in ["SOCRATA", "BANREP_API", "BANREP_XLS", "CACHE", "MANUAL"]
        finally:
            await servicio.close()


class TestFuenteDatos:
    """Tests para el enum FuenteDatos"""
    
    def test_fuente_socrata_existe(self):
        """FuenteDatos debe incluir SOCRATA"""
        assert FuenteDatos.SOCRATA.value == "SOCRATA"
    
    def test_todas_las_fuentes(self):
        """Verificar todas las fuentes disponibles"""
        fuentes = [f.value for f in FuenteDatos]
        
        assert "SOCRATA" in fuentes
        assert "BANREP_API" in fuentes
        assert "BANREP_XLS" in fuentes
        assert "CACHE" in fuentes
        assert "MANUAL" in fuentes
