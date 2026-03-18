import React from 'react';

const SECTION_TITLE_CLASS = 'text-xl md:text-2xl font-bold text-[var(--verde-bosque)]';
const SUBTITLE_CLASS = 'text-lg font-semibold text-[var(--verde-bosque)]';
const PARAGRAPH_CLASS = 'text-sm md:text-base text-gray-700 leading-relaxed';
const LIST_CLASS = 'list-disc pl-6 space-y-2 text-sm md:text-base text-gray-700 leading-relaxed';

export function TermsAndConditionsContent() {
  return (
    <div className="space-y-8">
      <section className="space-y-4">
        <h1 className={SECTION_TITLE_CLASS}>Términos y condiciones de uso — PerFinanzas</h1>
        <p className={PARAGRAPH_CLASS}>
          Estos términos y condiciones regulan el acceso y uso de la plataforma PerFinanzas. Al crear una cuenta y usar
          los servicios, el usuario declara que leyó, entendió y aceptó integralmente estas condiciones.
        </p>
      </section>

      <section className="space-y-4">
        <h2 className={SUBTITLE_CLASS}>Objeto del servicio</h2>
        <p className={PARAGRAPH_CLASS}>
          PerFinanzas ofrece herramientas de análisis y proyección financiera para apoyar la toma de decisiones del
          usuario. La información mostrada tiene fines orientativos y no constituye asesoría financiera, legal o
          tributaria personalizada.
        </p>
      </section>

      <section className="space-y-4">
        <h2 className={SUBTITLE_CLASS}>Responsabilidad del usuario</h2>
        <ul className={LIST_CLASS}>
          <li>Proporcionar información veraz, completa y actualizada.</li>
          <li>Mantener la confidencialidad de sus credenciales de acceso.</li>
          <li>Usar la plataforma de manera lícita y de buena fe.</li>
          <li>No realizar actividades que comprometan la seguridad o disponibilidad del servicio.</li>
        </ul>
      </section>

      <section className="space-y-4">
        <h2 className={SUBTITLE_CLASS}>Alcance de resultados</h2>
        <p className={PARAGRAPH_CLASS}>
          Las simulaciones, proyecciones y análisis dependen de la calidad de los datos suministrados y de parámetros
          técnicos del sistema. En consecuencia, pueden variar frente a cálculos o decisiones de terceros.
        </p>
      </section>

      <section className="space-y-4">
        <h2 className={SUBTITLE_CLASS}>Protección de datos personales</h2>
        <p className={PARAGRAPH_CLASS}>
          El tratamiento de datos personales se rige por la Política de Privacidad y Protección de Datos Personales de
          PerFinanzas, la cual hace parte integral de estos términos y se encuentra disponible para consulta permanente.
        </p>
      </section>

      <section className="space-y-4">
        <h2 className={SUBTITLE_CLASS}>Propiedad intelectual</h2>
        <p className={PARAGRAPH_CLASS}>
          Los contenidos, diseños, marcas, software y demás elementos de PerFinanzas están protegidos por la normativa
          aplicable de propiedad intelectual. No se autoriza su reproducción o explotación no permitida por la ley.
        </p>
      </section>

      <section className="space-y-4">
        <h2 className={SUBTITLE_CLASS}>Modificaciones</h2>
        <p className={PARAGRAPH_CLASS}>
          PerFinanzas podrá actualizar estos términos y su política de privacidad cuando sea necesario para fines
          operativos, normativos o de mejora del servicio. Los cambios relevantes serán informados por canales oficiales.
        </p>
      </section>

      <section className="space-y-4">
        <h2 className={SUBTITLE_CLASS}>Aceptación</h2>
        <p className={PARAGRAPH_CLASS}>
          Al registrarse en la plataforma, el usuario manifiesta su aceptación expresa de estos términos y de la política
          de privacidad vigente.
        </p>
      </section>
    </div>
  );
}


