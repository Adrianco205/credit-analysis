'use client';

import { FileText, ShieldCheck } from 'lucide-react';

import { Card, CardHeader } from '@/components/ui/card';
import { TermsAndConditionsContent } from '@/components/legal/TermsAndConditionsContent';
import { PrivacyPolicyContent } from '@/components/legal/PrivacyPolicyContent';

export default function ClientContratoPage() {
  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold text-[var(--verde-bosque)]">Tratamiento de información</h1>
        <p className="text-sm text-gray-600">
          Aquí puedes consultar en cualquier momento los términos y la política de privacidad aceptados durante tu registro.
        </p>
      </div>

      <Card className="border-t-4 border-[var(--verde-hoja)]">
        <CardHeader>
          <h2 className="text-xl font-semibold flex items-center gap-2 text-gray-800">
            <ShieldCheck className="text-[var(--verde-hoja)]" size={20} />
            Documentos legales vigentes
          </h2>
        </CardHeader>
        <div className="bg-[var(--gray-50)] border border-gray-200 rounded-xl p-4 text-sm text-gray-700">
          La aceptación se realiza al crear tu cuenta en EcoFinanzas y aplica para el uso de la plataforma.
        </div>
      </Card>

      <Card className="border border-gray-200">
        <CardHeader>
          <h2 className="text-xl font-semibold flex items-center gap-2 text-gray-800">
            <FileText className="text-[var(--verde-hoja)]" size={20} />
            Términos y condiciones
          </h2>
        </CardHeader>
        <TermsAndConditionsContent />
      </Card>

      <Card className="border border-gray-200">
        <CardHeader>
          <h2 className="text-xl font-semibold flex items-center gap-2 text-gray-800">
            <FileText className="text-[var(--verde-hoja)]" size={20} />
            Política de privacidad y protección de datos
          </h2>
        </CardHeader>
        <PrivacyPolicyContent />
      </Card>
    </div>
  );
}
