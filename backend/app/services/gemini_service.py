"""
Gemini Service - Extracción de datos de PDFs con Google Generative AI
======================================================================

Funcionalidades:
- Extracción estructurada de datos de extractos de crédito hipotecario
- Validación de autenticidad del documento
- Comparación inteligente de nombres
- Soporte para múltiples bancos colombianos

OPTIMIZACIÓN:
- Usa File API de Google en lugar de Base64 para reducir consumo de tokens
- Los PDFs se suben una vez y se referencian por URI
- Usa el nuevo SDK google-genai con Client()
"""

import json
import logging
import os
import re
import tempfile
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Optional

from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN Y CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

class ExtractionStatus(str, Enum):
    """Estados de la extracción"""
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"  # Algunos campos no encontrados
    FAILED = "FAILED"
    NOT_CREDIT_DOCUMENT = "NOT_CREDIT_DOCUMENT"
    API_ERROR = "API_ERROR"


@dataclass
class ExtractionResult:
    """Resultado de la extracción de datos"""
    status: ExtractionStatus
    confidence: float = 0.0
    message: str = ""
    
    # Datos extraídos
    data: dict = field(default_factory=dict)
    
    # Metadata
    campos_encontrados: list[str] = field(default_factory=list)
    campos_faltantes: list[str] = field(default_factory=list)
    banco_detectado: str | None = None
    es_extracto_hipotecario: bool = True
    
    # Raw response para debugging
    raw_response: str | None = None


@dataclass 
class NameComparisonResult:
    """Resultado de comparación de nombres"""
    match: bool
    similarity: float
    pdf_name_normalized: str
    user_name_normalized: str
    explanation: str


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT DE EXTRACCIÓN
# ═══════════════════════════════════════════════════════════════════════════════

