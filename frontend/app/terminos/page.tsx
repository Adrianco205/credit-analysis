import Link from 'next/link';

import { Card } from '@/components/ui/card';
import { TermsAndConditionsContent } from '@/components/legal/TermsAndConditionsContent';

export default function TerminosPage() {
  return (
    <div className="min-h-screen bg-[var(--gray-50)] py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="flex justify-between items-center gap-4">
          <h1 className="text-2xl md:text-3xl font-bold text-[var(--verde-bosque)]">Términos y condiciones</h1>
          <Link href="/auth/register" className="text-sm font-medium text-[var(--verde-bosque)] hover:text-[var(--verde-hoja)] underline">
            Volver al registro
          </Link>
        </div>
        <Card className="border-t-4 border-[var(--verde-hoja)]">
          <TermsAndConditionsContent />
        </Card>
      </div>
    </div>
  );
}
