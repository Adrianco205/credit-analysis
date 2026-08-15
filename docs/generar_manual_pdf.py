"""Genera el PDF del manual de usuario del módulo de Proyección Manual.

Aplica la paleta oficial de PerFinanzas definida en frontend/app/globals.css.
Uso:  python docs/generar_manual_pdf.py
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# ── Paleta oficial PerFinanzas ────────────────────────────────────────────────
VERDE_BOSQUE = colors.HexColor("#1B5E20")
VERDE_HOJA = colors.HexColor("#4CAF50")
VERDE_CLARO = colors.HexColor("#66BB6A")
VERDE_SUAVE = colors.HexColor("#E8F5E9")
BLANCO = colors.HexColor("#FFFFFF")

GRIS_50 = colors.HexColor("#F9FAFB")
GRIS_200 = colors.HexColor("#E5E7EB")
GRIS_500 = colors.HexColor("#6B7280")
GRIS_700 = colors.HexColor("#374151")
GRIS_900 = colors.HexColor("#111827")

ADVERTENCIA = colors.HexColor("#FBA500")
ADVERTENCIA_BG = colors.HexColor("#FFF7E6")
ERROR = colors.HexColor("#DC2626")
ERROR_BG = colors.HexColor("#FEF2F2")
INFO = colors.HexColor("#0284C7")
INFO_BG = colors.HexColor("#EFF6FF")

ANCHO_UTIL = LETTER[0] - 4 * cm

# ── Estilos ───────────────────────────────────────────────────────────────────
_base = getSampleStyleSheet()

S = {
    "portada_titulo": ParagraphStyle(
        "pt", parent=_base["Title"], fontName="Helvetica-Bold", fontSize=30,
        leading=36, textColor=BLANCO, alignment=TA_CENTER, spaceAfter=6),
    "portada_sub": ParagraphStyle(
        "ps", parent=_base["Normal"], fontName="Helvetica", fontSize=14,
        leading=20, textColor=VERDE_SUAVE, alignment=TA_CENTER),
    "portada_meta": ParagraphStyle(
        "pm", parent=_base["Normal"], fontName="Helvetica", fontSize=10.5,
        leading=17, textColor=GRIS_700, alignment=TA_CENTER),
    "capitulo": ParagraphStyle(
        "cap", parent=_base["Heading1"], fontName="Helvetica-Bold", fontSize=17,
        leading=21, textColor=VERDE_BOSQUE, spaceBefore=4, spaceAfter=2),
    "seccion": ParagraphStyle(
        "sec", parent=_base["Heading2"], fontName="Helvetica-Bold", fontSize=12,
        leading=15, textColor=VERDE_BOSQUE, spaceBefore=2, spaceAfter=2),
    "rotulo": ParagraphStyle(
        "rot", parent=_base["Normal"], fontName="Helvetica-Bold", fontSize=9,
        leading=12, textColor=VERDE_BOSQUE, spaceBefore=8, spaceAfter=3),
    "cuerpo": ParagraphStyle(
        "cue", parent=_base["Normal"], fontName="Helvetica", fontSize=9.5,
        leading=14, textColor=GRIS_700, alignment=TA_JUSTIFY, spaceAfter=6),
    "vineta": ParagraphStyle(
        "vin", parent=_base["Normal"], fontName="Helvetica", fontSize=9.5,
        leading=14, textColor=GRIS_700, leftIndent=12, bulletIndent=2, spaceAfter=3),
    "celda": ParagraphStyle(
        "cel", parent=_base["Normal"], fontName="Helvetica", fontSize=8.5,
        leading=11.5, textColor=GRIS_700),
    "celda_campo": ParagraphStyle(
        "celc", parent=_base["Normal"], fontName="Helvetica-Bold", fontSize=8.5,
        leading=11.5, textColor=GRIS_900),
    "th": ParagraphStyle(
        "th", parent=_base["Normal"], fontName="Helvetica-Bold", fontSize=8.5,
        leading=11, textColor=BLANCO),
    "callout": ParagraphStyle(
        "cal", parent=_base["Normal"], fontName="Helvetica", fontSize=9,
        leading=13, textColor=GRIS_900),
    "callout_titulo": ParagraphStyle(
        "calt", parent=_base["Normal"], fontName="Helvetica-Bold", fontSize=8.5,
        leading=12, textColor=GRIS_900, spaceAfter=2),
    "mono": ParagraphStyle(
        "mon", parent=_base["Normal"], fontName="Courier", fontSize=9,
        leading=13, textColor=GRIS_900),
    "pie": ParagraphStyle(
        "pie", parent=_base["Normal"], fontName="Helvetica", fontSize=8,
        textColor=GRIS_500, alignment=TA_CENTER),
}

OBLIGATORIO = f' <font color="#DC2626"><b>*</b></font>'


# ── Bloques constructivos ─────────────────────────────────────────────────────
def capitulo(num, titulo):
    """Encabezado de capítulo con barra inferior en verde hoja."""
    barra = Table([[""]], colWidths=[ANCHO_UTIL], rowHeights=[2.5])
    barra.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), VERDE_HOJA),
                               ("LINEBELOW", (0, 0), (-1, -1), 0, BLANCO)]))
    return [Spacer(1, 14), Paragraph(f"{num}. {titulo}", S["capitulo"]), barra, Spacer(1, 10)]


def seccion(titulo):
    """Subtítulo tipo tarjeta con fondo verde suave."""
    t = Table([[Paragraph(titulo, S["seccion"])]], colWidths=[ANCHO_UTIL])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), VERDE_SUAVE),
        ("LINEBEFORE", (0, 0), (0, -1), 3, VERDE_CLARO),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return [Spacer(1, 8), t, Spacer(1, 7)]


def parrafo(texto):
    return Paragraph(texto, S["cuerpo"])


def rotulo(texto):
    return Paragraph(texto, S["rotulo"])


def vinetas(items):
    return [Paragraph(i, S["vineta"], bulletText="•") for i in items]


def tabla_campos(filas, encabezados=("Campo", "Qué registrar")):
    """Tabla de campos: encabezado verde bosque, filas alternas gris 50."""
    data = [[Paragraph(encabezados[0], S["th"]), Paragraph(encabezados[1], S["th"])]]
    for campo, obligatorio, desc in filas:
        etiqueta = campo + (OBLIGATORIO if obligatorio else "")
        data.append([Paragraph(etiqueta, S["celda_campo"]), Paragraph(desc, S["celda"])])

    t = Table(data, colWidths=[ANCHO_UTIL * 0.30, ANCHO_UTIL * 0.70], repeatRows=1)
    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), VERDE_BOSQUE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, GRIS_200),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            estilo.append(("BACKGROUND", (0, i), (-1, i), GRIS_50))
    t.setStyle(TableStyle(estilo))
    return t


def tabla_datos(encabezados, filas, anchos=None, alinear_der=None):
    """Tabla genérica de datos numéricos."""
    data = [[Paragraph(h, S["th"]) for h in encabezados]]
    for fila in filas:
        data.append([Paragraph(str(c), S["celda"]) for c in fila])
    anchos = anchos or [ANCHO_UTIL / len(encabezados)] * len(encabezados)
    t = Table(data, colWidths=anchos, repeatRows=1)
    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), VERDE_BOSQUE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, GRIS_200),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            estilo.append(("BACKGROUND", (0, i), (-1, i), GRIS_50))
    for col in (alinear_der or []):
        estilo.append(("ALIGN", (col, 1), (col, -1), "RIGHT"))
    t.setStyle(TableStyle(estilo))
    return t


def caja(tipo, titulo, cuerpo):
    """Caja de aviso con borde izquierdo de color según el tipo."""
    paleta = {
        "advertencia": (ADVERTENCIA_BG, ADVERTENCIA),
        "error": (ERROR_BG, ERROR),
        "buena": (VERDE_SUAVE, VERDE_HOJA),
        "info": (INFO_BG, INFO),
    }
    fondo, borde = paleta[tipo]
    contenido = []
    if titulo:
        contenido.append(Paragraph(titulo.upper(), S["callout_titulo"]))
    if isinstance(cuerpo, str):
        cuerpo = [cuerpo]
    for c in cuerpo:
        contenido.append(Paragraph(c, S["callout"]))

    t = Table([[contenido]], colWidths=[ANCHO_UTIL])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), fondo),
        ("LINEBEFORE", (0, 0), (0, -1), 4, borde),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return KeepTogether([Spacer(1, 4), t, Spacer(1, 8)])


def bloque_codigo(lineas):
    t = Table([[Paragraph(l, S["mono"])] for l in lineas], colWidths=[ANCHO_UTIL])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GRIS_50),
        ("BOX", (0, 0), (-1, -1), 0.5, GRIS_200),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return KeepTogether([Spacer(1, 4), t, Spacer(1, 8)])


# ── Página ────────────────────────────────────────────────────────────────────
def decorar(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setStrokeColor(GRIS_200)
        canvas.setLineWidth(0.5)
        canvas.line(2 * cm, 1.8 * cm, LETTER[0] - 2 * cm, 1.8 * cm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GRIS_500)
        canvas.drawString(2 * cm, 1.3 * cm, "PerFinanzas  |  Manual del Módulo de Proyección Manual")
        canvas.drawRightString(LETTER[0] - 2 * cm, 1.3 * cm, str(doc.page))
        # Franja superior de identidad
        canvas.setFillColor(VERDE_BOSQUE)
        canvas.rect(0, LETTER[1] - 0.45 * cm, LETTER[0], 0.45 * cm, stroke=0, fill=1)
    canvas.restoreState()


def portada(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(VERDE_BOSQUE)
    canvas.rect(0, LETTER[1] - 11 * cm, LETTER[0], 11 * cm, stroke=0, fill=1)
    canvas.setFillColor(VERDE_HOJA)
    canvas.rect(0, LETTER[1] - 11.35 * cm, LETTER[0], 0.35 * cm, stroke=0, fill=1)

    canvas.setFillColor(BLANCO)
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawCentredString(LETTER[0] / 2, LETTER[1] - 2.8 * cm, "PERFINANZAS")
    canvas.setFont("Helvetica", 9.5)
    canvas.setFillColor(VERDE_SUAVE)
    canvas.drawCentredString(LETTER[0] / 2, LETTER[1] - 3.5 * cm, "Panel de Administración")

    canvas.setFillColor(BLANCO)
    canvas.setFont("Helvetica-Bold", 27)
    canvas.drawCentredString(LETTER[0] / 2, LETTER[1] - 6.2 * cm, "Manual de Usuario")
    canvas.setFont("Helvetica-Bold", 19)
    canvas.setFillColor(VERDE_CLARO)
    canvas.drawCentredString(LETTER[0] / 2, LETTER[1] - 7.6 * cm, "Módulo de Proyección Manual")

    canvas.setFillColor(GRIS_500)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(LETTER[0] / 2, 1.6 * cm,
                             "Documento de uso interno  |  Version 1.0")
    canvas.restoreState()


def construir():
    salida = Path(__file__).with_name("Manual_Proyeccion_Manual_PerFinanzas.pdf")
    doc = BaseDocTemplate(
        str(salida), pagesize=LETTER,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2.2 * cm,
        title="Manual de Usuario - Modulo de Proyeccion Manual",
        author="PerFinanzas", subject="Guia de uso del modulo de proyeccion manual",
    )
    marco = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([
        PageTemplate(id="portada", frames=[marco], onPage=portada),
        PageTemplate(id="contenido", frames=[marco], onPage=decorar),
    ])

    E = []  # elementos

    # ── PORTADA ──────────────────────────────────────────────────────────────
    E.append(Spacer(1, 12.5 * cm))
    E.append(Paragraph(
        "Guía completa para crear análisis de crédito hipotecario digitando "
        "manualmente la información del extracto.", S["portada_meta"]))
    E.append(Spacer(1, 1.2 * cm))
    E.append(tabla_datos(
        ["", ""],
        [["Dirigido a", "Administradores de PerFinanzas"],
         ["Requisito de acceso", "Rol ADMIN"],
         ["Ruta del módulo", "/dashboard/admin/proyeccion-manual"],
         ["Versión", "1.0"]],
        anchos=[ANCHO_UTIL * 0.35, ANCHO_UTIL * 0.65]))
    # Sin esto reportlab mantiene la plantilla de portada en todo el documento:
    # el banner verde se repetiría y no saldrían los números de página.
    E.append(NextPageTemplate("contenido"))
    E.append(PageBreak())

    # ── 1. QUÉ ES ────────────────────────────────────────────────────────────
    E += capitulo(1, "Qué es este módulo")
    E.append(parrafo(
        "El módulo de <b>Proyección Manual</b> permite crear un análisis de crédito "
        "hipotecario digitando a mano todos los datos del extracto, sin depender de la "
        "extracción automática con inteligencia artificial."))
    E.append(parrafo(
        "El resultado alimenta exactamente los mismos cálculos, resúmenes y proyecciones "
        "que un análisis extraído automáticamente. La única diferencia es el origen de los datos."))
    E.append(rotulo("Cuándo usarlo"))
    E += vinetas([
        "El PDF del extracto tiene un formato que la extracción automática no lee bien, o está escaneado con mala calidad.",
        "El extracto reporta cifras que no describen el crédito real (ver el capítulo 10).",
        "El banco entregó información complementaria por otro canal, por ejemplo una proyección de pagos aparte, y esos son los valores correctos.",
        "Se necesita corregir un análisis cuyo cálculo automático quedó bloqueado.",
    ])
    E.append(caja("buena", "Qué lo diferencia",
        "El análisis creado por este módulo queda marcado en el historial con el estado "
        "<b>Validado manualmente</b>. Eso indica que un administrador revisó y digitó cada "
        "cifra, y da trazabilidad sobre quién respondió por los datos."))

    # ── 2. ACCESO ────────────────────────────────────────────────────────────
    E += capitulo(2, "Cómo acceder")
    E += vinetas([
        "Iniciar sesión con una cuenta de rol ADMIN.",
        "En la barra lateral izquierda, hacer clic en <b>Proyección manual</b>.",
    ])
    E.append(Spacer(1, 4))
    E.append(bloque_codigo(["/dashboard/admin/proyeccion-manual"]))
    E.append(caja("info", "Si no ves la opción",
        "Si el enlace no aparece o está deshabilitado, la cuenta no tiene rol ADMIN."))

    # ── 3. ANTES DE EMPEZAR ──────────────────────────────────────────────────
    E += capitulo(3, "Antes de empezar: qué tener a la mano")
    E += vinetas([
        "El <b>PDF del extracto</b> del crédito. Es obligatorio adjuntarlo.",
        "La contraseña del PDF, si está protegido.",
        "<b>Datos de contacto del cliente</b>: nombre completo, cédula, correo y teléfono. Estos NO vienen en el extracto y hay que pedirlos aparte.",
        "Los <b>ingresos mensuales</b> del cliente.",
        "Si el banco entregó una proyección de pagos por separado, tenerla a mano: puede contener la cuota contractual real.",
    ])
    E.append(caja("buena", "Recomendación",
        "Llenar el formulario con el extracto abierto al lado. Cada campo de este manual "
        "indica de dónde sale el dato dentro del extracto."))

    # ── 4. ESTRUCTURA ────────────────────────────────────────────────────────
    E.append(PageBreak())
    E += capitulo(4, "Estructura del formulario")
    E.append(parrafo(
        "El formulario está dividido en bloques. Los campos marcados con asterisco rojo "
        f"({OBLIGATORIO.strip()}) son obligatorios. Algunos bloques aparecen o desaparecen "
        "según lo que se seleccione, como se explica en el capítulo 6."))
    E.append(tabla_datos(
        ["Bloque", "Contenido", "Visibilidad"],
        [["A", "Extracto y banco", "Siempre"],
         ["B", "Datos del cliente", "Siempre"],
         ["C", "Identificación del crédito", "Siempre"],
         ["D", "Saldos y cuotas", "Siempre"],
         ["E", "Tasas de interés", "Siempre"],
         ["F", "Cuota mensual y seguros", "Siempre"],
         ["G", "Beneficio FRECH", "Al marcar la casilla"],
         ["H", "Pagos acumulados", "Siempre"],
         ["I", "Datos UVR", "Solo si el sistema es UVR"],
         ["J", "Componentes del período", "Siempre"],
         ["K", "Opciones de abono a proyectar", "Siempre"],
         ["L", "Totales calculados", "Solo lectura"]],
        anchos=[ANCHO_UTIL * 0.12, ANCHO_UTIL * 0.53, ANCHO_UTIL * 0.35]))

    E += seccion("Bloque A - Extracto y banco")
    E.append(tabla_campos([
        ("Banco", True, "Lista desplegable. Seleccionar la entidad del crédito."),
        ("Contraseña del PDF", False, "Solo si el archivo está protegido. Si el PDF tiene contraseña y no se suministra, el sistema avisa y no permite continuar."),
        ("PDF del extracto", True, "Botón para adjuntar el archivo. Solo se aceptan archivos PDF. Una vez seleccionado se muestra el nombre debajo del botón."),
    ]))

    E += seccion("Bloque B - Datos del cliente")
    E.append(caja("info", "", "Si la cédula o el correo ya existen en la plataforma, el sistema "
                              "reutiliza ese cliente y actualiza sus datos. No se crean duplicados."))
    E.append(tabla_campos([
        ("Nombre completo", True, "Nombre y apellidos del titular, tal como debe aparecer en la propuesta."),
        ("Cédula", True, "Solo números. Mínimo 5 dígitos."),
        ("Email", True, "Debe ser un correo válido. Se normaliza a minúsculas."),
        ("Teléfono", True, "Solo números. Mínimo 7 dígitos."),
        ("Ingresos mensuales", True, "Ingreso declarado por el cliente. No viene en el extracto."),
        ("Capacidad de pago máxima", False, "Tope mensual que el cliente puede destinar al crédito."),
        ("Tipo de contrato", False, "Indefinido, Término fijo, Independiente, Prestación de servicios u Otro."),
    ]))

    E.append(PageBreak())
    E += seccion("Bloque C - Identificación del crédito")
    E.append(tabla_campos([
        ("Número del crédito", True, "Tal como aparece en el extracto."),
        ("Sistema de amortización", True, "PESOS o UVR. Esta selección determina si aparece el bloque de datos UVR."),
        ("Plan del crédito", False, 'Descripción del producto. Ejemplo: "Cuota constante en UVR - VIS".'),
        ("Fecha del extracto", True, 'La fecha de <b>corte</b>, no la de pago. En Bancolombia es "Fecha en que se generó el extracto"; en Banco de Bogotá es "Fecha de corte".'),
        ("Fecha de desembolso", False, "Fecha en que se entregó el crédito. Necesaria para estimar la vigencia del beneficio FRECH."),
        ("Plazo total (meses)", False, "Plazo original pactado. Si se deja vacío, el sistema toma el número de cuotas pactadas."),
    ]))

    E += seccion("Bloque D - Saldos y cuotas")
    E.append(tabla_campos([
        ("Valor prestado", True, 'Monto original desembolsado. En Bancolombia es "Valor desembolso"; en Banco de Bogotá es "Monto aprobado".'),
        ("Saldo capital", True, 'Lo que el cliente debe a la fecha del extracto. En Bancolombia es "Saldo a la fecha en que se generó el extracto". Es la cifra base de toda la proyección.'),
        ("Total por pagar del período", False, "Lo que el cliente debe pagar este mes."),
        ("Cuotas pactadas", True, "Número total de cuotas del crédito. Normalmente 360 o 180."),
        ("Cuotas pagadas", True, "Cuántas ha pagado hasta la fecha del extracto."),
        ("Cuotas por pagar", True, 'Cuántas le faltan. En Bancolombia es "Nro. cuotas pendientes para pago total".'),
        ("Nro. cuota a cancelar", False, "Número de la cuota que se está cobrando en el extracto."),
        ("Cuotas vencidas", False, "Cuotas en mora."),
    ]))
    E.append(caja("error", "Dos avisos críticos de este bloque", [
        "<b>Valor prestado no es saldo capital.</b> Son dos cifras distintas y ambas se piden por separado. "
        "En créditos UVR el saldo suele ser MAYOR que el valor prestado, porque se indexa con la inflación.",
        "<b>Cuotas vencidas mayor a cero bloquea la proyección.</b> Un crédito en mora no se puede proyectar "
        "con la cuota corriente.",
    ]))

    E.append(PageBreak())
    E += seccion("Bloque E - Tasas de interés (efectiva anual)")
    E.append(caja("buena", "Formato aceptado",
        "Se puede escribir tanto <b>7,47</b> como <b>0,0747</b>: el sistema interpreta ambas "
        "como 7,47% efectivo anual. El valor máximo aceptado es 100."))
    E.append(tabla_campos([
        ("Tasa cobrada E.A.", True, "La tasa que el banco está aplicando hoy. Es la que se usa para calcular los intereses de la proyección."),
        ("Tasa pactada E.A.", False, "La tasa plena del contrato original. Importante en créditos con FRECH: es la tasa a la que vuelve el crédito cuando se acaba el subsidio."),
        ("Tasa subsidiada E.A.", False, "Los puntos que cubre el gobierno, si aplica."),
        ("Tasa de mora E.A.", False, "Tasa de interés moratorio pactada."),
    ]))

    E += seccion("Bloque F - Cuota mensual y seguros")
    E.append(caja("advertencia", "Bloque delicado",
        "Este es el bloque donde más se equivoca la gente. Si el crédito tiene algún beneficio "
        "o subsidio, leer el <b>capítulo 10, caso 1</b> antes de llenarlo."))
    E.append(tabla_campos([
        ("Cuota completa aproximada", True, "Cuota total facturada, incluyendo seguros."),
        ("Cuota sin seguros", False, "Solo capital más intereses, sin seguros ni comisiones."),
        ("Cuota que paga el cliente", False, "Cuota neta después de descontar el subsidio FRECH. Si el crédito no tiene subsidio, se deja vacío."),
        ("Seguro de vida", False, "Valor mensual."),
        ("Seguro de incendio", False, "Valor mensual. Si el extracto trae incendio y terremoto en una sola línea, registrar aquí el total."),
        ("Seguro de terremoto", False, "Valor mensual. Dejar en cero si ya se sumó en el campo anterior."),
    ]))

    E += seccion("Bloque G - Beneficio FRECH")
    E.append(tabla_campos([
        ("¿Cuenta con beneficio FRECH?", False, 'Casilla de verificación. Al activarla aparecen los campos siguientes. Si el extracto muestra "Valor subsidio Gobierno" en cero, dejarla desmarcada.'),
        ("Beneficio FRECH mensual", True, "Obligatorio solo si la casilla está activa. Valor mensual que aporta el gobierno."),
        ("FRECH recibido hasta hoy", False, "Total acumulado aportado por el gobierno. Si se deja vacío, el sistema lo calcula como beneficio mensual por cuotas pagadas."),
        ("Inicio de vigencia FRECH", False, "El FRECH de vivienda VIS suele durar 84 meses desde el desembolso."),
        ("Fin de vigencia FRECH", False, "Fecha en que se agota el subsidio."),
    ]))
    E.append(caja("info", "Nota",
        "Si se desmarca la casilla, el sistema limpia automáticamente todos los campos de "
        "subsidio. No quedan residuos de datos."))

    E.append(PageBreak())
    E += seccion("Bloque H - Pagos acumulados")
    E.append(tabla_campos([
        ("Pagado por el cliente hasta hoy", False, "Total que el cliente ha desembolsado de su bolsillo desde que inició el crédito. Si se deja vacío, el sistema lo estima como cuota del cliente por cuotas pagadas. Cuando se digita un valor, el sistema lo respeta como dato duro y no lo sobrescribe."),
    ]))

    E += seccion("Bloque I - Datos UVR")
    E.append(caja("info", "", "Este bloque solo aparece cuando el sistema de amortización es UVR. "
                              "Todos sus campos admiten hasta 4 decimales."))
    E.append(tabla_campos([
        ("Saldo capital en UVR", True, "Saldo expresado en unidades UVR."),
        ("Valor UVR a la fecha", True, "Valor de la unidad UVR en la fecha del extracto."),
        ("Valor de la cuota en UVR", False, "Cuota expresada en unidades UVR."),
    ]))
    E.append(caja("advertencia", 'Cuidado con "Valor de la cuota en UVR"',
        "En algunos extractos este valor corresponde a la cuota ya rebajada por un beneficio, "
        "no a la cuota contractual. Si es el caso, <b>dejar el campo vacío</b> y registrar la "
        "cuota contractual en el bloque F. Ver el capítulo 10, caso 1."))

    E += seccion("Bloque J - Componentes del período")
    E.append(parrafo("Desglose del último pago reportado en el extracto. Son opcionales y sirven "
                     "principalmente para auditoría."))
    E.append(tabla_campos([
        ("Capital abonado en el período", False, "Parte del pago que redujo la deuda."),
        ("Intereses corrientes del período", False, "Intereses cobrados en el mes."),
        ("Intereses de mora", False, "Si los hubo."),
        ("Otros cargos", False, "Comisiones, seguros voluntarios u otros conceptos."),
    ]))

    E += seccion("Bloque K - Opciones de abono a proyectar")
    E.append(tabla_campos([
        ("Abono opción 1", False, "Precargado en 200.000. Se puede cambiar."),
        ("Abono opción 2", False, "Precargado en 300.000. Se puede cambiar."),
        ("Abono opción 3", False, "Precargado en 400.000. Se puede cambiar."),
    ]))

    E.append(PageBreak())
    E += seccion("Bloque L - Totales calculados (solo lectura)")
    E.append(parrafo("Este bloque no se llena: se actualiza solo, en tiempo real, a medida que se "
                     "digitan los datos. Sirve para verificar antes de guardar."))
    E.append(tabla_campos([
        ("Cuota que paga el cliente", False, "Cuota completa menos el beneficio FRECH."),
        ("Pagado por el cliente", False, "Lo declarado, o la estimación por cuotas pagadas."),
        ("FRECH acumulado", False, "Lo declarado, o beneficio mensual por cuotas pagadas."),
        ("Total abonado al crédito", False, "Suma de lo que puso el cliente más lo que puso el gobierno. Es el total que ha recibido el banco."),
    ], encabezados=("Indicador", "Cómo se obtiene")))
    E.append(caja("buena", "Cómo usarlo",
        "Comparar estas cuatro cifras contra el extracto antes de guardar. Si alguna se ve "
        "desproporcionada, hay un dato mal digitado más arriba."))

    # ── 5. NÚMEROS ───────────────────────────────────────────────────────────
    E += capitulo(5, "Cómo escribir los números")
    E.append(parrafo("El formulario usa el formato colombiano."))
    E.append(bloque_codigo([
        "El punto separa los miles:       1.148.411",
        "La coma separa los decimales:    1.148.411,97",
    ]))
    E.append(parrafo("Se puede escribir de corrido, sin puntos: el campo los agrega solo mientras "
                     "se escribe. Para los decimales hay que usar coma."))
    E.append(tabla_datos(
        ["Tipo de campo", "Decimales admitidos", "Separador de miles"],
        [["Dinero", "2", "Sí"],
         ["Tasa", "4", "No"],
         ["UVR", "4", "Sí"],
         ["Cantidad (cuotas, meses, cédula)", "Ninguno", "Sí"]],
        anchos=[ANCHO_UTIL * 0.44, ANCHO_UTIL * 0.28, ANCHO_UTIL * 0.28]))

    # ── 6. CAMPOS CONDICIONALES ──────────────────────────────────────────────
    E += capitulo(6, "Campos que aparecen y desaparecen")
    E.append(parrafo("El formulario se adapta para no pedir datos que no aplican."))
    E.append(tabla_datos(
        ["Si...", "Entonces..."],
        [["Sistema de amortización = UVR",
          "Aparece el bloque I y sus dos primeros campos pasan a ser obligatorios."],
         ["Sistema de amortización = PESOS",
          "El bloque I desaparece por completo."],
         ["Casilla FRECH marcada",
          "Aparecen el valor mensual (obligatorio), el acumulado y las dos fechas de vigencia."],
         ["Casilla FRECH desmarcada",
          "Esos campos desaparecen y se limpian automáticamente."]],
        anchos=[ANCHO_UTIL * 0.38, ANCHO_UTIL * 0.62]))

    # ── 7. VALIDACIONES ──────────────────────────────────────────────────────
    E.append(PageBreak())
    E += capitulo(7, "Validaciones")
    E.append(parrafo("El sistema no deja guardar si alguna de estas reglas no se cumple. El mensaje "
                     "aparece en pantalla indicando exactamente qué falla."))
    E.append(tabla_datos(
        ["Categoría", "Regla"],
        [["Cuotas", "Cuotas pagadas + cuotas por pagar no puede superar las cuotas pactadas."],
         ["Cuotas", "Las cuotas vencidas no pueden superar las cuotas por pagar."],
         ["Fechas", "La fecha del extracto no puede ser anterior a la fecha de desembolso."],
         ["Fechas", "La vigencia FRECH no puede terminar antes de empezar."],
         ["Montos", "El beneficio FRECH no puede ser mayor o igual a la cuota completa."],
         ["Montos", "La cuota sin seguros no puede superar la cuota con seguros."],
         ["Tasas", "Ninguna tasa efectiva anual puede superar el 100%."],
         ["UVR", "Se exigen el saldo de capital en UVR y el valor de la UVR a la fecha."],
         ["FRECH", "Si se marca que tiene FRECH, hay que registrar el valor mensual."],
         ["Archivo", "El PDF es obligatorio. Si está protegido, hay que suministrar la contraseña correcta."]],
        anchos=[ANCHO_UTIL * 0.20, ANCHO_UTIL * 0.80]))
    E.append(caja("info", "Ayuda en pantalla",
        "Mientras falten campos obligatorios, aparece una caja ámbar con la lista de lo que "
        "falta, y el botón de guardar permanece deshabilitado."))

    # ── 8. GUARDAR ───────────────────────────────────────────────────────────
    E += capitulo(8, "Guardar")
    E.append(parrafo('Al presionar <b>Guardar y abrir proyecciones</b> el sistema ejecuta esta secuencia:'))
    E.append(tabla_datos(
        ["Paso", "Qué ocurre"],
        [["1", "Valida todo el formulario."],
         ["2", "Guarda el PDF. Si tenía contraseña, lo desencripta antes."],
         ["3", "Crea o actualiza el cliente."],
         ["4", 'Crea el análisis con estado "Validado manualmente".'],
         ["5", "Redirige a la pantalla de proyecciones de ese crédito."]],
        anchos=[ANCHO_UTIL * 0.12, ANCHO_UTIL * 0.88]))
    E.append(caja("buena", "Dónde queda registrado",
        'En <b>Ver historial de análisis</b>, el crédito aparece con la etiqueta '
        '"Validado manualmente" en la columna de estado. Si algo falla al guardar, aparece un '
        "mensaje con el motivo concreto y no se pierde lo digitado."))

    # ── 9. PROYECCIONES ──────────────────────────────────────────────────────
    E.append(PageBreak())
    E += capitulo(9, "Generar las proyecciones")
    E.append(parrafo("Después de guardar se llega a la pantalla de proyecciones."))

    E += seccion("Paso 1 - Definir el IPC proyectado")
    E.append(parrafo("Solo aplica a créditos UVR. Es la inflación anual estimada con la que crecerá "
                     "la UVR durante la proyección."))
    E.append(tabla_datos(
        ["Referencia de mercado", "IPC"],
        [["Suave / Bancos", "2,2%"],
         ["Medio / Meta Banco de la República", "3,0% a 3,5%"],
         ["Alto", "5,0%"]],
        anchos=[ANCHO_UTIL * 0.65, ANCHO_UTIL * 0.35]))
    E.append(Spacer(1, 6))
    E.append(caja("advertencia", "El IPC cambia mucho el resultado",
        "En un crédito con 66 millones de saldo, el costo total proyectado varía así:"))
    E.append(tabla_datos(
        ["IPC", "Costo total proyectado", "Veces pagado"],
        [["2,0%", "182.345.933", "2,75"],
         ["3,0%", "211.274.693", "3,18"],
         ["5,0%", "288.459.056", "4,35"],
         ["6,0%", "339.653.871", "5,12"]],
        anchos=[ANCHO_UTIL * 0.20, ANCHO_UTIL * 0.50, ANCHO_UTIL * 0.30],
        alinear_der=[1, 2]))
    E.append(Spacer(1, 6))
    E.append(parrafo("Para estudios de 2026 el valor recomendado es <b>3</b>. El sistema limita el "
                     "IPC a un máximo de 30% anual para evitar errores de digitación."))

    E += seccion("Paso 2 - Revisar los abonos")
    E.append(parrafo("Se pueden ajustar los tres montos antes de calcular."))

    E += seccion("Paso 3 - Calcular proyecciones")
    E.append(parrafo("El sistema genera la comparación entre el escenario actual y las tres opciones. "
                     "El botón <b>Calcular proyecciones</b> es el que guarda el IPC: escribirlo en el "
                     "campo no basta."))
    E.append(caja("buena", "Verificación de coherencia",
        ["La tabla es coherente cuando se cumple:",
         "<font name='Courier'>Ahorro = Total del escenario actual - Total de la opción</font>",
         "Si no cuadra, las proyecciones guardadas son de un cálculo anterior con otro IPC. "
         "La solución es volver a presionar <b>Calcular proyecciones</b>."]))

    # ── 10. CASOS ESPECIALES ─────────────────────────────────────────────────
    E.append(PageBreak())
    E += capitulo(10, "Casos especiales y errores frecuentes")

    E += seccion("Caso 1 - El extracto reporta una cuota que no amortiza")
    E.append(caja("error", "El error más costoso y el más difícil de detectar",
        "Algunos extractos muestran como cuota el valor ya rebajado por un beneficio, no la "
        "cuota contractual. Si se digita esa cifra, la proyección arroja resultados absurdos: "
        "plazos de 100 años y costos de miles de millones."))
    E.append(rotulo("Cómo detectarlo"))
    E.append(parrafo("Comparar la cuota contra el interés mensual del saldo. Si la cuota es menor "
                     "que el interés, el crédito nunca se pagaría, lo cual es imposible en un "
                     "crédito vigente."))
    E.append(bloque_codigo([
        "interes mensual = saldo capital x (tasa cobrada anual / 12)",
    ]))
    E.append(rotulo("Ejemplo real"))
    E.append(tabla_datos(
        ["Dato", "Valor"],
        [["Saldo capital", "177.833.619"],
         ["Tasa cobrada", "6,40% E.A."],
         ["Interés mensual del saldo", "cerca de 921.712"],
         ["Cuota que reportaba el extracto", "543.918   (no alcanza ni para los intereses)"],
         ["Cuota contractual real", "1.097.678   (la trajo la proyección de pagos del banco)"]],
        anchos=[ANCHO_UTIL * 0.40, ANCHO_UTIL * 0.60]))
    E.append(Spacer(1, 6))
    E.append(caja("buena", "Cómo resolverlo",
        "Pedir al banco la <b>proyección de pagos</b> del crédito. Ese documento trae la cuota "
        "contractual real, es decir capital más intereses. Registrarla en el bloque F y dejar "
        'vacío el campo "Valor de la cuota en UVR" del bloque I.'))

    E.append(PageBreak())
    E += seccion("Caso 2 - Créditos con FRECH")
    E.append(parrafo("El FRECH es un subsidio sobre la <b>tasa</b> de interés, no sobre la cuota. "
                     "El gobierno cubre unos puntos porcentuales durante un plazo determinado."))
    E.append(rotulo("Qué registrar"))
    E += vinetas([
        "<b>Tasa cobrada</b>: la que el banco aplica hoy, ya con el subsidio.",
        "<b>Tasa pactada</b>: la tasa plena del contrato, a la que volverá el crédito.",
        "<b>Beneficio FRECH mensual</b>: el valor que aporta el gobierno.",
        "Fechas de vigencia, si el extracto las trae.",
    ])
    E.append(caja("info", "Qué sucede al vencer el subsidio",
        "El plazo del crédito no se altera: alargarlo constituiría una reestructuración y es "
        "causal de pérdida anticipada del beneficio. La tasa vuelve a la pactada y la cuota "
        "mensual sube para amortizar el saldo en el tiempo que queda."))
    E.append(caja("advertencia", "Verificación automática",
        "Si la cuota digitada y la tasa cobrada no son coherentes con las cuotas pendientes que "
        "reporta el extracto, el sistema bloquea la proyección e indica en cuántas cuotas se "
        "liquidaría el saldo según lo digitado, frente a las que reporta el banco. Es señal de "
        "que la cuota y la tasa corresponden a dos lecturas distintas del mismo crédito."))

    E += seccion("Caso 3 - Créditos en mora")
    E.append(parrafo('Si "Cuotas vencidas" es mayor a cero, el sistema no genera proyecciones. El '
                     "saldo vencido no puede tratarse como cuota recurrente. Hay que normalizar el "
                     "crédito antes de proyectar."))

    E += seccion("Caso 4 - Confundir valor prestado con saldo")
    E.append(tabla_datos(
        ["Campo", "Significado"],
        [["Valor prestado", "Lo que el banco entregó en su momento."],
         ["Saldo capital", "Lo que el cliente debe hoy."]],
        anchos=[ANCHO_UTIL * 0.30, ANCHO_UTIL * 0.70]))
    E.append(Spacer(1, 6))
    E.append(parrafo("En créditos UVR el saldo suele ser mayor que el valor prestado, porque se "
                     "indexa con la inflación. No es un error del sistema."))

    E += seccion("Caso 5 - El PDF está protegido")
    E.append(parrafo("Si el archivo tiene contraseña y no se suministra, el sistema avisa. Al "
                     "digitarla correctamente, el PDF se guarda ya desencriptado."))

    # ── 11. GLOSARIO ─────────────────────────────────────────────────────────
    E.append(PageBreak())
    E += capitulo(11, "Glosario")
    E.append(tabla_campos([
        ("UVR", False, "Unidad de Valor Real. Unidad de cuenta que se ajusta con la inflación. En un crédito en UVR el saldo crece con el IPC."),
        ("E.A.", False, "Efectiva Anual. Forma de expresar una tasa de interés en Colombia."),
        ("FRECH", False, "Fondo de Reserva para la Estabilización de la Cartera Hipotecaria. Subsidio del gobierno sobre los puntos de interés de créditos de vivienda."),
        ("VIS / VIP", False, "Vivienda de Interés Social / Vivienda de Interés Prioritario."),
        ("IPC", False, "Índice de Precios al Consumidor. Mide la inflación."),
        ("Cuota contractual", False, "Capital más intereses, sin seguros. Es la que realmente amortiza la deuda."),
        ("Abono extra", False, "Pago mensual adicional a la cuota, destinado a reducir capital."),
        ("Veces pagado", False, "Cuántas veces el saldo actual terminará pagando el cliente. Un valor de 3,18 significa que pagará 3,18 veces lo que debe hoy."),
    ], encabezados=("Término", "Definición")))

    # ── 12. RESUMEN ──────────────────────────────────────────────────────────
    E += capitulo(12, "Resumen de un vistazo")
    E.append(tabla_datos(
        ["#", "Paso"],
        [["1", "Sidebar - Proyección manual"],
         ["2", "Adjuntar el PDF y seleccionar el banco"],
         ["3", "Datos del cliente: nombre, cédula, correo, teléfono, ingresos"],
         ["4", "Identificación del crédito: número, sistema, fechas"],
         ["5", "Saldos y cuotas. No confundir valor prestado con saldo"],
         ["6", "Tasas. Se acepta 7,47 o 0,0747"],
         ["7", "Cuota y seguros. Verificar que la cuota cubra el interés mensual"],
         ["8", "FRECH, si aplica"],
         ["9", "Datos UVR, si aplica"],
         ["10", "Abonos a proyectar"],
         ["11", "Revisar el bloque de totales calculados"],
         ["12", "Guardar y abrir proyecciones"],
         ["13", "Definir el IPC (3 para estudios de 2026) y calcular"]],
        anchos=[ANCHO_UTIL * 0.08, ANCHO_UTIL * 0.92]))

    doc.build(E)
    return salida


if __name__ == "__main__":
    ruta = construir()
    print(f"PDF generado: {ruta}")
