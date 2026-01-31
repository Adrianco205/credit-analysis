"""
Tests para el Motor de Cálculo Financiero.
Usa datos reales del extracto Bancolombia como caso de prueba.
"""
import pytest
from decimal import Decimal
from app.services.calc_service import (
    CalculadoraFinanciera,
    DatosCredito,
    TiempoAhorro,
    PORCENTAJE_HONORARIOS,
    TARIFA_MINIMA_HONORARIOS,
)


@pytest.fixture
def calculadora():
    """Fixture para instanciar la calculadora"""
    return CalculadoraFinanciera()


@pytest.fixture
def datos_extracto_bancolombia():
    """
    Datos reales del extracto Bancolombia de la imagen.
    Crédito UVR con beneficio FRECH.
    """
    return DatosCredito(
        saldo_capital=Decimal("56069733.47"),
        valor_cuota_actual=Decimal("305034.17"),
        cuotas_pendientes=325,
        tasa_interes_ea=Decimal("0.0471"),  # 4.71% EA
        valor_prestado_inicial=Decimal("45200180"),
        beneficio_frech=Decimal("183855.65"),
        seguros_mensual=Decimal("21134"),
        sistema_amortizacion="UVR",
        valor_uvr_actual=Decimal("376.1794"),
        saldo_uvr=Decimal("149292.3850")
    )


class TestConversionTasas:
    """Tests para conversión de tasas de interés"""
    
    def test_tasa_ea_a_mensual(self, calculadora):
        """4.71% EA debe convertir a ~0.384% mensual"""
        tasa_ea = Decimal("0.0471")
        tasa_mensual = calculadora.tasa_ea_a_mensual(tasa_ea)
        
        # Verificar que está en rango esperado (0.38% - 0.39%)
        assert Decimal("0.0038") < tasa_mensual < Decimal("0.0039")
    
    def test_tasa_mensual_a_ea(self, calculadora):
        """Conversión inversa debe dar el mismo resultado"""
        tasa_ea_original = Decimal("0.0471")
        tasa_mensual = calculadora.tasa_ea_a_mensual(tasa_ea_original)
        tasa_ea_calculada = calculadora.tasa_mensual_a_ea(tasa_mensual)
        
        # Debe ser aproximadamente igual (tolerancia por redondeo)
        diferencia = abs(tasa_ea_original - tasa_ea_calculada)
        assert diferencia < Decimal("0.0001")
    
    def test_tasa_cero(self, calculadora):
        """Tasa 0% debe retornar 0"""
        assert calculadora.tasa_ea_a_mensual(Decimal("0")) == Decimal("0")


class TestCuotaFija:
    """Tests para cálculo de cuota sistema francés"""
    
    def test_cuota_fija_basica(self, calculadora):
        """Verificar fórmula de cuota fija"""
        capital = Decimal("100000000")  # 100 millones
        tasa_mensual = Decimal("0.01")  # 1% mensual
        num_cuotas = 120  # 10 años
        
        cuota = calculadora.calcular_cuota_fija(capital, tasa_mensual, num_cuotas)
        
        # La cuota debe ser mayor que capital/cuotas (porque incluye interés)
        cuota_sin_interes = capital / num_cuotas
        assert cuota > cuota_sin_interes
        
        # Verificar que está en rango razonable
        assert Decimal("1000000") < cuota < Decimal("2000000")
    
    def test_cuota_sin_interes(self, calculadora):
        """Sin interés, cuota = capital / cuotas"""
        capital = Decimal("12000000")
        num_cuotas = 12
        
        cuota = calculadora.calcular_cuota_fija(capital, Decimal("0"), num_cuotas)
        
        assert cuota == Decimal("1000000.00")


