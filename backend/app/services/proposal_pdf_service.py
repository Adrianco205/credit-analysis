"""
Servicio de Generación de PDF de Propuestas
============================================

Genera documentos PDF profesionales con la propuesta de reducción
de crédito hipotecario para el cliente.

Incluye:
- Resumen del crédito actual
- Comparativa de las 3 opciones de ahorro
- Tabla de beneficios por opción
- Honorarios y condiciones
- Información legal
"""
import io
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from dataclasses import dataclass

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DatosCredito:
    """Datos del crédito actual"""
    numero_credito: str
    banco: str
    saldo_capital: Decimal
    tasa_interes_ea: Decimal
    cuota_mensual: Decimal
    cuotas_pendientes: int
    cuotas_pagadas: int
    fecha_desembolso: Optional[date]
    sistema_amortizacion: str  # UVR o PESOS


@dataclass
class DatosCliente:
    """Datos del cliente"""
    nombre_completo: str
    cedula: str
    email: str
    telefono: Optional[str]
    ingresos_mensuales: Decimal


@dataclass
class OpcionAhorro:
    """Una opción de ahorro/abono extra"""
    numero_opcion: int
    nombre: str
    abono_extra_mensual: Decimal
    cuotas_nuevas: int
    tiempo_ahorrado_meses: int
    intereses_ahorrados: Decimal
    honorarios: Decimal
    honorarios_con_iva: Decimal
    ingreso_minimo_requerido: Decimal
    nueva_cuota: Decimal


@dataclass
class DatosPropuesta:
    """Todos los datos necesarios para generar la propuesta"""
    cliente: DatosCliente
    credito: DatosCredito
    opciones: List[OpcionAhorro]
    fecha_generacion: datetime
    numero_propuesta: str


# ═══════════════════════════════════════════════════════════════════════════════
# ESTILOS PERSONALIZADOS
# ═══════════════════════════════════════════════════════════════════════════════

def get_custom_styles():
    """Retorna estilos personalizados para el PDF"""
    styles = getSampleStyleSheet()
    
    # Título principal
    styles.add(ParagraphStyle(
        name='TituloPrincipal',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1B5E20'),  # Verde oscuro
    ))
    
    # Subtítulo
    styles.add(ParagraphStyle(
        name='Subtitulo',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        spaceBefore=20,
        textColor=colors.HexColor('#2E7D32'),  # Verde
    ))
    
    # Sección
    styles.add(ParagraphStyle(
        name='Seccion',
        parent=styles['Heading3'],
        fontSize=14,
        spaceAfter=10,
        spaceBefore=15,
        textColor=colors.HexColor('#388E3C'),
    ))
    
    # Texto normal
    styles.add(ParagraphStyle(
        name='TextoNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=8,
        alignment=TA_JUSTIFY,
        leading=14,
    ))
    
    # Texto destacado
    styles.add(ParagraphStyle(
        name='Destacado',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=8,
        textColor=colors.HexColor('#1B5E20'),
        fontName='Helvetica-Bold',
    ))
    
    # Pie de página
    styles.add(ParagraphStyle(
        name='PiePagina',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        alignment=TA_CENTER,
    ))
    
    # Nota legal
    styles.add(ParagraphStyle(
        name='NotaLegal',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#666666'),
        alignment=TA_JUSTIFY,
        leading=10,
    ))
    
    return styles


# ═══════════════════════════════════════════════════════════════════════════════
# GENERADOR DE PDF
# ═══════════════════════════════════════════════════════════════════════════════