EXTRACTION_PROMPT = """Eres un experto en análisis de documentos financieros colombianos, especializado en extractos de créditos hipotecarios.

## TAREA PRIMARIA: VALIDACIÓN DE TIPO DE DOCUMENTO
**ANTES de extraer datos**, debes determinar si el documento es un EXTRACTO DE CRÉDITO HIPOTECARIO/HABITACIONAL válido.

### Documentos VÁLIDOS (es_extracto_hipotecario = true):
- Extracto de crédito hipotecario
- Extracto de crédito de vivienda
- Estado de cuenta de crédito hipotecario
- Certificado de deuda hipotecaria
- Extracto de préstamo para vivienda

### Documentos INVÁLIDOS (es_extracto_hipotecario = false):
- Facturas de servicios públicos (agua, luz, gas)
- Extractos bancarios de cuenta de ahorros o corriente
- Certificados de ingresos o laborales
- Declaraciones de renta
- Pólizas de seguros (que no sean parte del extracto)
- Escrituras o documentos notariales
- Contratos de arrendamiento
- Cualquier otro documento no relacionado con crédito hipotecario

**Si el documento NO es un extracto hipotecario, responde INMEDIATAMENTE con:**
```json
{"es_extracto_hipotecario": false, "tipo_documento_detectado": "Factura de energía eléctrica", "confianza_extraccion": 0.95}
```

## TAREA SECUNDARIA: EXTRACCIÓN DE DATOS
Solo si el documento ES un extracto hipotecario válido, extrae TODOS los datos disponibles.

## CONTEXTO IMPORTANTE
- Los créditos pueden estar en sistema UVR (Unidad de Valor Real) o en PESOS
- El UVR es una unidad monetaria que se ajusta diariamente por inflación
- Los bancos colombianos incluyen: Bancolombia, Davivienda, BBVA, Banco de Bogotá, Scotiabank Colpatria, AV Villas, Banco Popular, etc.
- El beneficio FRECH es un subsidio gubernamental a la tasa de interés
- Las cuotas pueden incluir seguros de vida, incendio y terremoto

## CAMPOS A EXTRAER (extrae TODOS los que encuentres)

### Identificación del Titular
- nombre_titular: Nombre completo del titular del crédito
- identificacion_titular: Número de cédula o NIT del titular (IMPORTANTE para validación de identidad)
- tipo_identificacion_titular: "CC" (Cédula), "CE" (Cédula Extranjería), "NIT", etc.
- numero_credito: Número u obligación del crédito
- banco: Nombre del banco o entidad financiera
- sistema_amortizacion: "UVR" o "PESOS" o "MIXTO"
- plan_credito: Tipo de plan o línea de crédito (VIS, No VIS, Mi Casa Ya, etc.)

### Fechas y Plazos
- fecha_desembolso: Fecha de desembolso del crédito (formato YYYY-MM-DD)
- fecha_extracto: Fecha del extracto (formato YYYY-MM-DD)
- plazo_total_meses: Plazo total pactado en meses

### Cuotas
- cuotas_pactadas: Total de cuotas pactadas
- cuotas_pagadas: Cuotas ya pagadas
- cuotas_pendientes: Cuotas por pagar
- cuotas_vencidas: Cuotas en mora (si aplica)

### Tasas de Interés (como PORCENTAJE, ej: 9.53 para 9.53%)
- tasa_interes_pactada_ea: Tasa pactada Efectiva Anual
- tasa_interes_cobrada_ea: Tasa que realmente se cobra E.A.
- tasa_interes_subsidiada_ea: Tasa con subsidio FRECH (si aplica)
- tasa_mora_ea: Tasa de mora E.A. (si aparece)

### Valores en Pesos Colombianos (solo números, sin símbolos)
- valor_prestado_inicial: Monto inicial del préstamo
- valor_cuota_sin_seguros: Cuota sin incluir seguros
- valor_cuota_con_seguros: Cuota total incluyendo seguros
- beneficio_frech_mensual: Valor mensual del subsidio FRECH
- valor_cuota_con_subsidio: Cuota que paga el cliente (con FRECH aplicado)
- saldo_capital_pesos: Saldo de capital actual en pesos
- total_por_pagar: Total adeudado

### Valores UVR (si el crédito es en UVR)
- saldo_capital_uvr: Saldo de capital en UVR
- valor_uvr_fecha_extracto: Valor del UVR a la fecha del extracto
- valor_cuota_uvr: Valor de la cuota en UVR

### Seguros Mensuales (valores individuales)
- seguro_vida: Prima mensual de seguro de vida
- seguro_incendio: Prima mensual de seguro de incendio/hogar
- seguro_terremoto: Prima mensual de seguro de terremoto

### Intereses del Período
- intereses_corrientes_periodo: Intereses del mes/período actual
- intereses_mora: Intereses de mora (si aplica)

## FORMATO DE RESPUESTA
Responde ÚNICAMENTE con un JSON válido con esta estructura:

```json
{
  "es_extracto_hipotecario": true,
  "confianza_extraccion": 0.85,
  "banco_detectado": "Bancolombia",
  "sistema_amortizacion": "UVR",
  
  "nombre_titular": "JUAN CARLOS PÉREZ GARCÍA",
  "identificacion_titular": "1234567890",
  "tipo_identificacion_titular": "CC",
  "numero_credito": "123456789012",
  "plan_credito": "VIS",
  
  "fecha_desembolso": "2020-05-15",
  "fecha_extracto": "2024-01-15",
  "plazo_total_meses": 180,
  
  "cuotas_pactadas": 180,
  "cuotas_pagadas": 44,
  "cuotas_pendientes": 136,
  "cuotas_vencidas": 0,
  
  "tasa_interes_pactada_ea": 9.53,
  "tasa_interes_cobrada_ea": 9.53,
  "tasa_interes_subsidiada_ea": 4.71,
  "tasa_mora_ea": 19.56,
  
  "valor_prestado_inicial": 150000000,
  "valor_cuota_sin_seguros": 1150000,
  "valor_cuota_con_seguros": 1350000,
  "beneficio_frech_mensual": 200000,
  "valor_cuota_con_subsidio": 1150000,
  "saldo_capital_pesos": 142000000,
  "total_por_pagar": 145000000,
  
  "saldo_capital_uvr": 350000,
  "valor_uvr_fecha_extracto": 405.72,
  "valor_cuota_uvr": 2850,
  
  "seguro_vida": 85000,
  "seguro_incendio": 45000,
  "seguro_terremoto": 25000,
  
  "intereses_corrientes_periodo": 950000,
  "intereses_mora": 0,
  
  "campos_no_encontrados": ["tasa_mora_ea"],
  "notas": "Extracto de Bancolombia con crédito VIS en UVR"
}
```

## REGLAS IMPORTANTES
1. Si un campo NO aparece en el documento, inclúyelo en "campos_no_encontrados" y NO lo incluyas en el JSON principal
2. Para valores monetarios, usa SOLO números sin puntos de miles ni símbolos (ejemplo: 1500000 no 1.500.000)
3. Para tasas de interés, usa el valor PORCENTUAL (ejemplo: 9.53 para 9.53% E.A.)
4. Las fechas deben estar en formato YYYY-MM-DD
5. Si el documento NO es un extracto de crédito hipotecario, responde: {"es_extracto_hipotecario": false, "tipo_documento_detectado": "..."}
6. El campo "confianza_extraccion" debe ser un número entre 0 y 1 indicando qué tan seguro estás de la extracción

Analiza el documento y responde SOLO con el JSON, sin texto adicional."""