class TestTablaAmortizacion:
    """Tests para generación de tabla de amortización"""
    
    def test_tabla_amortizacion_basica(self, calculadora):
        """La tabla debe terminar con saldo 0"""
        resultado = calculadora.generar_tabla_amortizacion(
            saldo_inicial=Decimal("10000000"),
            tasa_mensual=Decimal("0.01"),
            cuota_fija=Decimal("500000"),
            abono_extra=Decimal("0")
        )
        
        # Última fila debe tener saldo final ~ 0
        ultima_fila = resultado.tabla[-1]
        assert ultima_fila.saldo_final < Decimal("1")
        
        # Total capital pagado debe igualar saldo inicial
        assert abs(resultado.total_capital - Decimal("10000000")) < Decimal("1")
    
    def test_abono_extra_reduce_cuotas(self, calculadora):
        """Abono extra debe reducir número de cuotas"""
        saldo = Decimal("10000000")
        tasa = Decimal("0.01")
        cuota = Decimal("500000")
        
        resultado_sin_abono = calculadora.generar_tabla_amortizacion(
            saldo, tasa, cuota, Decimal("0")
        )
        resultado_con_abono = calculadora.generar_tabla_amortizacion(
            saldo, tasa, cuota, Decimal("100000")
        )
        
        assert resultado_con_abono.cuotas_totales < resultado_sin_abono.cuotas_totales
    
    def test_abono_extra_reduce_intereses(self, calculadora):
        """Abono extra debe reducir total de intereses"""
        saldo = Decimal("10000000")
        tasa = Decimal("0.01")
        cuota = Decimal("500000")
        
        resultado_sin = calculadora.generar_tabla_amortizacion(
            saldo, tasa, cuota, Decimal("0")
        )
        resultado_con = calculadora.generar_tabla_amortizacion(
            saldo, tasa, cuota, Decimal("100000")
        )
        
        assert resultado_con.total_intereses < resultado_sin.total_intereses


class TestProyeccion:
    """Tests para proyecciones con datos reales"""
    
    def test_proyeccion_reduce_tiempo(self, calculadora, datos_extracto_bancolombia):
        """Proyección con abono debe reducir tiempo"""
        proyeccion = calculadora.calcular_proyeccion(
            datos_extracto_bancolombia,
            abono_extra=Decimal("200000"),
            numero_opcion=1
        )
        
        # Debe reducir cuotas
        assert proyeccion.cuotas_nuevas < datos_extracto_bancolombia.cuotas_pendientes
        assert proyeccion.cuotas_reducidas > 0
        
    def test_proyeccion_ahorra_intereses(self, calculadora, datos_extracto_bancolombia):
        """Proyección con abono debe ahorrar intereses"""
        proyeccion = calculadora.calcular_proyeccion(
            datos_extracto_bancolombia,
            abono_extra=Decimal("200000"),
            numero_opcion=1
        )
        
        # Debe tener ahorro positivo
        assert proyeccion.valor_ahorrado_intereses > Decimal("0")
    
    def test_proyeccion_nueva_cuota(self, calculadora, datos_extracto_bancolombia):
        """Nueva cuota = cuota actual + abono extra"""
        abono = Decimal("200000")
        proyeccion = calculadora.calcular_proyeccion(
            datos_extracto_bancolombia,
            abono_extra=abono,
            numero_opcion=1
        )
        
        cuota_esperada = datos_extracto_bancolombia.valor_cuota_actual + abono
        assert proyeccion.nuevo_valor_cuota == cuota_esperada
    
    def test_proyecciones_multiples(self, calculadora, datos_extracto_bancolombia):
        """Generar 3 proyecciones diferentes"""
        abonos = [Decimal("200000"), Decimal("300000"), Decimal("400000")]
        proyecciones = calculadora.generar_proyecciones_multiple(
            datos_extracto_bancolombia,
            abonos
        )
        
        assert len(proyecciones) == 3
        
        # A mayor abono, mayor ahorro
        assert proyecciones[0].valor_ahorrado_intereses < proyecciones[1].valor_ahorrado_intereses
        assert proyecciones[1].valor_ahorrado_intereses < proyecciones[2].valor_ahorrado_intereses
        
        # A mayor abono, menos cuotas
        assert proyecciones[0].cuotas_nuevas > proyecciones[1].cuotas_nuevas
        assert proyecciones[1].cuotas_nuevas > proyecciones[2].cuotas_nuevas


class TestHonorarios:
    """Tests para cálculo de honorarios"""
    
    def test_honorarios_3_porciento(self, calculadora):
        """Honorarios = 3% del ahorro"""
        ahorro = Decimal("100000000")  # 100 millones
        honorarios = calculadora.calcular_honorarios(ahorro)
        
        esperado = ahorro * PORCENTAJE_HONORARIOS
        assert honorarios == esperado.quantize(Decimal("0.01"))
    
    def test_honorarios_minimo(self, calculadora):
        """Honorarios no pueden ser menor que tarifa mínima"""
        ahorro_bajo = Decimal("1000000")  # 1 millón (3% = 30,000)
        honorarios = calculadora.calcular_honorarios(ahorro_bajo)
        
        # Debe aplicar tarifa mínima
        assert honorarios == TARIFA_MINIMA_HONORARIOS
    
    def test_honorarios_con_iva(self, calculadora):
        """Honorarios + IVA = Honorarios * 1.19"""
        honorarios_base = Decimal("1000000")
        con_iva = calculadora.calcular_honorarios_con_iva(honorarios_base)
        
        esperado = honorarios_base * Decimal("1.19")
        assert con_iva == esperado.quantize(Decimal("0.01"))