class PropuestaPDFGenerator:
    """Generador de PDFs de propuestas de ahorro hipotecario"""
    
    def __init__(self):
        self.styles = get_custom_styles()
        
        # Colores corporativos
        self.verde_primario = colors.HexColor('#1B5E20')
        self.verde_claro = colors.HexColor('#E8F5E9')
        self.gris_claro = colors.HexColor('#F5F5F5')
    
    def generar_propuesta(self, datos: DatosPropuesta) -> bytes:
        """
        Genera el PDF de propuesta completo.
        
        Args:
            datos: Todos los datos necesarios para la propuesta
            
        Returns:
            bytes: Contenido del PDF en bytes
        """
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        # Construir contenido
        story = []
        
        # Encabezado
        story.extend(self._crear_encabezado(datos))
        
        # Datos del cliente
        story.extend(self._crear_seccion_cliente(datos.cliente))
        
        # Resumen del crédito actual
        story.extend(self._crear_seccion_credito(datos.credito))
        
        # Comparativa de opciones
        story.extend(self._crear_seccion_opciones(datos.opciones, datos.credito))
        
        # Detalle por opción
        story.extend(self._crear_detalle_opciones(datos.opciones))
        
        # Términos y condiciones
        story.extend(self._crear_terminos())
        
        # Pie con información de contacto
        story.extend(self._crear_pie(datos))
        
        # Generar PDF
        doc.build(story)
        
        buffer.seek(0)
        return buffer.getvalue()
    
    def _crear_encabezado(self, datos: DatosPropuesta) -> List:
        """Crea el encabezado del documento"""
        elementos = []
        
        # Logo/Nombre de la empresa
        elementos.append(Paragraph(
            "🏠 EcoFinanzas",
            self.styles['TituloPrincipal']
        ))
        
        elementos.append(Paragraph(
            "Propuesta de Optimización de Crédito Hipotecario",
            self.styles['Subtitulo']
        ))
        
        # Información de la propuesta
        info_propuesta = f"""
        <b>Propuesta N°:</b> {datos.numero_propuesta}<br/>
        <b>Fecha de generación:</b> {datos.fecha_generacion.strftime('%d de %B de %Y')}<br/>
        <b>Válida hasta:</b> {(datos.fecha_generacion.replace(day=1) + 
            __import__('datetime').timedelta(days=32)).replace(day=1).strftime('%d de %B de %Y')}
        """
        elementos.append(Paragraph(info_propuesta, self.styles['TextoNormal']))
        
        elementos.append(HRFlowable(
            width="100%",
            thickness=2,
            color=self.verde_primario,
            spaceAfter=20
        ))
        
        return elementos
    
    def _crear_seccion_cliente(self, cliente: DatosCliente) -> List:
        """Crea la sección de datos del cliente"""
        elementos = []
        
        elementos.append(Paragraph("📋 Datos del Cliente", self.styles['Seccion']))
        
        data = [
            ['Nombre completo:', cliente.nombre_completo],
            ['Cédula:', cliente.cedula],
            ['Email:', cliente.email],
            ['Teléfono:', cliente.telefono or 'No registrado'],
            ['Ingresos mensuales:', f"${cliente.ingresos_mensuales:,.0f} COP"],
        ]
        
        tabla = Table(data, colWidths=[2.5*inch, 4*inch])
        tabla.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), self.verde_primario),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elementos.append(tabla)
        elementos.append(Spacer(1, 15))
        
        return elementos
    
    def _crear_seccion_credito(self, credito: DatosCredito) -> List:
        """Crea la sección de resumen del crédito actual"""
        elementos = []
        
        elementos.append(Paragraph("🏦 Su Crédito Actual", self.styles['Seccion']))
        
        # Calcular tiempo restante
        años_restantes = credito.cuotas_pendientes // 12
        meses_restantes = credito.cuotas_pendientes % 12
        tiempo_restante = f"{años_restantes} años y {meses_restantes} meses"
        
        data = [
            ['Banco:', credito.banco],
            ['Número de crédito:', credito.numero_credito],
            ['Sistema:', credito.sistema_amortizacion],
            ['Saldo actual:', f"${credito.saldo_capital:,.0f} COP"],
            ['Tasa de interés:', f"{credito.tasa_interes_ea:.2f}% E.A."],
            ['Cuota mensual:', f"${credito.cuota_mensual:,.0f} COP"],
            ['Cuotas pendientes:', f"{credito.cuotas_pendientes} ({tiempo_restante})"],
            ['Cuotas pagadas:', str(credito.cuotas_pagadas)],
        ]
        
        if credito.fecha_desembolso:
            data.append(['Fecha desembolso:', credito.fecha_desembolso.strftime('%d/%m/%Y')])
        
        tabla = Table(data, colWidths=[2.5*inch, 4*inch])
        tabla.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), self.verde_primario),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 3), (-1, 3), self.verde_claro),  # Destacar saldo
        ]))
        
        elementos.append(tabla)
        elementos.append(Spacer(1, 20))
        
        return elementos
    
    def _crear_seccion_opciones(self, opciones: List[OpcionAhorro], credito: DatosCredito) -> List:
        """Crea la tabla comparativa de opciones"""
        elementos = []
        
        elementos.append(Paragraph("📊 Comparativa de Opciones de Ahorro", self.styles['Seccion']))
        
        elementos.append(Paragraph(
            """A continuación se presentan las opciones de ahorro según los montos de abono extra 
            que usted indicó. Cada opción muestra cuánto tiempo y dinero puede ahorrar 
            realizando pagos adicionales a su cuota mensual.""",
            self.styles['TextoNormal']
        ))
        
        # Encabezados de la tabla
        headers = ['Concepto', 'Sin abono\n(Actual)'] + [
            f"Opción {op.numero_opcion}\n(+${op.abono_extra_mensual:,.0f})"
            for op in opciones
        ]
        
        # Filas de datos
        años_actual = credito.cuotas_pendientes // 12
        meses_actual = credito.cuotas_pendientes % 12
        
        data = [headers]
        
        # Tiempo restante
        tiempo_actual = f"{años_actual}a {meses_actual}m"
        row_tiempo = ['Tiempo restante', tiempo_actual]
        for op in opciones:
            años = op.cuotas_nuevas // 12
            meses = op.cuotas_nuevas % 12
            row_tiempo.append(f"{años}a {meses}m")
        data.append(row_tiempo)
        
        # Tiempo ahorrado
        row_ahorro_tiempo = ['Tiempo ahorrado', '-']
        for op in opciones:
            años = op.tiempo_ahorrado_meses // 12
            meses = op.tiempo_ahorrado_meses % 12
            row_ahorro_tiempo.append(f"{años}a {meses}m")
        data.append(row_ahorro_tiempo)
        
        # Intereses ahorrados
        row_intereses = ['Intereses ahorrados', '-']
        for op in opciones:
            row_intereses.append(f"${op.intereses_ahorrados:,.0f}")
        data.append(row_intereses)
        
        # Nueva cuota total
        row_cuota = ['Nueva cuota mensual', f"${credito.cuota_mensual:,.0f}"]
        for op in opciones:
            row_cuota.append(f"${op.nueva_cuota:,.0f}")
        data.append(row_cuota)
        
        # Ingreso mínimo
        row_ingreso = ['Ingreso mínimo req.', '-']
        for op in opciones:
            row_ingreso.append(f"${op.ingreso_minimo_requerido:,.0f}")
        data.append(row_ingreso)
        
        # Crear tabla
        col_widths = [1.8*inch] + [1.4*inch] * (len(opciones) + 1)
        tabla = Table(data, colWidths=col_widths)
        
        tabla.setStyle(TableStyle([
            # Encabezado
            ('BACKGROUND', (0, 0), (-1, 0), self.verde_primario),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Cuerpo
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            
            # Bordes
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            
            # Destacar fila de intereses ahorrados
            ('BACKGROUND', (0, 3), (-1, 3), self.verde_claro),
            
            # Alternar colores
            ('BACKGROUND', (0, 1), (-1, 1), self.gris_claro),
            ('BACKGROUND', (0, 5), (-1, 5), self.gris_claro),
        ]))
        
        elementos.append(tabla)
        elementos.append(Spacer(1, 20))
        
        return elementos
    
    def _crear_detalle_opciones(self, opciones: List[OpcionAhorro]) -> List:
        """Crea el detalle de cada opción con honorarios"""
        elementos = []
        
        elementos.append(Paragraph("💰 Detalle de Honorarios por Opción", self.styles['Seccion']))
        
        elementos.append(Paragraph(
            """Los honorarios de EcoFinanzas corresponden al 3% del total de intereses 
            que usted dejará de pagar al banco. Solo paga si obtiene un beneficio real.""",
            self.styles['TextoNormal']
        ))
        
        for op in opciones:
            elementos.append(Paragraph(
                f"<b>Opción {op.numero_opcion}: {op.nombre}</b>",
                self.styles['Destacado']
            ))
            
            data = [
                ['Abono extra mensual:', f"${op.abono_extra_mensual:,.0f} COP"],
                ['Intereses que dejará de pagar:', f"${op.intereses_ahorrados:,.0f} COP"],
                ['Honorarios (3%):', f"${op.honorarios:,.0f} COP"],
                ['IVA (19%):', f"${(op.honorarios_con_iva - op.honorarios):,.0f} COP"],
                ['Total honorarios con IVA:', f"${op.honorarios_con_iva:,.0f} COP"],
            ]
            
            tabla = Table(data, colWidths=[3*inch, 3*inch])
            tabla.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BACKGROUND', (0, -1), (-1, -1), self.verde_claro),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ]))
            
            elementos.append(tabla)
            elementos.append(Spacer(1, 15))
        
        return elementos
    
    def _crear_terminos(self) -> List:
        """Crea la sección de términos y condiciones"""
        elementos = []
        
        elementos.append(Paragraph("📜 Términos y Condiciones", self.styles['Seccion']))
        
        terminos = """
        <b>1. Vigencia:</b> Esta propuesta tiene una vigencia de 30 días calendario a partir de 
        la fecha de generación.<br/><br/>
        
        <b>2. Aprobación bancaria:</b> La reducción de cuotas está sujeta a la aprobación del 
        banco emisor del crédito. EcoFinanzas realizará las gestiones necesarias pero no 
        garantiza la aprobación.<br/><br/>
        
        <b>3. Requisitos:</b> Para proceder con la gestión, el cliente debe:<br/>
        - Demostrar ingresos iguales o superiores al mínimo requerido según la opción elegida.<br/>
        - Estar al día con los pagos del crédito.<br/>
        - Firmar el contrato de servicios de EcoFinanzas.<br/><br/>
        
        <b>4. Honorarios:</b> Los honorarios de EcoFinanzas corresponden al 3% del total de 
        intereses ahorrados, más IVA (19%). El pago se realiza una vez el banco apruebe 
        formalmente la modificación del crédito.<br/><br/>
        
        <b>5. Ley aplicable:</b> Los cálculos se realizan conforme a la Ley 546 de 1999 y 
        demás normativa vigente en Colombia sobre créditos hipotecarios.
        """
        
        elementos.append(Paragraph(terminos, self.styles['NotaLegal']))
        elementos.append(Spacer(1, 20))
        
        return elementos
    
    def _crear_pie(self, datos: DatosPropuesta) -> List:
        """Crea el pie del documento"""
        elementos = []
        
        elementos.append(HRFlowable(
            width="100%",
            thickness=1,
            color=colors.grey,
            spaceBefore=20,
            spaceAfter=10
        ))
        
        pie = f"""
        <b>EcoFinanzas</b> - Optimización de Créditos Hipotecarios<br/>
        📧 contacto@ecofinanzas.com | 📱 (+57) 300-123-4567<br/>
        Documento generado automáticamente el {datos.fecha_generacion.strftime('%d/%m/%Y %H:%M')}<br/>
        Propuesta N° {datos.numero_propuesta}
        """
        
        elementos.append(Paragraph(pie, self.styles['PiePagina']))
        
        return elementos


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE CONVENIENCIA
# ═══════════════════════════════════════════════════════════════════════════════

def crear_generador_propuesta() -> PropuestaPDFGenerator:
    """Factory function para crear el generador"""
    return PropuestaPDFGenerator()


def generar_numero_propuesta(analisis_id: str, fecha: datetime) -> str:
    """Genera un número de propuesta único"""
    return f"ECO-{fecha.strftime('%Y%m%d')}-{analisis_id[:8].upper()}"
