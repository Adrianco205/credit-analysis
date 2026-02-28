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

export function formatMonetaryInput(value: string): string {
  if (!value) return '';

  const sanitized = value.replace(/\s/g, '').replace(/[^\d.,]/g, '');
  if (!sanitized) return '';

  const lastComma = sanitized.lastIndexOf(',');
  const lastDot = sanitized.lastIndexOf('.');
  const decimalIndex = Math.max(lastComma, lastDot);

  let integerPartRaw = sanitized;
  let decimalPartRaw = '';

  if (decimalIndex >= 0) {
    integerPartRaw = sanitized.slice(0, decimalIndex);
    decimalPartRaw = sanitized.slice(decimalIndex + 1);
  }

  const integerDigits = cleanDigitsInput(integerPartRaw);
  const decimalDigits = cleanDigitsInput(decimalPartRaw).slice(0, 2);

  const formattedInteger = integerDigits
    ? INTEGER_FORMATTER.format(Number(integerDigits))
    : '0';

  return decimalDigits ? `${formattedInteger},${decimalDigits}` : formattedInteger;
}

export function parseMonetaryInput(value: string): number | null {
  if (!value) return null;

  const sanitized = value.replace(/\s/g, '').replace(/[^\d.,]/g, '');
  if (!sanitized) return null;

  const lastComma = sanitized.lastIndexOf(',');
  const lastDot = sanitized.lastIndexOf('.');
  const decimalIndex = Math.max(lastComma, lastDot);

  let integerPartRaw = sanitized;
  let decimalPartRaw = '';

  if (decimalIndex >= 0) {
    integerPartRaw = sanitized.slice(0, decimalIndex);
    decimalPartRaw = sanitized.slice(decimalIndex + 1);
  }

  const integerDigits = cleanDigitsInput(integerPartRaw);
  const decimalDigits = cleanDigitsInput(decimalPartRaw).slice(0, 2);

  if (!integerDigits && !decimalDigits) {
    return null;
  }

  const normalized = `${integerDigits || '0'}${decimalDigits ? `.${decimalDigits}` : ''}`;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}
