import re
import sys

with open('backend/app/services/calc_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace variables before while
old_before_while = """        tasa_mensual_frech = self.tasa_ea_a_mensual(tasa_cobertura_frech)
        total_subsidio_frech_salida = Decimal("0")
        
        # Seguro de incendio fijo convertido con factor estático
        seguro_incendio_unidad_mes = (valor_seguro_incendio_fijo / factor_uvr).quantize(self._precision_tasa)
        
        # Abono extra en unidad estática
        abono_extra_real = abono_extra_unidad
        
        while saldo > Decimal("0.01") and cuota_num < max_cuotas:"""

new_before_while = """        tasa_mensual_frech = self.tasa_ea_a_mensual(tasa_cobertura_frech)
        total_subsidio_frech_salida = Decimal("0")
        
        tasa_inflacion_mensual = self.calcular_tasa_inflacion_mensual(ipc_anual_proyectado) if usa_uvr else Decimal("0")
        
        while saldo > Decimal("0.01") and cuota_num < max_cuotas:"""

content = content.replace(old_before_while, new_before_while)


# Replace logic inside while
old_while_inside = """        while saldo > Decimal("0.01") and cuota_num < max_cuotas:
            cuota_num += 1
            saldo_inicio_mes = saldo
            
            # Seguro dinámico mes a mes: vida sobre saldo + incendio fijo
            seguro_vida_unidad_mes = (saldo * tasa_seguro_vida).quantize(self._precision_tasa)
            seguros_unidad_total = seguro_vida_unidad_mes + seguro_incendio_unidad_mes
            
            # Interés del mes
            interes_mes = (saldo * tasa_mensual).quantize(self._precision_dinero)
            
            # Abono a capital = (cuota - seguros) - interés
            abono_capital_base = (
                cuota_fija_unidad
                - seguros_unidad_total
                - cargos_no_amortizables_unidad
                - interes_mes
            )"""

new_while_inside = """        while saldo > Decimal("0.01") and cuota_num < max_cuotas:
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
            )"""

content = content.replace(old_while_inside, new_while_inside)

old_salida = """            if tasa_mensual_frech > 0:
                limite_frech = frech_meses_activos if frech_meses_activos > 0 else FRECH_MAX_MESES_DEFAULT
                if cuota_num <= limite_frech:
                    alivio_frech_mes = (saldo_inicio_mes * tasa_mensual_frech).quantize(self._precision_dinero)
                    alivio_frech_salida = (alivio_frech_mes * factor_uvr).quantize(self._precision_dinero)
                    total_subsidio_frech_salida += alivio_frech_salida
            
            # Convertir valores de iteración a pesos usando factor estático
            saldo_inicio_salida_val = (saldo_inicio_mes * factor_uvr).quantize(self._precision_dinero)
            cuota_real_salida_val = (cuota_real * factor_uvr).quantize(self._precision_dinero)
            interes_salida_val = (interes_mes * factor_uvr).quantize(self._precision_dinero)
            abono_capital_salida_val = (abono_capital_real * factor_uvr).quantize(self._precision_dinero)
            abono_extra_salida_val = (abono_extra_real * factor_uvr).quantize(self._precision_dinero)
            saldo_salida_val = (saldo * factor_uvr).quantize(self._precision_dinero)
            costos_no_amort_salida_val = ((seguros_unidad_total + cargos_no_amortizables_unidad) * factor_uvr).quantize(self._precision_dinero)"""

new_salida = """            if tasa_mensual_frech > 0:
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
            costos_no_amort_salida_val = ((seguros_unidad_total + cargos_no_amortizables_unidad) * factor_uvr_dinamico).quantize(self._precision_dinero)"""

content = content.replace(old_salida, new_salida)

with open('backend/app/services/calc_service.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated UVR loop correctly.")
