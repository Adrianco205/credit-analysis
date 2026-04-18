"""
Motor de Cálculo Financiero - PerFinanzas
=========================================
El "cerebro" del sistema. Calcula amortización, proyecciones y ahorros.

Soporta dos sistemas:
- Sistema en Pesos: Amortización francesa estándar
- Sistema en UVR: Convierte a pesos usando valor UVR actual

Fórmulas clave:
- Cuota fija (francesa): C = P * [r(1+r)^n] / [(1+r)^n - 1]
- Tasa mensual: rm = (1 + EA)^(1/12) - 1
- Relación costo/saldo: costo_total_proyectado / saldo_credito_actual
- Honorarios: max(ahorro * 0.06, TARIFA_MINIMA)
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

PORCENTAJE_HONORARIOS = Decimal("0.05")  # 5% del saldo del crédito
PORCENTAJE_IVA = Decimal("0.19")  # 19% IVA Colombia
TARIFA_MINIMA_HONORARIOS = Decimal("500000")  # $500,000 COP mínimo
PORCENTAJE_INGRESO_MINIMO = Decimal("0.30")  # 30% de la cuota (Ley 546/99)
FRECH_MAX_MESES_DEFAULT = 84

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
    tasa_seguro_vida: Decimal = Decimal("0")
    valor_seguro_incendio_fijo: Decimal = Decimal("0")
    tasa_cobertura_frech: Decimal = Decimal("0")
    cargos_no_amortizables_mensuales: Decimal = Decimal("0")
    sistema_amortizacion: str = "PESOS"  # PESOS o UVR
    valor_uvr_actual: Optional[Decimal] = None
    saldo_uvr: Optional[Decimal] = None
    frech_meses_restantes: Optional[int] = None
    ipc_anual_proyectado: Decimal = Decimal("0.022")


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
    total_costos_no_amortizables: Decimal
    total_capital: Decimal
    tabla: List[FilaAmortizacion]
    total_subsidio_frech_dinamico: Decimal = Decimal("0")


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
    # Legacy aliases kept for backward compatibility with older mappers/serializers.
    total_por_pagar: Decimal  # Alias legacy de costo_total_proyectado
    total_por_pagar_simple: Decimal  # Alias legacy de total_por_pagar_aprox
    costo_total_proyectado: Decimal
    costo_total_proyectado_banco: Decimal
    total_subsidio_frech_proyectado: Decimal
    incluye_frech_en_costo_total_banco: bool
    total_intereses_proyectados: Decimal
    total_seguros_proyectados: Decimal
    valor_ahorrado_intereses: Decimal
    ahorro_total_proyectado: Decimal
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

    def _normalizar_sistema_amortizacion(self, sistema_amortizacion: str | None) -> str:
        """Normaliza variantes del sistema de amortizacion a PESOS o UVR."""
        sistema = (sistema_amortizacion or "PESOS").upper().strip()
        if sistema in {"PESOS", "CAPITAL"}:
            return "PESOS"
        return "UVR" if sistema == "UVR" else "PESOS"

    def calcular_tasa_inflacion_mensual(self, ipc_anual: Decimal) -> Decimal:
        """Calcula la tasa de inflacion mensual efectiva."""
        if ipc_anual <= 0:
            return Decimal("0")
        uno = Decimal("1")
        exponente = Decimal("1") / Decimal("12")
        base = uno + ipc_anual
        tasa_mensual = Decimal(str(float(base) ** float(exponente))) - uno
        return tasa_mensual.quantize(self._precision_tasa)

    def calcular_cuota_total_objetivo(
        self,
        saldo_capital: Decimal,
        tasa_interes_ea: Decimal,
        cuotas_objetivo: int,
        seguros_mensual: Decimal = Decimal("0"),
        cargos_no_amortizables_mensuales: Decimal = Decimal("0"),
    ) -> Decimal:
        """Calcula la cuota total mensual necesaria para amortizar en un numero objetivo de cuotas."""
        if saldo_capital <= 0 or cuotas_objetivo <= 0:
            return Decimal("0.00")

        tasa_mensual = self.tasa_ea_a_mensual(tasa_interes_ea)
        cuota_base = self.calcular_cuota_fija(saldo_capital, tasa_mensual, cuotas_objetivo)
        cuota_total = cuota_base + (seguros_mensual or Decimal("0")) + (cargos_no_amortizables_mensuales or Decimal("0"))
        return cuota_total.quantize(self._precision_dinero)

    def calcular_flujo_frech(
        self,
        beneficio_frech_mensual: Decimal,
        cuotas_proyectadas: int,
        frech_meses_restantes: int | None = None,
    ) -> Decimal:
        """Calcula el subsidio FRECH proyectado total (si aplica)."""
        if beneficio_frech_mensual <= 0 or cuotas_proyectadas <= 0:
            return Decimal("0.00")

        meses_subsidiados = cuotas_proyectadas
        if frech_meses_restantes is not None:
            try:
                meses_frech = int(frech_meses_restantes)
            except (TypeError, ValueError):
                meses_frech = cuotas_proyectadas
            meses_subsidiados = min(cuotas_proyectadas, max(0, meses_frech))
        else:
            logger.warning(
                "frech_meses_restantes es NULL; usando politica por defecto de %s meses",
                FRECH_MAX_MESES_DEFAULT,
            )
            meses_subsidiados = min(cuotas_proyectadas, FRECH_MAX_MESES_DEFAULT)

        return (beneficio_frech_mensual * Decimal(meses_subsidiados)).quantize(self._precision_dinero)

    def calcular_costo_total_proyectado(
        self,
        total_flujo_cliente: Decimal,
        beneficio_frech_mensual: Decimal,
        cuotas_proyectadas: int,
        frech_meses_restantes: int | None = None,
        total_subsidio_frech_dinamico: Decimal | None = None,
    ) -> tuple[Decimal, Decimal, Decimal]:
        """
        Separa el costo total proyectado en dos visiones:
        - cliente: lo que paga el cliente
        - banco: cliente + subsidio FRECH proyectado

        Nota: cuando frech_meses_restantes es NULL, se aplica la politica conservadora
        de tope FRECH (84 meses) para evitar sobreproyecciones.
        """
        costo_cliente = total_flujo_cliente.quantize(self._precision_dinero)
        if total_subsidio_frech_dinamico is not None:
            subsidio_frech = total_subsidio_frech_dinamico.quantize(self._precision_dinero)
        else:
            subsidio_frech = self.calcular_flujo_frech(
                beneficio_frech_mensual=beneficio_frech_mensual,
                cuotas_proyectadas=cuotas_proyectadas,
                frech_meses_restantes=frech_meses_restantes,
            )
        costo_banco = (costo_cliente + subsidio_frech).quantize(self._precision_dinero)
        return costo_cliente, costo_banco, subsidio_frech

    def _normalize_tasa_ea(self, tasa_ea: Decimal) -> Decimal:
        if tasa_ea <= 0:
            return Decimal("0")
        if tasa_ea > 1:
            tasa_normalizada = tasa_ea / Decimal("100")
        else:
            tasa_normalizada = tasa_ea
        return tasa_normalizada
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CONVERSIONES DE TASAS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def tasa_ea_a_mensual(self, tasa_ea: Decimal) -> Decimal:
        """
        Convierte tasa efectiva anual a tasa efectiva mensual.
        
        Fórmula: rm = (1 + EA)^(1/12) - 1
        
        Ejemplo: 4.71% EA → 0.3844% mensual
        """
        tasa_ea_normalizada = self._normalize_tasa_ea(tasa_ea)
        if tasa_ea_normalizada <= 0:
            return Decimal("0")
        
        # (1 + EA)^(1/12) - 1
        uno = Decimal("1")
        exponente = Decimal("1") / Decimal("12")
        base = uno + tasa_ea_normalizada
        
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
        tasa_seguro_vida: Decimal = Decimal("0"),
        valor_seguro_incendio_fijo: Decimal = Decimal("0"),
        cargos_no_amortizables_mensuales: Decimal = Decimal("0"),
        sistema_amortizacion: str = "PESOS",
        valor_uvr_actual: Decimal | None = None,
        max_cuotas: int = 600,  # Límite de seguridad (50 años)
        ipc_anual_proyectado: Decimal = Decimal("0.022"),
        tasa_cobertura_frech: Decimal = Decimal("0"),
        frech_meses_restantes: int | None = None,
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

        sistema_normalizado = self._normalizar_sistema_amortizacion(sistema_amortizacion)
        usa_uvr = sistema_normalizado == "UVR" and valor_uvr_actual is not None and valor_uvr_actual > 0
        factor_uvr = valor_uvr_actual if usa_uvr else Decimal("1")

        saldo = saldo_inicial / factor_uvr
        cuota_fija_unidad = cuota_fija / factor_uvr
        abono_extra_unidad = abono_extra / factor_uvr
        cargos_no_amortizables_unidad = cargos_no_amortizables_mensuales / factor_uvr

        total_intereses = Decimal("0")
        total_costos_no_amortizables = Decimal("0")
        total_capital = Decimal("0")
        total_pagado = Decimal("0")
        
        # Totales en pesos (salida)
        total_pagado_salida = Decimal("0")
        total_intereses_salida = Decimal("0")
        total_costos_no_amortizables_salida = Decimal("0")
        total_capital_salida = Decimal("0")
        
        cuota_num = 0
        
        # FRECH dinámico basado en cobertura de interés (si aplica)
        frech_meses_activos = 0
        if frech_meses_restantes is not None:
            try:
                frech_meses_activos = max(0, int(frech_meses_restantes))
            except (TypeError, ValueError):
                frech_meses_activos = 0
        tasa_mensual_frech = self.tasa_ea_a_mensual(tasa_cobertura_frech)
        total_subsidio_frech_salida = Decimal("0")
        
        tasa_inflacion_mensual = self.calcular_tasa_inflacion_mensual(ipc_anual_proyectado) if usa_uvr else Decimal("0")
        
        while saldo > Decimal("0.01") and cuota_num < max_cuotas:
            cuota_num += 1
            saldo_inicio_mes = saldo
            
            factor_uvr_dinamico = factor_uvr * Decimal(str(float(1 + tasa_inflacion_mensual) ** cuota_num)) if usa_uvr else Decimal("1")
            
            # Seguro dinámico mes a mes: vida sobre saldo + incendio fijo
            seguro_vida_unidad_mes = (saldo * tasa_seguro_vida).quantize(self._precision_tasa)
            seguro_incendio_unidad_mes = (valor_seguro_incendio_fijo / factor_uvr_dinamico).quantize(self._precision_tasa) if factor_uvr_dinamico > 0 else Decimal("0")
            seguros_unidad_total = seguro_vida_unidad_mes + seguro_incendio_unidad_mes
            
            # Interés del mes
            interes_mes = (saldo * tasa_mensual).quantize(self._precision_dinero)
            
            cargos_no_amortizables_unidad = (cargos_no_amortizables_mensuales / factor_uvr_dinamico).quantize(self._precision_dinero) if factor_uvr_dinamico > 0 else Decimal("0")
            abono_extra_real = (abono_extra / factor_uvr_dinamico).quantize(self._precision_dinero) if factor_uvr_dinamico > 0 else Decimal("0")
            
            # Abono a capital = (cuota - seguros) - interés
            abono_capital_base = (
                cuota_fija_unidad
                - seguros_unidad_total
                - cargos_no_amortizables_unidad
                - interes_mes
            )
            if abono_capital_base < 0:
                abono_capital_base = Decimal("0")
            
            # Si el saldo es menor que el abono, ajustar última cuota
            if saldo <= abono_capital_base + abono_extra_real:
                abono_capital_real = saldo
                abono_extra_real = Decimal("0")
                cuota_sin_seguros_real = interes_mes + saldo
                cuota_real = cuota_sin_seguros_real + seguros_unidad_total + cargos_no_amortizables_unidad
            else:
                abono_capital_real = abono_capital_base
                cuota_real = cuota_fija_unidad + abono_extra_real
            
            # Actualizar saldo
            saldo = saldo - abono_capital_real - abono_extra_real
            if saldo < 0:
                saldo = Decimal("0")
            
            # Acumular totales
            total_intereses += interes_mes
            total_costos_no_amortizables += seguros_unidad_total + cargos_no_amortizables_unidad
            total_capital += abono_capital_real + abono_extra_real
            total_pagado += cuota_real

            if tasa_mensual_frech > 0:
                limite_frech = frech_meses_activos if frech_meses_activos > 0 else FRECH_MAX_MESES_DEFAULT
                if cuota_num <= limite_frech:
                    alivio_frech_mes = (saldo_inicio_mes * tasa_mensual_frech).quantize(self._precision_dinero)
                    alivio_frech_salida = (alivio_frech_mes * factor_uvr_dinamico).quantize(self._precision_dinero)
                    total_subsidio_frech_salida += alivio_frech_salida
            
            # Convertir valores de iteración a pesos usando factor dinámico
            saldo_inicio_salida_val = (saldo_inicio_mes * factor_uvr_dinamico).quantize(self._precision_dinero)
            cuota_real_salida_val = (cuota_real * factor_uvr_dinamico).quantize(self._precision_dinero)
            interes_salida_val = (interes_mes * factor_uvr_dinamico).quantize(self._precision_dinero)
            abono_capital_salida_val = (abono_capital_real * factor_uvr_dinamico).quantize(self._precision_dinero)
            abono_extra_salida_val = (abono_extra_real * factor_uvr_dinamico).quantize(self._precision_dinero)
            saldo_salida_val = (saldo * factor_uvr_dinamico).quantize(self._precision_dinero)
            costos_no_amort_salida_val = ((seguros_unidad_total + cargos_no_amortizables_unidad) * factor_uvr_dinamico).quantize(self._precision_dinero)

            total_pagado_salida += cuota_real_salida_val
            total_intereses_salida += interes_salida_val
            total_capital_salida += abono_capital_salida_val + abono_extra_salida_val
            total_costos_no_amortizables_salida += costos_no_amort_salida_val

            # Agregar fila
            tabla.append(FilaAmortizacion(
                numero_cuota=cuota_num,
                saldo_inicial=saldo_inicio_salida_val,
                cuota_total=cuota_real_salida_val,
                interes=interes_salida_val,
                abono_capital=abono_capital_salida_val,
                abono_extra=abono_extra_salida_val,
                saldo_final=saldo_salida_val
            ))
        
        resultado = ResultadoAmortizacion(
            cuotas_totales=cuota_num,
            total_pagado=total_pagado_salida,
            total_intereses=total_intereses_salida,
            total_costos_no_amortizables=total_costos_no_amortizables_salida,
            total_capital=total_capital_salida,
            tabla=tabla,
            total_subsidio_frech_dinamico=total_subsidio_frech_salida.quantize(self._precision_dinero)
        )
        return resultado
    
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
        Calcula la proyeccion con un abono extra mensual.
        
        Compara el escenario actual (sin abono) vs con abono extra
        para determinar ahorros en tiempo e intereses.

        Semantica de costos:
        - total_por_pagar_simple: estimacion rapida (nueva_cuota x cuotas_nuevas)
        - costo_total_proyectado: suma real mes a mes de la tabla de amortizacion
        - costo_total_proyectado_banco: costo cliente + FRECH proyectado

        Por ajuste de ultima cuota, costo_total_proyectado puede quedar levemente
        por debajo del total simple; ese comportamiento es esperado.
        """
        tasa_mensual = self.tasa_ea_a_mensual(datos.tasa_interes_ea)
        
        # ═══════════════════════════════════════════════════════════════════
        # Escenario ACTUAL (sin abono extra)
        # ═══════════════════════════════════════════════════════════════════
        resultado_actual = self.generar_tabla_amortizacion(
            saldo_inicial=datos.saldo_capital,
            tasa_mensual=tasa_mensual,
            cuota_fija=datos.valor_cuota_actual,
            abono_extra=Decimal("0"),
            tasa_seguro_vida=datos.tasa_seguro_vida,
            valor_seguro_incendio_fijo=datos.valor_seguro_incendio_fijo,
            cargos_no_amortizables_mensuales=datos.cargos_no_amortizables_mensuales,
            sistema_amortizacion=datos.sistema_amortizacion,
            valor_uvr_actual=datos.valor_uvr_actual,
            ipc_anual_proyectado=datos.ipc_anual_proyectado,
            tasa_cobertura_frech=datos.tasa_cobertura_frech,
            frech_meses_restantes=datos.frech_meses_restantes,
        )
        
        # ═══════════════════════════════════════════════════════════════════
        # Escenario CON ABONO EXTRA
        # ═══════════════════════════════════════════════════════════════════
        resultado_con_abono = self.generar_tabla_amortizacion(
            saldo_inicial=datos.saldo_capital,
            tasa_mensual=tasa_mensual,
            cuota_fija=datos.valor_cuota_actual,
            abono_extra=abono_extra,
            tasa_seguro_vida=datos.tasa_seguro_vida,
            valor_seguro_incendio_fijo=datos.valor_seguro_incendio_fijo,
            cargos_no_amortizables_mensuales=datos.cargos_no_amortizables_mensuales,
            sistema_amortizacion=datos.sistema_amortizacion,
            valor_uvr_actual=datos.valor_uvr_actual,
            ipc_anual_proyectado=datos.ipc_anual_proyectado,
            tasa_cobertura_frech=datos.tasa_cobertura_frech,
            frech_meses_restantes=datos.frech_meses_restantes,
        )

        # Nueva cuota total (cuota base + abono extra)
        nueva_cuota = datos.valor_cuota_actual + abono_extra

        # Costo total proyectado del cliente: suma mes a mes de la amortizacion.
        costo_total_proyectado = resultado_con_abono.total_pagado

        sistema_normalizado = self._normalizar_sistema_amortizacion(datos.sistema_amortizacion)

        def _resolver_subsidio_frech(total_dinamico: Decimal, cuotas_totales: int) -> Decimal:
            if total_dinamico > 0:
                return total_dinamico.quantize(self._precision_dinero)
            if datos.beneficio_frech <= 0 or cuotas_totales <= 0:
                return Decimal("0.00")
            if sistema_normalizado == "PESOS":
                # Fallback comercial para PESOS cuando no hay cobertura FRECH explícita.
                return (datos.beneficio_frech * Decimal(cuotas_totales)).quantize(self._precision_dinero)
            return self.calcular_flujo_frech(
                beneficio_frech_mensual=datos.beneficio_frech,
                cuotas_proyectadas=cuotas_totales,
                frech_meses_restantes=datos.frech_meses_restantes,
            )

        total_subsidio_frech_actual = _resolver_subsidio_frech(
            resultado_actual.total_subsidio_frech_dinamico,
            resultado_actual.cuotas_totales,
        )
        total_subsidio_frech_proyectado = _resolver_subsidio_frech(
            resultado_con_abono.total_subsidio_frech_dinamico,
            resultado_con_abono.cuotas_totales,
        )

        # Baseline banco = flujo cliente + subsidio FRECH proyectado
        costo_total_actual_banco = (resultado_actual.total_pagado + total_subsidio_frech_actual).quantize(
            self._precision_dinero
        )

        # Costo proyectado banco = flujo cliente + subsidio FRECH proyectado
        costo_total_proyectado_banco = (resultado_con_abono.total_pagado + total_subsidio_frech_proyectado).quantize(
            self._precision_dinero
        )
        
        incluye_frech_en_costo_total_banco = total_subsidio_frech_proyectado > 0
        
        # ═══════════════════════════════════════════════════════════════════
        # CÁLCULOS DE AHORRO
        # ═══════════════════════════════════════════════════════════════════
        
        cuotas_reducidas = datos.cuotas_pendientes - resultado_con_abono.cuotas_totales
        if cuotas_reducidas < 0:
            cuotas_reducidas = 0
        tiempo_ahorrado = TiempoAhorro.desde_meses(cuotas_reducidas)
        tiempo_restante = TiempoAhorro.desde_meses(resultado_con_abono.cuotas_totales)
        
        # Semantica solicitada: ahorro visible = baseline banco - costo banco opcion.
        ahorro_intereses = (costo_total_actual_banco - costo_total_proyectado_banco).quantize(self._precision_dinero)
        ahorro_total_proyectado = (resultado_actual.total_pagado - resultado_con_abono.total_pagado).quantize(
            self._precision_dinero
        )
        
        # Total por pagar simple (estimacion rapida): cuota x cuotas.
        total_por_pagar_simple = costo_total_proyectado_banco

        # Indicador comercial "No. Veces Pagado": relacion entre costo total
        # integral (cliente + FRECH proyectado) y saldo de capital actual.
        if datos.saldo_capital > 0:
            veces_pagado = (costo_total_proyectado_banco / datos.saldo_capital).quantize(
                Decimal("0.01")
            )
        else:
            veces_pagado = Decimal("0")
        
        # ═══════════════════════════════════════════════════════════════════
        # HONORARIOS (5% del saldo capital actual o tarifa mínima)
        # ═══════════════════════════════════════════════════════════════════
        honorarios = self.calcular_honorarios(datos.saldo_capital)
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
            total_por_pagar=costo_total_proyectado,
            total_por_pagar_simple=total_por_pagar_simple,
            costo_total_proyectado=costo_total_proyectado,
            costo_total_proyectado_banco=costo_total_proyectado_banco,
            total_subsidio_frech_proyectado=total_subsidio_frech_proyectado,
            incluye_frech_en_costo_total_banco=incluye_frech_en_costo_total_banco,
            total_intereses_proyectados=resultado_con_abono.total_intereses,
            total_seguros_proyectados=resultado_con_abono.total_costos_no_amortizables,
            valor_ahorrado_intereses=ahorro_intereses,
            ahorro_total_proyectado=ahorro_total_proyectado,
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
        
        cuota_cliente = datos.valor_cuota_actual

        # Cuota completa informativa (cliente + FRECH)
        cuota_completa = cuota_cliente + datos.beneficio_frech
        
        # Pagado por el cliente (estimado)
        total_pagado_fecha = cuota_cliente * cuotas_pagadas
        
        # Total FRECH recibido
        total_frech_recibido = datos.beneficio_frech * cuotas_pagadas
        
        # Total abonado al crédito (cliente + FRECH)
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
            cuota_actual=cuota_cliente,
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
    
    def calcular_honorarios(self, saldo_capital: Decimal) -> Decimal:
        """
        Calcula honorarios: 5% del saldo capital o tarifa mínima.
        
        Regla: max(saldo_capital * 0.05, TARIFA_MINIMA)
        """
        honorarios = saldo_capital * PORCENTAJE_HONORARIOS
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
        tasa_seguro_vida=Decimal("0.0006"),
        valor_seguro_incendio_fijo=Decimal("21134"),
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
        print(f"Honorarios (5%): ${p.honorarios:,.0f}")
        print(f"Honorarios + IVA: ${p.honorarios_con_iva:,.0f}")
        print(f"Ingreso mínimo requerido: ${p.ingreso_minimo_requerido:,.0f}")

