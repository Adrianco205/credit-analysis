import React from 'react';

const SECTION_TITLE_CLASS = 'text-xl md:text-2xl font-bold text-[var(--verde-bosque)]';
const SUBTITLE_CLASS = 'text-lg font-semibold text-[var(--verde-bosque)]';
const PARAGRAPH_CLASS = 'text-sm md:text-base text-gray-700 leading-relaxed';
const LIST_CLASS = 'list-disc pl-6 space-y-2 text-sm md:text-base text-gray-700 leading-relaxed';

export function PrivacyPolicyContent() {
  return (
    <div className="space-y-8">
      <section className="space-y-4">
        <h1 className={SECTION_TITLE_CLASS}>Política para el manejo de datos personales de EcoFinanzas</h1>
        <p className={PARAGRAPH_CLASS}>
          EcoFinanzas, con sede en Barranquilla, Colombia, valora de manera especial la seguridad, la intimidad y la
          confidencialidad de los datos personales pertenecientes a sus clientes, usuarios, empleados, proveedores,
          accionistas, socios estratégicos y, en general, a todos los grupos de interés sobre los cuales realiza
          tratamiento de información personal.
        </p>
        <p className={PARAGRAPH_CLASS}>
          Por esta razón, y en estricto cumplimiento de las normas constitucionales y legales aplicables, ha adoptado la
          presente Política para el Manejo de Datos Personales, que regula la obtención, almacenamiento, procesamiento,
          gestión, cesión y salvaguarda de la información recibida por canales digitales, presenciales o telefónicos.
        </p>
      </section>

      <section className="space-y-4">
        <h2 className={SUBTITLE_CLASS}>Normativa aplicable</h2>
        <ul className={LIST_CLASS}>
          <li>Artículo 15 de la Constitución Política de Colombia.</li>
          <li>Ley Estatutaria 1266 de 2008.</li>
          <li>Ley 1273 de 2009.</li>
          <li>Ley Estatutaria 1581 de 2012.</li>
          <li>Decreto 1377 de 2013.</li>
          <li>Decreto 886 de 2014.</li>
          <li>Decreto 1074 de 2015.</li>
          <li>Título V de la Circular Única de la Superintendencia de Industria y Comercio.</li>
          <li>Demás normas concordantes sobre protección de datos personales.</li>
        </ul>
      </section>

      <section className="space-y-4">
        <h2 className={SUBTITLE_CLASS}>Contexto y alcance</h2>
        <p className={PARAGRAPH_CLASS}>
          EcoFinanzas, actuando como responsable del tratamiento, aplica esta política de acuerdo con la Ley 1581 de 2012,
          la Ley 1266 de 2008 y el Decreto 1377 de 2013, velando por la seguridad y calidad en el procesamiento de los
          datos personales suministrados por los titulares.
        </p>
        <p className={PARAGRAPH_CLASS}>
          Los titulares pueden ejercer sus derechos de conocer, actualizar, rectificar, suprimir la información y revocar
          la autorización concedida, salvo deber legal o contractual que impida dicha revocatoria o supresión.
        </p>
      </section>

      <section className="space-y-4">
        <h2 className={SUBTITLE_CLASS}>Autorizaciones y finalidades</h2>
        <ol className="list-decimal pl-6 space-y-2 text-sm md:text-base text-gray-700 leading-relaxed">
          <li>
            EcoFinanzas solicita autorización previa, expresa e informada para el tratamiento de los datos personales por
            medios verificables.
          </li>
          <li>
            La información se usa para la gestión, administración y optimización de servicios, ejecución de procesos
            internos, análisis estadístico y mejora de productos.
          </li>
          <li>
            Los datos no se transfieren a terceros sin consentimiento, salvo en los casos permitidos por la ley.
          </li>
          <li>
            El titular declara que la información suministrada es veraz, actual y precisa, y asume responsabilidad por
            inexactitudes.
          </li>
          <li>
            EcoFinanzas conserva evidencia de las autorizaciones y aplica reglas especiales para datos sensibles.
          </li>
        </ol>
      </section>

      <section className="space-y-4">
        <h2 className={SUBTITLE_CLASS}>Principios rectores</h2>
        <ul className={LIST_CLASS}>
          <li><strong>Legalidad:</strong> tratamiento conforme a la ley.</li>
          <li><strong>Finalidad:</strong> uso legítimo e informado al titular.</li>
          <li><strong>Libertad:</strong> consentimiento previo, expreso e informado.</li>
          <li><strong>Veracidad o calidad:</strong> datos exactos, completos y actualizados.</li>
          <li><strong>Transparencia:</strong> derecho a conocer la existencia y uso de los datos.</li>
          <li><strong>Acceso restringido:</strong> circulación limitada a autorizados.</li>
          <li><strong>Seguridad:</strong> medidas técnicas, humanas y administrativas adecuadas.</li>
          <li><strong>Confidencialidad:</strong> reserva de la información no pública.</li>
        </ul>
      </section>

      <section className="space-y-4">
        <h2 className={SUBTITLE_CLASS}>Duración del tratamiento</h2>
        <p className={PARAGRAPH_CLASS}>
          Los datos permanecerán en tratamiento durante la vigencia de la relación contractual, comercial o de servicio
          con EcoFinanzas y por el término adicional exigido por la ley aplicable.
        </p>
      </section>

      <section className="space-y-4">
        <h2 className={SUBTITLE_CLASS}>Derechos del titular</h2>
        <ul className={LIST_CLASS}>
          <li>Conocer, actualizar, rectificar, suprimir y revocar autorización sobre sus datos personales.</li>
          <li>Presentar consultas, peticiones y reclamos relacionados con protección de datos.</li>
          <li>Solicitar evidencia de la autorización otorgada para el tratamiento.</li>
          <li>Presentar queja ante la SIC luego de agotar el trámite interno correspondiente.</li>
        </ul>
      </section>

      <section className="space-y-4">
        <h2 className={SUBTITLE_CLASS}>Deberes de EcoFinanzas</h2>
        <ul className={LIST_CLASS}>
          <li>Garantizar el ejercicio pleno y efectivo de los derechos del titular.</li>
          <li>Informar finalidades de uso y mantener evidencia de autorizaciones.</li>
          <li>Proteger la información con controles de seguridad y acceso restringido.</li>
          <li>Actualizar, corregir y reportar novedades a encargados del tratamiento cuando corresponda.</li>
          <li>Atender consultas y reclamos en los términos legales.</li>
          <li>Reportar incidentes de seguridad a la autoridad competente cuando aplique.</li>
        </ul>
      </section>

      <section className="space-y-4">
        <h2 className={SUBTITLE_CLASS}>Atención de consultas, quejas y reclamos</h2>
        <p className={PARAGRAPH_CLASS}>
          Las consultas serán atendidas en un término máximo de quince (15) días hábiles desde su recepción. Si no es
          posible responder en dicho término, se informará al solicitante la causa de la demora y la nueva fecha,
          conforme a la ley.
        </p>
        <p className={PARAGRAPH_CLASS}>
          Los reclamos de corrección, actualización, supresión o revocatoria se tramitarán de acuerdo con el artículo 15
          de la Ley 1581 de 2012 y los procedimientos internos de EcoFinanzas.
        </p>
      </section>

      <section className="space-y-4">
        <h2 className={SUBTITLE_CLASS}>Relacionamiento con terceros</h2>
        <p className={PARAGRAPH_CLASS}>
          Cuando EcoFinanzas comparta datos personales con encargados o proveedores, exigirá contractualmente medidas de
          seguridad y confidencialidad equivalentes o superiores a las adoptadas internamente, y limitará su uso a las
          finalidades autorizadas.
        </p>
      </section>

      <section className="space-y-4">
        <h2 className={SUBTITLE_CLASS}>Vigencia</h2>
        <p className={PARAGRAPH_CLASS}>
          Esta Política de Tratamiento de Datos Personales entra en vigor a partir de su aprobación y expedición, y podrá
          ser actualizada por EcoFinanzas conforme a la normativa aplicable.
        </p>
      </section>
    </div>
  );
}