NAME_COMPARISON_PROMPT = """Compara estos dos nombres y determina si corresponden a la misma persona.

Nombre en el documento PDF: "{pdf_name}"
Nombre del usuario registrado: "{user_name}"

Considera:
- Pueden estar en diferente orden (apellidos primero vs nombres primero)
- Pueden tener tildes o no
- Pueden estar abreviados
- Pueden tener errores menores de digitación
- Un nombre puede ser más completo que el otro

Responde SOLO con JSON:
```json
{{
  "match": true/false,
  "similarity": 0.0-1.0,
  "explanation": "Breve explicación del resultado"
}}
```"""


# ═══════════════════════════════════════════════════════════════════════════════
# SERVICIO PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class GeminiService:
    """
    Servicio para extracción de datos de PDFs usando Google Gemini.
    Usa el nuevo SDK google-genai con Client().
    """
    
    # Modelo a usar (gemini-2.5-flash es el más reciente y económico)
    MODEL_NAME = "gemini-2.5-flash"
    
    def __init__(self, api_key: str | None = None):
        """
        Inicializa el servicio de Gemini.
        
        Args:
            api_key: API key de Google Generative AI (usa settings si no se proporciona)
        """
        self.api_key = api_key or settings.GEMINI_API_KEY
        self._client: genai.Client | None = None
        
        if self.api_key:
            self._configure_client()
    
    def _configure_client(self) -> None:
        """Configura el cliente de Gemini."""
        try:
            self._client = genai.Client(api_key=self.api_key)
            logger.info(f"Gemini Client configurado con modelo {self.MODEL_NAME}")
        except Exception as e:
            logger.error(f"Error configurando Gemini Client: {e}")
            self._client = None
    
    @property
    def is_configured(self) -> bool:
        """Verifica si el servicio está configurado correctamente."""
        return self._client is not None
    
    def _call_with_retry(
        self, 
        contents: list,
        max_retries: int = 3,
        initial_delay: float = 5.0
    ):
        """
        Llama a Gemini con retry y backoff exponencial para manejar rate limits.
        
        Args:
            contents: Contenido a enviar a Gemini
            max_retries: Número máximo de reintentos
            initial_delay: Delay inicial en segundos (se duplica en cada reintento)
            
        Returns:
            Response de Gemini
        """
        delay = initial_delay
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return self._client.models.generate_content(
                    model=self.MODEL_NAME,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        temperature=0.1,  # Baja temperatura para respuestas consistentes
                        top_p=0.8,
                        top_k=40,
                        max_output_tokens=8192,
                    )
                )
                
            except Exception as e:
                error_str = str(e).lower()
                
                # Verificar si es un error de rate limit (429)
                if "429" in str(e) or "quota" in error_str or "rate" in error_str or "exhausted" in error_str:
                    last_exception = e
                    
                    if attempt < max_retries:
                        # Extraer tiempo de espera sugerido si está disponible
                        retry_after = self._extract_retry_delay(e)
                        wait_time = retry_after if retry_after else delay
                        
                        logger.warning(
                            f"Rate limit alcanzado (intento {attempt + 1}/{max_retries + 1}). "
                            f"Esperando {wait_time:.1f}s antes de reintentar..."
                        )
                        time.sleep(wait_time)
                        delay *= 2  # Backoff exponencial
                    else:
                        logger.error(f"Rate limit: se agotaron los {max_retries} reintentos")
                        raise
                else:
                    # Otros errores no se reintentan
                    raise
        
        raise last_exception
    
    def _extract_retry_delay(self, exception: Exception) -> float | None:
        """Extrae el tiempo de espera sugerido del error 429."""
        try:
            error_message = str(exception)
            # Buscar "retry in X.XXs" en el mensaje
            match = re.search(r'retry in (\d+\.?\d*)s', error_message, re.IGNORECASE)
            if match:
                return float(match.group(1)) + 1  # +1 segundo de margen
        except Exception:
            pass
        return None

    async def extract_credit_data(
        self,
        pdf_content: bytes,
        additional_context: dict | None = None
    ) -> ExtractionResult:
        """
        Extrae datos estructurados de un PDF de extracto de crédito.
        
        Usa la File API de Google para subir el PDF en lugar de Base64,
        lo que reduce drásticamente el consumo de tokens de entrada.
        
        Args:
            pdf_content: Contenido binario del PDF
            additional_context: Contexto adicional (banco esperado, etc.)
            
        Returns:
            ExtractionResult con los datos extraídos
        """
        if not self.is_configured:
            return ExtractionResult(
                status=ExtractionStatus.API_ERROR,
                message="Gemini API no está configurada. Verifica GEMINI_API_KEY.",
                confidence=0.0
            )
        
        uploaded_file = None
        temp_file_path = None
        
        try:
            # Crear archivo temporal para el PDF
            with tempfile.NamedTemporaryFile(
                suffix=".pdf", 
                delete=False,
                prefix="credit_extract_"
            ) as temp_file:
                temp_file.write(pdf_content)
                temp_file_path = temp_file.name
            
            # Subir el archivo usando File API de Google
            logger.info("Subiendo PDF a Google File API...")
            uploaded_file = self._client.files.upload(
                file=temp_file_path,
                config=types.UploadFileConfig(
                    mime_type="application/pdf",
                    display_name=f"credit_extract_{int(time.time())}"
                )
            )
            
            # Esperar a que el archivo esté procesado
            while uploaded_file.state == "PROCESSING":
                logger.debug("Esperando procesamiento del archivo...")
                time.sleep(0.5)
                uploaded_file = self._client.files.get(name=uploaded_file.name)
            
            if uploaded_file.state == "FAILED":
                return ExtractionResult(
                    status=ExtractionStatus.API_ERROR,
                    message="Error al procesar el archivo en Google File API",
                    confidence=0.0
                )
            
            logger.info(f"PDF subido exitosamente: {uploaded_file.uri}")
            
            # Crear el contenido multimodal usando la referencia al archivo
            contents = [
                types.Part.from_uri(
                    file_uri=uploaded_file.uri,
                    mime_type="application/pdf"
                ),
                EXTRACTION_PROMPT
            ]
            
            logger.info("Enviando solicitud a Gemini para extracción...")
            
            # Llamar a Gemini con retry para manejar rate limits (429)
            response = self._call_with_retry(contents)
            
            if not response or not response.text:
                return ExtractionResult(
                    status=ExtractionStatus.API_ERROR,
                    message="Gemini no retornó respuesta",
                    confidence=0.0
                )
            
            # Parsear respuesta JSON
            return self._parse_extraction_response(response.text)
        
        except Exception as e:
            error_str = str(e).lower()
            if "429" in str(e) or "quota" in error_str or "exhausted" in error_str:
                logger.error(f"Cuota de Gemini excedida: {e}")
                return ExtractionResult(
                    status=ExtractionStatus.API_ERROR,
                    message="Cuota de API excedida. Intenta más tarde o activa facturación en Google AI Studio.",
                    confidence=0.0
                )
            
            logger.error(f"Error en extracción con Gemini: {e}")
            return ExtractionResult(
                status=ExtractionStatus.API_ERROR,
                message=f"Error en API de Gemini: {str(e)}",
                confidence=0.0
            )
        finally:
            # Limpiar: eliminar archivo temporal local
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    logger.debug(f"Archivo temporal eliminado: {temp_file_path}")
                except OSError as e:
                    logger.warning(f"No se pudo eliminar archivo temporal: {e}")
            
            # Limpiar: eliminar archivo de Google File API
            if uploaded_file:
                try:
                    self._client.files.delete(name=uploaded_file.name)
                    logger.debug(f"Archivo eliminado de Google File API: {uploaded_file.name}")
                except Exception as e:
                    logger.warning(f"No se pudo eliminar archivo de File API: {e}")
    
    def _parse_extraction_response(self, response_text: str) -> ExtractionResult:
        """
        Parsea la respuesta JSON de Gemini.
        """
        try:
            # Limpiar respuesta (puede venir con markdown)
            json_text = response_text.strip()
            
            # Remover bloques de código markdown si existen
            if json_text.startswith("```"):
                # Encontrar el JSON dentro del bloque de código
                match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', json_text)
                if match:
                    json_text = match.group(1)
            
            # Parsear JSON
            data = json.loads(json_text)
            
            # Verificar si es un extracto hipotecario
            if not data.get("es_extracto_hipotecario", True):
                return ExtractionResult(
                    status=ExtractionStatus.NOT_CREDIT_DOCUMENT,
                    message=f"El documento no es un extracto de crédito hipotecario. Tipo detectado: {data.get('tipo_documento_detectado', 'desconocido')}",
                    confidence=0.0,
                    es_extracto_hipotecario=False,
                    raw_response=response_text
                )
            
            # Obtener confianza
            confidence = float(data.get("confianza_extraccion", 0.5))
            
            # Obtener campos faltantes
            campos_faltantes = data.pop("campos_no_encontrados", [])
            
            # Limpiar campos de metadata del dict de datos
            notas = data.pop("notas", None)
            es_extracto = data.pop("es_extracto_hipotecario", True)
            confianza = data.pop("confianza_extraccion", 0.5)
            banco = data.pop("banco_detectado", None)  # Remover del data dict
            
            # Normalizar datos (convertir tipos)
            normalized_data = self._normalize_extracted_data(data)
            
            # Determinar campos encontrados
            campos_encontrados = [k for k, v in normalized_data.items() if v is not None]
            
            # Determinar status
            if len(campos_faltantes) == 0:
                status = ExtractionStatus.SUCCESS
                message = "Extracción completa exitosa"
            elif len(campos_encontrados) > 5:
                status = ExtractionStatus.PARTIAL
                message = f"Extracción parcial. Campos faltantes: {', '.join(campos_faltantes[:5])}"
            else:
                status = ExtractionStatus.FAILED
                message = "No se pudieron extraer suficientes datos del documento"
            
            return ExtractionResult(
                status=status,
                confidence=confidence,
                message=message,
                data=normalized_data,
                campos_encontrados=campos_encontrados,
                campos_faltantes=campos_faltantes,
                banco_detectado=banco,
                es_extracto_hipotecario=True,
                raw_response=response_text
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON de Gemini: {e}")
            logger.debug(f"Respuesta recibida: {response_text[:500]}")
            return ExtractionResult(
                status=ExtractionStatus.API_ERROR,
                message=f"Error parseando respuesta de Gemini: {str(e)}",
                confidence=0.0,
                raw_response=response_text
            )
    
    def _normalize_extracted_data(self, data: dict) -> dict:
        """
        Normaliza los datos extraídos a los tipos correctos.
        """
        normalized = {}
        
        # Campos de texto
        text_fields = [
            "nombre_titular", "numero_credito", "banco_detectado", 
            "sistema_amortizacion", "plan_credito",
            # MEJORA 1: Tipo de documento detectado
            "tipo_documento_detectado",
            # MEJORA 4: Identificación del titular
            "identificacion_titular", "tipo_identificacion_titular"
        ]
        for field in text_fields:
            if field in data and data[field]:
                normalized[field] = str(data[field]).strip()
        
        # Campos de fecha
        date_fields = ["fecha_desembolso", "fecha_extracto"]
        for field in date_fields:
            if field in data and data[field]:
                try:
                    if isinstance(data[field], str):
                        normalized[field] = datetime.strptime(data[field], "%Y-%m-%d").date()
                    elif isinstance(data[field], date):
                        normalized[field] = data[field]
                except ValueError:
                    logger.warning(f"No se pudo parsear fecha {field}: {data[field]}")
        
        # Campos enteros
        int_fields = [
            "plazo_total_meses", "cuotas_pactadas", "cuotas_pagadas",
            "cuotas_pendientes", "cuotas_vencidas"
        ]
        for field in int_fields:
            if field in data and data[field] is not None:
                try:
                    normalized[field] = int(data[field])
                except (ValueError, TypeError):
                    logger.warning(f"No se pudo convertir a entero {field}: {data[field]}")
        
        # Campos decimales (montos y tasas)
        decimal_fields = [
            "tasa_interes_pactada_ea", "tasa_interes_cobrada_ea",
            "tasa_interes_subsidiada_ea", "tasa_mora_ea",
            "valor_prestado_inicial", "valor_cuota_sin_seguros",
            "valor_cuota_con_seguros", "beneficio_frech_mensual",
            "valor_cuota_con_subsidio", "saldo_capital_pesos",
            "total_por_pagar", "saldo_capital_uvr", "valor_uvr_fecha_extracto",
            "valor_cuota_uvr", "seguro_vida", "seguro_incendio",
            "seguro_terremoto", "intereses_corrientes_periodo", "intereses_mora"
        ]
        for field in decimal_fields:
            if field in data and data[field] is not None:
                try:
                    # Limpiar el valor (remover comas, espacios)
                    value = str(data[field]).replace(",", "").replace(" ", "")
                    normalized[field] = Decimal(value)
                except (InvalidOperation, ValueError):
                    logger.warning(f"No se pudo convertir a decimal {field}: {data[field]}")
        
        # Convertir tasas de porcentaje a decimal si son muy grandes
        # (Gemini puede retornar 9.53 en lugar de 0.0953)
        tasa_fields = [
            "tasa_interes_pactada_ea", "tasa_interes_cobrada_ea",
            "tasa_interes_subsidiada_ea", "tasa_mora_ea"
        ]
        for field in tasa_fields:
            if field in normalized and normalized[field] is not None:
                if normalized[field] > 1:
                    # Es un porcentaje, convertir a decimal
                    normalized[field] = normalized[field] / Decimal("100")
        
        return normalized
    
    async def compare_names(
        self,
        pdf_name: str,
        user_name: str
    ) -> NameComparisonResult:
        """
        Compara el nombre del PDF con el nombre del usuario.
        
        Args:
            pdf_name: Nombre extraído del PDF
            user_name: Nombre del usuario registrado
            
        Returns:
            NameComparisonResult con el resultado de la comparación
        """
        if not self.is_configured:
            # Fallback: comparación simple
            return self._simple_name_comparison(pdf_name, user_name)
        
        try:
            prompt = NAME_COMPARISON_PROMPT.format(
                pdf_name=pdf_name,
                user_name=user_name
            )
            
            response = self._client.models.generate_content(
                model=self.MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=1024,
                )
            )
            
            if response and response.text:
                # Parsear respuesta
                json_text = response.text.strip()
                if json_text.startswith("```"):
                    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', json_text)
                    if match:
                        json_text = match.group(1)
                
                data = json.loads(json_text)
                
                return NameComparisonResult(
                    match=data.get("match", False),
                    similarity=float(data.get("similarity", 0.0)),
                    pdf_name_normalized=pdf_name.upper().strip(),
                    user_name_normalized=user_name.upper().strip(),
                    explanation=data.get("explanation", "")
                )
        except Exception as e:
            logger.warning(f"Error en comparación con Gemini, usando fallback: {e}")
        
        return self._simple_name_comparison(pdf_name, user_name)
    
    def _simple_name_comparison(
        self,
        pdf_name: str,
        user_name: str
    ) -> NameComparisonResult:
        """
        Comparación simple de nombres sin usar IA.
        """
        # Normalizar nombres
        def normalize(name: str) -> set[str]:
            # Remover tildes
            replacements = {
                'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
                'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
                'ñ': 'n', 'Ñ': 'N'
            }
            for old, new in replacements.items():
                name = name.replace(old, new)
            
            # Convertir a mayúsculas y dividir en palabras
            words = set(name.upper().split())
            # Remover conectores
            words -= {"DE", "DEL", "LA", "LOS", "LAS", "Y"}
            return words
        
        pdf_words = normalize(pdf_name)
        user_words = normalize(user_name)
        
        # Calcular similitud por palabras en común
        if not pdf_words or not user_words:
            return NameComparisonResult(
                match=False,
                similarity=0.0,
                pdf_name_normalized=pdf_name.upper(),
                user_name_normalized=user_name.upper(),
                explanation="Uno de los nombres está vacío"
            )
        
        common = pdf_words & user_words
        total = pdf_words | user_words
        similarity = len(common) / len(total) if total else 0.0
        
        # Considerar match si:
        # - >70% de similitud, O
        # - El nombre más corto está completamente contenido en el más largo
        shorter = pdf_words if len(pdf_words) <= len(user_words) else user_words
        longer = user_words if len(pdf_words) <= len(user_words) else pdf_words
        
        # Verificar si el más corto está contenido en el más largo
        shorter_in_longer = shorter.issubset(longer) and len(common) > 0
        
        match = similarity >= 0.7 or shorter_in_longer
        
        return NameComparisonResult(
            match=match,
            similarity=similarity,
            pdf_name_normalized=" ".join(sorted(pdf_words)),
            user_name_normalized=" ".join(sorted(user_words)),
            explanation=f"Palabras en común: {common}" if common else "Sin palabras en común"
        )
    
    async def validate_document(
        self,
        pdf_content: bytes
    ) -> tuple[bool, float, str]:
        """
        Valida que el documento sea un extracto de crédito hipotecario real.
        
        Returns:
            Tuple de (es_valido, confianza, razon)
        """
        # La validación se hace como parte de la extracción
        result = await self.extract_credit_data(pdf_content)
        
        return (
            result.es_extracto_hipotecario,
            result.confidence,
            result.message
        )


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE CONVENIENCIA
# ═══════════════════════════════════════════════════════════════════════════════

