import { type ClassValue, clsx } from 'clsx';

const COP_CURRENCY_FORMATTER = new Intl.NumberFormat('es-CO', {
  style: 'currency',
  currency: 'COP',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const NUMBER_FORMATTER = new Intl.NumberFormat('es-CO', {
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

const INTEGER_FORMATTER = new Intl.NumberFormat('es-CO', {
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

/**
 * Utility para combinar clases de Tailwind CSS
 */
export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

/**
 * Formatea números de identificación (cédula)
 */
export function formatIdentificacion(value: string): string {
  // Elimina caracteres no numéricos
  const numbers = value.replace(/\D/g, '');
  
  // Limita a 10 dígitos
  return numbers.slice(0, 10);
}

/**
 * Valida formato de email
 */
export function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * Valida formato de teléfono colombiano
 */
export function isValidPhone(phone: string): boolean {
  // Acepta formato: +57 3XX XXXXXXX o 3XXXXXXXXX
  const phoneRegex = /^(\+57)?3\d{9}$/;
  return phoneRegex.test(phone.replace(/\s/g, ''));
}

/**
 * Formatea número de teléfono
 */
export function formatPhone(value: string): string {
  const numbers = value.replace(/\D/g, '');
  
  if (numbers.length <= 3) return numbers;
  if (numbers.length <= 6) return `${numbers.slice(0, 3)} ${numbers.slice(3)}`;
  return `${numbers.slice(0, 3)} ${numbers.slice(3, 6)} ${numbers.slice(6, 10)}`;
}

export function formatCopCurrency(value?: number | null): string {
  if (value === undefined || value === null || Number.isNaN(Number(value))) {
    return '-';
  }
  return COP_CURRENCY_FORMATTER.format(Number(value));
}

export function formatNumberWithThousands(value?: number | null): string {
  if (value === undefined || value === null || Number.isNaN(Number(value))) {
    return '-';
  }
  return NUMBER_FORMATTER.format(Number(value));
}

export function cleanDigitsInput(value: string): string {
  return value.replace(/\D/g, '');
}

export function formatDigitsInput(value: string): string {
  if (!value) return '';
  const digits = cleanDigitsInput(value);
  if (!digits) return '';
  const parsed = Number(digits);
  if (Number.isNaN(parsed)) return '';
  return INTEGER_FORMATTER.format(parsed);
}

/**
 * Calcula los totales del resumen de crédito separando correctamente
 * el pago del cliente, el subsidio FRECH y el total abonado al banco.
 *
 * Reglas:
 *   pagadoCliente     = cuotaPagadaCliente × cuotasPagadas
 *   frechAcumulado    = beneficioFrech     × cuotasPagadas
 *   totalAbonadoCredito = pagadoCliente + frechAcumulado
 *
 * Donde cuotaPagadaCliente = cuotaTotal − beneficioFrech
 */
export interface CreditSummaryInput {
  cuotaTotal: number;
  beneficioFrech: number;
  cuotasPagadas: number;
}

export interface CreditSummaryResult {
  pagadoCliente: number;
  frechAcumulado: number;
  totalAbonadoCredito: number;
}

export function calculateCreditSummary(input: CreditSummaryInput): CreditSummaryResult {
  const { cuotaTotal, beneficioFrech, cuotasPagadas } = input;
  const cuotaPagadaCliente = Math.max(cuotaTotal - beneficioFrech, 0);
  const pagadoCliente = cuotaPagadaCliente * cuotasPagadas;
  const frechAcumulado = beneficioFrech * cuotasPagadas;
  const totalAbonadoCredito = pagadoCliente + frechAcumulado;
  return { pagadoCliente, frechAcumulado, totalAbonadoCredito };
}

export interface NumericInputOptions {
  /** Dígitos permitidos después de la coma decimal. 0 = solo enteros. */
  maxDecimals?: number;
  /** Aplica separador de miles (punto) a la parte entera. */
  thousands?: boolean;
}

/**
 * Descompone lo que el usuario escribió usando la convención es-CO:
 * el punto es SIEMPRE separador de miles y la coma es el decimal.
 *
 * Interpretar el punto como decimal rompía el campo apenas superaba las
 * tres cifras: al formatear 1000 como "1.000" la siguiente tecla releía ese
 * punto como coma decimal y colapsaba el valor a "1,00".
 */
function splitNumericInput(
  value: string,
  maxDecimals: number
): { integerDigits: string; decimalDigits: string; hasDecimalMark: boolean } {
  const sanitized = String(value ?? '').replace(/[^\d.,]/g, '');
  const withoutThousands = sanitized.replace(/\./g, '');
  const [integerRaw = '', ...decimalParts] = withoutThousands.split(',');

  const hasDecimalMark = maxDecimals > 0 && decimalParts.length > 0;
  const integerDigits = cleanDigitsInput(integerRaw).replace(/^0+(?=\d)/, '');
  const decimalDigits = hasDecimalMark
    ? cleanDigitsInput(decimalParts.join('')).slice(0, maxDecimals)
    : '';

  return { integerDigits, decimalDigits, hasDecimalMark };
}

/**
 * Normaliza el texto de un campo numérico mientras se escribe.
 * Conserva la coma final para que el usuario pueda seguir con los decimales.
 */
export function formatNumericInput(value: string, options: NumericInputOptions = {}): string {
  const { maxDecimals = 2, thousands = true } = options;
  const { integerDigits, decimalDigits, hasDecimalMark } = splitNumericInput(value, maxDecimals);

  if (!integerDigits && !hasDecimalMark) return '';

  let formattedInteger = '';
  if (integerDigits) {
    formattedInteger = thousands
      ? INTEGER_FORMATTER.format(Number(integerDigits))
      : integerDigits;
  } else if (hasDecimalMark) {
    formattedInteger = '0';
  }

  return hasDecimalMark ? `${formattedInteger},${decimalDigits}` : formattedInteger;
}

/** Convierte el texto de un campo numérico al número que espera la API. */
export function parseNumericInput(value: string, maxDecimals = 2): number | null {
  const { integerDigits, decimalDigits } = splitNumericInput(value, maxDecimals);
  if (!integerDigits && !decimalDigits) return null;

  const parsed = Number(`${integerDigits || '0'}.${decimalDigits || '0'}`);
  return Number.isFinite(parsed) ? parsed : null;
}

/**
 * Convierte un número de la API al texto localizado que muestra el campo.
 * `String(1234.5)` usa punto decimal, así que no puede pasarse directo a
 * `formatNumericInput` (que lee el punto como separador de miles).
 */
export function numberToNumericInput(
  value?: number | string | null,
  options: NumericInputOptions = {}
): string {
  if (value === null || value === undefined || value === '') return '';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '';

  const { maxDecimals = 2, thousands = true } = options;
  const [integerPart, decimalPart = ''] = numeric.toFixed(maxDecimals).split('.');
  const trimmedDecimals = decimalPart.replace(/0+$/, '');
  const localized = trimmedDecimals ? `${integerPart},${trimmedDecimals}` : integerPart;

  return formatNumericInput(localized, { maxDecimals, thousands });
}

export function formatMonetaryInput(value: string): string {
  return formatNumericInput(value, { maxDecimals: 2, thousands: true });
}

export function parseMonetaryInput(value: string): number | null {
  return parseNumericInput(value, 2);
}