class TestIngresoMinimo:
    """Tests para cálculo de ingreso mínimo (Ley 546/99)"""
    
    def test_ingreso_minimo_30_porciento(self, calculadora):
        """Ingreso mínimo = cuota / 0.30"""
        cuota = Decimal("600000")
        ingreso = calculadora.calcular_ingreso_minimo(cuota)
        
        esperado = cuota / Decimal("0.30")
        assert ingreso == esperado.quantize(Decimal("0.01"))
    
    def test_ingreso_minimo_valores_reales(self, calculadora, datos_extracto_bancolombia):
        """Test con valores del extracto real"""
        proyeccion = calculadora.calcular_proyeccion(
            datos_extracto_bancolombia,
            abono_extra=Decimal("200000"),
            numero_opcion=1
        )
        
        # Verificar que ingreso mínimo > cuota
        assert proyeccion.ingreso_minimo_requerido > proyeccion.nuevo_valor_cuota


class TestResumenCredito:
    """Tests para generación de resumen (4 bloques)"""
    
    def test_resumen_datos_basicos(self, calculadora, datos_extracto_bancolombia):
        """Bloque 1: Datos básicos correctos"""
        resumen = calculadora.calcular_resumen_credito(
            datos_extracto_bancolombia,
            cuotas_pagadas=35,
            cuotas_pactadas=360
        )
        
        assert resumen.valor_prestado == datos_extracto_bancolombia.valor_prestado_inicial
        assert resumen.cuotas_pactadas == 360
        assert resumen.cuotas_pagadas == 35
        assert resumen.cuotas_por_pagar == 325
    
    def test_resumen_ajuste_inflacion(self, calculadora, datos_extracto_bancolombia):
        """Bloque 3: Ajuste inflación para UVR"""
        resumen = calculadora.calcular_resumen_credito(
            datos_extracto_bancolombia,
            cuotas_pagadas=35,
            cuotas_pactadas=360
        )
        
        # El saldo actual > valor prestado (típico en UVR)
        assert resumen.ajuste_inflacion_pesos > Decimal("0")
        
        # El porcentaje debe ser ~24% según el extracto
        assert Decimal("0.20") < resumen.porcentaje_ajuste < Decimal("0.30")


class TestTiempoAhorro:
    """Tests para la estructura TiempoAhorro"""
    
    def test_desde_meses_basico(self):
        """Convertir meses a años+meses"""
        tiempo = TiempoAhorro.desde_meses(27)
        
        assert tiempo.anios == 2
        assert tiempo.meses == 3
        assert tiempo.total_meses == 27
    
    def test_desde_meses_exacto(self):
        """Años exactos sin meses sobrantes"""
        tiempo = TiempoAhorro.desde_meses(24)
        
        assert tiempo.anios == 2
        assert tiempo.meses == 0
    
    def test_string_format(self):
        """Formato legible"""
        tiempo = TiempoAhorro(anios=16, meses=4)
        assert str(tiempo) == "16 años, 4 meses"


class TestConversionUVR:
    """Tests para conversión UVR <-> Pesos"""
    
    def test_uvr_a_pesos(self, calculadora):
        """Saldo UVR * Valor UVR = Saldo Pesos"""
        saldo_uvr = Decimal("149292.3850")
        valor_uvr = Decimal("376.1794")
        
        pesos = calculadora.convertir_uvr_a_pesos(saldo_uvr, valor_uvr)
        
        # Debe ser aproximadamente 56 millones (según extracto)
        assert Decimal("56000000") < pesos < Decimal("57000000")
    
    def test_pesos_a_uvr(self, calculadora):
        """Conversión inversa"""
        saldo_pesos = Decimal("56069733.47")
        valor_uvr = Decimal("376.1794")
        
        uvr = calculadora.convertir_pesos_a_uvr(saldo_pesos, valor_uvr)
        
        # Debe ser aproximadamente 149,292 UVR
        assert Decimal("149000") < uvr < Decimal("150000")