# Instancia global del servicio
_gemini_service: Optional[GeminiService] = None


def get_gemini_service() -> GeminiService:
    """Obtiene la instancia global del servicio Gemini."""
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService()
    return _gemini_service


async def extract_credit_data_from_pdf(
    pdf_content: bytes,
    context: dict | None = None
) -> ExtractionResult:
    """
    Función de conveniencia para extraer datos de un PDF.
    """
    service = get_gemini_service()
    return await service.extract_credit_data(pdf_content, context)


def map_extraction_to_analysis(
    extraction: ExtractionResult,
    documento_id: str,
    usuario_id: str
) -> dict:
    """
    Mapea el resultado de extracción al formato del modelo AnalisisHipotecario.
    
    NOTA: El banco_detectado (string) debe resolverse a banco_id (FK) 
    en el servicio que use este mapping, buscando en la tabla bancos.
    """
    data = extraction.data
    
    return {
        "documento_id": documento_id,
        "usuario_id": usuario_id,
        
        # Identificación
        "nombre_titular_extracto": data.get("nombre_titular"),
        "numero_credito": data.get("numero_credito"),
        "sistema_amortizacion": data.get("sistema_amortizacion"),
        "plan_credito": data.get("plan_credito"),
        
        # Fechas
        "fecha_desembolso": data.get("fecha_desembolso"),
        "fecha_extracto": data.get("fecha_extracto"),
        "plazo_total_meses": data.get("plazo_total_meses"),
        
        # Cuotas
        "cuotas_pactadas": data.get("cuotas_pactadas"),
        "cuotas_pagadas": data.get("cuotas_pagadas"),
        "cuotas_pendientes": data.get("cuotas_pendientes"),
        
        # Tasas (ya convertidas a decimal)
        "tasa_interes_pactada_ea": data.get("tasa_interes_pactada_ea"),
        "tasa_interes_cobrada_ea": data.get("tasa_interes_cobrada_ea"),
        "tasa_interes_subsidiada_ea": data.get("tasa_interes_subsidiada_ea"),
        "tasa_mora_pactada_ea": data.get("tasa_mora_ea"),
        
        # Montos
        "valor_prestado_inicial": data.get("valor_prestado_inicial"),
        "valor_cuota_sin_seguros": data.get("valor_cuota_sin_seguros"),
        "valor_cuota_con_seguros": data.get("valor_cuota_con_seguros"),
        "beneficio_frech_mensual": data.get("beneficio_frech_mensual"),
        "valor_cuota_con_subsidio": data.get("valor_cuota_con_subsidio"),
        "saldo_capital_pesos": data.get("saldo_capital_pesos"),
        
        # UVR
        "saldo_capital_uvr": data.get("saldo_capital_uvr"),
        "valor_uvr_fecha_extracto": data.get("valor_uvr_fecha_extracto"),
        
        # Seguros
        "seguro_vida": data.get("seguro_vida"),
        "seguro_incendio": data.get("seguro_incendio"),
        "seguro_terremoto": data.get("seguro_terremoto"),
    }
