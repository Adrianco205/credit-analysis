"""
Motor de Cálculo Financiero - EcoFinanzas
=========================================
El "cerebro" del sistema. Calcula amortización, proyecciones y ahorros.

Soporta dos sistemas:
- Sistema en Pesos: Amortización francesa estándar
- Sistema en UVR: Convierte a pesos usando valor UVR actual

Fórmulas clave:
- Cuota fija (francesa): C = P * [r(1+r)^n] / [(1+r)^n - 1]
- Tasa mensual: rm = (1 + EA)^(1/12) - 1
- Veces pagado: total_pagado / valor_prestado_inicial
- Honorarios: max(ahorro * 0.03, TARIFA_MINIMA)
- Ingreso mínimo: nueva_cuota / 0.30
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

PORCENTAJE_HONORARIOS = Decimal("0.03")  # 3% del ahorro
PORCENTAJE_IVA = Decimal("0.19")  # 19% IVA Colombia
TARIFA_MINIMA_HONORARIOS = Decimal("500000")  # $500,000 COP mínimo
PORCENTAJE_INGRESO_MINIMO = Decimal("0.30")  # 30% de la cuota (Ley 546/99)

# Precisión para cálculos monetarios
PRECISION_DINERO = Decimal("0.01")
PRECISION_TASA = Decimal("0.000001")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DatosCredito:
    """Datos del crédito necesarios para cálculos"""
    saldo_capital: Decimal
    valor_cuota_actual: Decimal  # Cuota que paga el cliente (con subsidio si aplica)
    cuotas_pendientes: int
    tasa_interes_ea: Decimal  # Tasa efectiva anual (ej: 0.0471 para 4.71%)
    valor_prestado_inicial: Decimal
    
    # Opcionales
    beneficio_frech: Decimal = Decimal("0")
    seguros_mensual: Decimal = Decimal("0")
    sistema_amortizacion: str = "PESOS"  # PESOS o UVR
    valor_uvr_actual: Optional[Decimal] = None
    saldo_uvr: Optional[Decimal] = None


@dataclass
class FilaAmortizacion:
    """Una fila de la tabla de amortización"""
    numero_cuota: int
    saldo_inicial: Decimal
    cuota_total: Decimal
    interes: Decimal
    abono_capital: Decimal
    abono_extra: Decimal
    saldo_final: Decimal


@dataclass
class ResultadoAmortizacion:
    """Resultado del cálculo de amortización"""
    cuotas_totales: int
    total_pagado: Decimal
    total_intereses: Decimal
    total_capital: Decimal
    tabla: List[FilaAmortizacion]


@dataclass
class TiempoAhorro:
    """Representa tiempo en años y meses"""
    anios: int
    meses: int
    
    @property
    def total_meses(self) -> int:
        return (self.anios * 12) + self.meses
    
    @classmethod
    def desde_meses(cls, total_meses: int) -> "TiempoAhorro":
        return cls(anios=total_meses // 12, meses=total_meses % 12)
    
    def __str__(self) -> str:
        return f"{self.anios} años, {self.meses} meses"


@dataclass
class ResultadoProyeccion:
    """Resultado de una proyección con abono extra"""
    numero_opcion: int
    nombre_opcion: str
    abono_adicional: Decimal
    
    # Tiempo
    cuotas_nuevas: int
    tiempo_restante: TiempoAhorro
    cuotas_reducidas: int
    tiempo_ahorrado: TiempoAhorro
    
    # Dinero
    nuevo_valor_cuota: Decimal
    total_por_pagar: Decimal
    valor_ahorrado_intereses: Decimal
    veces_pagado: Decimal
    
    # Honorarios y requisitos
    honorarios: Decimal
    honorarios_con_iva: Decimal
    ingreso_minimo_requerido: Decimal


@dataclass
class ResumenCredito:
    """Resumen del crédito en 4 bloques"""
    # Bloque 1: Datos Básicos
    valor_prestado: Decimal
    cuotas_pactadas: int
    cuotas_pagadas: int
    cuotas_por_pagar: int
    cuota_actual: Decimal
    beneficio_frech: Decimal
    cuota_completa: Decimal  # Sin subsidio
    total_pagado_fecha: Decimal
    total_frech_recibido: Decimal
    monto_real_pagado_banco: Decimal
    
    # Bloque 2: Límites con el Banco
    saldo_actual: Decimal
    
    # Bloque 3: Ajuste Inflación (UVR)
    ajuste_inflacion_pesos: Decimal
    porcentaje_ajuste: Decimal
    
    # Bloque 4: Costos Extra
    total_intereses_seguros: Decimal


# ═══════════════════════════════════════════════════════════════════════════════
# CLASE PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class CalculadoraFinanciera:
    """
    Motor de cálculo financiero para créditos hipotecarios.
    
    Uso:
        calc = CalculadoraFinanciera()
        datos = DatosCredito(...)
        resultado = calc.calcular_proyeccion(datos, abono_extra=200000)
    """
    
    def __init__(self):
        self._precision_dinero = PRECISION_DINERO
        self._precision_tasa = PRECISION_TASA
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CONVERSIONES DE TASAS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def tasa_ea_a_mensual(self, tasa_ea: Decimal) -> Decimal:
        """
        Convierte tasa efectiva anual a tasa efectiva mensual.
        
        Fórmula: rm = (1 + EA)^(1/12) - 1
        
        Ejemplo: 4.71% EA → 0.3844% mensual
        """
        if tasa_ea <= 0:
            return Decimal("0")
        
        # (1 + EA)^(1/12) - 1
        uno = Decimal("1")
        exponente = Decimal("1") / Decimal("12")
        base = uno + tasa_ea
        
        # Usamos float para la potencia fraccionaria y volvemos a Decimal
        tasa_mensual = Decimal(str(float(base) ** float(exponente))) - uno
        return tasa_mensual.quantize(self._precision_tasa)
    
    def tasa_mensual_a_ea(self, tasa_mensual: Decimal) -> Decimal:
        """
        Convierte tasa mensual a efectiva anual.
        
        Fórmula: EA = (1 + rm)^12 - 1
        """
        if tasa_mensual <= 0:
            return Decimal("0")
        
        uno = Decimal("1")
        ea = Decimal(str((float(uno + tasa_mensual) ** 12))) - uno
        return ea.quantize(self._precision_tasa)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CÁLCULO DE CUOTA (SISTEMA FRANCÉS)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def calcular_cuota_fija(
        self, 
        capital: Decimal, 
        tasa_mensual: Decimal, 
        num_cuotas: int
    ) -> Decimal:
        """
        Calcula la cuota fija mensual (sistema francés).
        
        Fórmula: C = P * [r(1+r)^n] / [(1+r)^n - 1]
        
        Donde:
            P = Capital (saldo)
            r = Tasa mensual
            n = Número de cuotas
        """
        if capital <= 0 or num_cuotas <= 0:
            return Decimal("0")
        
        if tasa_mensual <= 0:
            # Sin interés, cuota = capital / cuotas
            return (capital / num_cuotas).quantize(self._precision_dinero)
        
        r = tasa_mensual
        n = num_cuotas
        
        # (1 + r)^n
        factor = Decimal(str((1 + float(r)) ** n))
        
        # C = P * [r * factor] / [factor - 1]
        numerador = capital * r * factor
        denominador = factor - 1
        
        cuota = numerador / denominador
        return cuota.quantize(self._precision_dinero, rounding=ROUND_HALF_UP)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TABLA DE AMORTIZACIÓN
    # ═══════════════════════════════════════════════════════════════════════════
    
    def generar_tabla_amortizacion(
        self,
        saldo_inicial: Decimal,
        tasa_mensual: Decimal,
        cuota_fija: Decimal,
        abono_extra: Decimal = Decimal("0"),
        max_cuotas: int = 600  # Límite de seguridad (50 años)
    ) -> ResultadoAmortizacion:
        """
        Genera la tabla de amortización completa.
        
        Args:
            saldo_inicial: Saldo de capital actual
            tasa_mensual: Tasa de interés mensual
            cuota_fija: Cuota mensual base (sin abono extra)
            abono_extra: Abono adicional mensual a capital
            max_cuotas: Límite máximo de cuotas
            
        Returns:
            ResultadoAmortizacion con tabla completa y totales
        """
        tabla: List[FilaAmortizacion] = []
        saldo = saldo_inicial
        total_intereses = Decimal("0")
        total_capital = Decimal("0")
        total_pagado = Decimal("0")
        cuota_num = 0
        
        while saldo > Decimal("0.01") and cuota_num < max_cuotas:
            cuota_num += 1
            saldo_inicio_mes = saldo
            
            # Interés del mes
            interes_mes = (saldo * tasa_mensual).quantize(self._precision_dinero)
            
            # Abono a capital = cuota - interés
            abono_capital_base = cuota_fija - interes_mes
            
            # Si el saldo es menor que el abono, ajustar última cuota
            if saldo <= abono_capital_base + abono_extra:
                abono_capital_real = saldo
                abono_extra_real = Decimal("0")
                cuota_real = interes_mes + saldo
            else:
                abono_capital_real = abono_capital_base
                abono_extra_real = abono_extra
                cuota_real = cuota_fija + abono_extra
            
            # Actualizar saldo
            saldo = saldo - abono_capital_real - abono_extra_real
            if saldo < 0:
                saldo = Decimal("0")
            
            # Acumular totales
            total_intereses += interes_mes
            total_capital += abono_capital_real + abono_extra_real
            total_pagado += cuota_real
            
            # Agregar fila
            tabla.append(FilaAmortizacion(
                numero_cuota=cuota_num,
                saldo_inicial=saldo_inicio_mes,
                cuota_total=cuota_real,
                interes=interes_mes,
                abono_capital=abono_capital_real,
                abono_extra=abono_extra_real,
                saldo_final=saldo
            ))
        
        return ResultadoAmortizacion(
            cuotas_totales=cuota_num,
            total_pagado=total_pagado.quantize(self._precision_dinero),
            total_intereses=total_intereses.quantize(self._precision_dinero),
            total_capital=total_capital.quantize(self._precision_dinero),
            tabla=tabla
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CÁLCULO DE PROYECCIÓN CON ABONO EXTRA
    # ═══════════════════════════════════════════════════════════════════════════
    
    def calcular_proyeccion(
        self,
        datos: DatosCredito,
        abono_extra: Decimal,
        numero_opcion: int = 1,
        nombre_opcion: str = "Opción"
    ) -> ResultadoProyeccion:
        """
        Calcula la proyección con un abono extra mensual.
        
        Compara el escenario actual (sin abono) vs con abono extra
        para determinar ahorros en tiempo e intereses.
        """
        tasa_mensual = self.tasa_ea_a_mensual(datos.tasa_interes_ea)
        
        # ═══════════════════════════════════════════════════════════════════
        # Escenario ACTUAL (sin abono extra)
        # ═══════════════════════════════════════════════════════════════════
        resultado_actual = self.generar_tabla_amortizacion(
            saldo_inicial=datos.saldo_capital,
            tasa_mensual=tasa_mensual,
            cuota_fija=datos.valor_cuota_actual,
            abono_extra=Decimal("0")
        )
        
        # ═══════════════════════════════════════════════════════════════════
        # Escenario CON ABONO EXTRA
        # ═══════════════════════════════════════════════════════════════════
        resultado_con_abono = self.generar_tabla_amortizacion(
            saldo_inicial=datos.saldo_capital,
            tasa_mensual=tasa_mensual,
            cuota_fija=datos.valor_cuota_actual,
            abono_extra=abono_extra
        )
        
        # ═══════════════════════════════════════════════════════════════════
        # CÁLCULOS DE AHORRO
        # ═══════════════════════════════════════════════════════════════════
        
        cuotas_reducidas = resultado_actual.cuotas_totales - resultado_con_abono.cuotas_totales
        tiempo_ahorrado = TiempoAhorro.desde_meses(cuotas_reducidas)
        tiempo_restante = TiempoAhorro.desde_meses(resultado_con_abono.cuotas_totales)
        
        # Ahorro en intereses
        ahorro_intereses = resultado_actual.total_intereses - resultado_con_abono.total_intereses
        
        # Nueva cuota total (cuota base + abono extra)
        nueva_cuota = datos.valor_cuota_actual + abono_extra
        
        # Veces pagado = total pagado / valor prestado inicial
        veces_pagado = (resultado_con_abono.total_pagado / datos.valor_prestado_inicial).quantize(
            Decimal("0.01")
        )
        
        # ═══════════════════════════════════════════════════════════════════
        # HONORARIOS (3% del ahorro o tarifa mínima)
        # ═══════════════════════════════════════════════════════════════════
        honorarios = self.calcular_honorarios(ahorro_intereses)
        honorarios_con_iva = self.calcular_honorarios_con_iva(honorarios)
        
        # ═══════════════════════════════════════════════════════════════════
        # INGRESO MÍNIMO REQUERIDO (30% de la nueva cuota - Ley 546/99)
        # ═══════════════════════════════════════════════════════════════════
        ingreso_minimo = self.calcular_ingreso_minimo(nueva_cuota)
        
        return ResultadoProyeccion(
            numero_opcion=numero_opcion,
            nombre_opcion=nombre_opcion,
            abono_adicional=abono_extra,
            cuotas_nuevas=resultado_con_abono.cuotas_totales,
            tiempo_restante=tiempo_restante,
            cuotas_reducidas=cuotas_reducidas,
            tiempo_ahorrado=tiempo_ahorrado,
            nuevo_valor_cuota=nueva_cuota,
            total_por_pagar=resultado_con_abono.total_pagado,
            valor_ahorrado_intereses=ahorro_intereses,
            veces_pagado=veces_pagado,
            honorarios=honorarios,
            honorarios_con_iva=honorarios_con_iva,
            ingreso_minimo_requerido=ingreso_minimo
        )
    
    def generar_proyecciones_multiple(
        self,
        datos: DatosCredito,
        abonos: List[Decimal]
    ) -> List[ResultadoProyeccion]:
        """
        Genera múltiples proyecciones para diferentes abonos.
        
        Args:
            datos: Datos del crédito
            abonos: Lista de abonos extras a simular (ej: [200000, 300000, 400000])
            
        Returns:
            Lista de ResultadoProyeccion, una por cada abono
        """
        proyecciones = []
        nombres = ["1a Elección", "2a Elección", "3a Elección", "4a Elección", "5a Elección"]
        
        for i, abono in enumerate(abonos):
            nombre = nombres[i] if i < len(nombres) else f"Opción {i + 1}"
            proyeccion = self.calcular_proyeccion(
                datos=datos,
                abono_extra=abono,
                numero_opcion=i + 1,
                nombre_opcion=nombre
            )
            proyecciones.append(proyeccion)
        
        return proyecciones
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CÁLCULO DE RESUMEN (4 BLOQUES)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def calcular_resumen_credito(
        self,
        datos: DatosCredito,
        cuotas_pagadas: int,
        cuotas_pactadas: int
    ) -> ResumenCredito:
        """
        Genera el resumen del crédito en 4 bloques para la UI.
        
        Bloques:
        1. DATOS BÁSICOS: Cuotas, valor prestado, FRECH
        2. LÍMITES CON EL BANCO: Saldo actual
        3. AJUSTE POR INFLACIÓN: Solo para UVR
        4. COSTOS EXTRA: Intereses y seguros
        """
        cuotas_por_pagar = cuotas_pactadas - cuotas_pagadas
        
        # Cuota completa (sin subsidio FRECH)
        cuota_completa = datos.valor_cuota_actual + datos.beneficio_frech
        
        # Total pagado a la fecha
        total_pagado_fecha = datos.valor_cuota_actual * cuotas_pagadas
        
        # Total FRECH recibido
        total_frech_recibido = datos.beneficio_frech * cuotas_pagadas
        
        # Monto real pagado al banco (incluye FRECH)
        monto_real_pagado_banco = total_pagado_fecha + total_frech_recibido
        
        # Ajuste por inflación (diferencia entre saldo actual y valor prestado)
        # Si es positivo, la deuda creció por inflación (típico en UVR)
        ajuste_inflacion = datos.saldo_capital - datos.valor_prestado_inicial
        
        # Porcentaje de ajuste
        if datos.valor_prestado_inicial > 0:
            porcentaje_ajuste = (ajuste_inflacion / datos.valor_prestado_inicial).quantize(
                Decimal("0.0001")
            )
        else:
            porcentaje_ajuste = Decimal("0")
        
        # Costos extra (estimado de intereses y seguros pagados)
        # = Total pagado - Capital amortizado estimado
        capital_amortizado_estimado = datos.valor_prestado_inicial - datos.saldo_capital
        total_intereses_seguros = monto_real_pagado_banco - capital_amortizado_estimado
        if total_intereses_seguros < 0:
            total_intereses_seguros = Decimal("0")
        
        return ResumenCredito(
            valor_prestado=datos.valor_prestado_inicial,
            cuotas_pactadas=cuotas_pactadas,
            cuotas_pagadas=cuotas_pagadas,
            cuotas_por_pagar=cuotas_por_pagar,
            cuota_actual=datos.valor_cuota_actual,
            beneficio_frech=datos.beneficio_frech,
            cuota_completa=cuota_completa,
            total_pagado_fecha=total_pagado_fecha,
            total_frech_recibido=total_frech_recibido,
            monto_real_pagado_banco=monto_real_pagado_banco,
            saldo_actual=datos.saldo_capital,
            ajuste_inflacion_pesos=ajuste_inflacion,
            porcentaje_ajuste=porcentaje_ajuste,
            total_intereses_seguros=total_intereses_seguros
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HONORARIOS Y REQUISITOS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def calcular_honorarios(self, ahorro_total: Decimal) -> Decimal:
        """
        Calcula honorarios: 3% del ahorro o tarifa mínima.
        
        Regla: max(ahorro * 0.03, TARIFA_MINIMA)
        """
        honorarios = ahorro_total * PORCENTAJE_HONORARIOS
        return max(honorarios, TARIFA_MINIMA_HONORARIOS).quantize(self._precision_dinero)
    
    def calcular_honorarios_con_iva(self, honorarios: Decimal) -> Decimal:
        """Agrega IVA (19%) a los honorarios"""
        return (honorarios * (1 + PORCENTAJE_IVA)).quantize(self._precision_dinero)
    
    def calcular_ingreso_minimo(self, cuota_mensual: Decimal) -> Decimal:
        """
        Calcula el ingreso mínimo requerido según Ley 546/99.
        
        Regla: La cuota no puede superar el 30% del ingreso.
        Entonces: Ingreso mínimo = Cuota / 0.30
        """
        if PORCENTAJE_INGRESO_MINIMO <= 0:
            return Decimal("0")
        
        ingreso = cuota_mensual / PORCENTAJE_INGRESO_MINIMO
        return ingreso.quantize(self._precision_dinero)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CONVERSIÓN UVR
    # ═══════════════════════════════════════════════════════════════════════════
    
    def convertir_uvr_a_pesos(self, saldo_uvr: Decimal, valor_uvr: Decimal) -> Decimal:
        """Convierte saldo en UVR a pesos colombianos"""
        return (saldo_uvr * valor_uvr).quantize(self._precision_dinero)
    
    def convertir_pesos_a_uvr(self, saldo_pesos: Decimal, valor_uvr: Decimal) -> Decimal:
        """Convierte saldo en pesos a UVR"""
        if valor_uvr <= 0:
            return Decimal("0")
        return (saldo_pesos / valor_uvr).quantize(Decimal("0.0001"))


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN DE CONVENIENCIA
# ═══════════════════════════════════════════════════════════════════════════════

def crear_calculadora() -> CalculadoraFinanciera:
    """Factory function para crear una instancia de la calculadora"""
    return CalculadoraFinanciera()


# ═══════════════════════════════════════════════════════════════════════════════
# EJEMPLO DE USO (para testing)
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Datos del extracto Bancolombia de la imagen
    calc = CalculadoraFinanciera()
    
    datos = DatosCredito(
        saldo_capital=Decimal("56069733.47"),  # Saldo a la fecha
        valor_cuota_actual=Decimal("305034.17"),  # Cuota con subsidio
        cuotas_pendientes=325,
        tasa_interes_ea=Decimal("0.0471"),  # 4.71% EA (tasa cobrada)
        valor_prestado_inicial=Decimal("45200180"),
        beneficio_frech=Decimal("183855.65"),
        seguros_mensual=Decimal("21134"),  # Vida + Incendio + Terremoto
        sistema_amortizacion="UVR"
    )
    
    print("=" * 70)
    print("RESUMEN DEL CRÉDITO")
    print("=" * 70)
    
    resumen = calc.calcular_resumen_credito(datos, cuotas_pagadas=35, cuotas_pactadas=360)
    print(f"Valor prestado: ${resumen.valor_prestado:,.2f}")
    print(f"Cuotas: {resumen.cuotas_pagadas}/{resumen.cuotas_pactadas} (faltan {resumen.cuotas_por_pagar})")
    print(f"Cuota actual: ${resumen.cuota_actual:,.2f}")
    print(f"Beneficio FRECH: ${resumen.beneficio_frech:,.2f}")
    print(f"Saldo actual: ${resumen.saldo_actual:,.2f}")
    print(f"Ajuste inflación: ${resumen.ajuste_inflacion_pesos:,.2f} ({resumen.porcentaje_ajuste:.2%})")
    
    print("\n" + "=" * 70)
    print("PROYECCIONES (NUEVAS OPORTUNIDADES)")
    print("=" * 70)
    
    # Simular 3 opciones de abono
    abonos = [Decimal("233027"), Decimal("265076"), Decimal("304632")]
    proyecciones = calc.generar_proyecciones_multiple(datos, abonos)
    
    for p in proyecciones:
        print(f"\n--- {p.nombre_opcion} ---")
        print(f"Abono adicional: ${p.abono_adicional:,.0f}")
        print(f"Nueva cuota: ${p.nuevo_valor_cuota:,.0f}")
        print(f"Cuotas nuevas: {p.cuotas_nuevas} ({p.tiempo_restante})")
        print(f"Cuotas reducidas: {p.cuotas_reducidas}")
        print(f"Tiempo ahorrado: {p.tiempo_ahorrado}")
        print(f"Ahorro en intereses: ${p.valor_ahorrado_intereses:,.0f}")
        print(f"Veces pagado: {p.veces_pagado}")
        print(f"Honorarios (3%): ${p.honorarios:,.0f}")
        print(f"Honorarios + IVA: ${p.honorarios_con_iva:,.0f}")
        print(f"Ingreso mínimo requerido: ${p.ingreso_minimo_requerido:,.0f}")
