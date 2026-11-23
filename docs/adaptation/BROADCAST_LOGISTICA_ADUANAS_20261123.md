# Seguimiento de Logística y Aduanas — 23/11/2026

El titular autoriza las dos campañas con sus plantillas Meta respectivas y confirma que las políticas de preinscripción incluían autorización de seguimiento WhatsApp. Esta declaración se registra como evidencia del titular; no se afirma haber inspeccionado el texto de las políticas ni que el Excel incluyera un opt-in.

## Preparación

Se revisaron 50 registros fuente: un teléfono inválido y tres registros anteriores que comparten número quedan fuera. Se conserva la preinscripción más reciente por número, sin fusionar personas. El contraste nativo de 46 seleccionados reconoció 35 importados e incorporó ocho fichas adicionales; tres posibles coincidencias con CRM quedan para revisión. Cohorte prevista: 32 Logística y 11 Aduanas, sujeta a las guardas de canal y consentimiento.

La nueva vinculación explícita trabaja en lotes de diez y exige permisos de campañas, CRM e Inbox, reautenticación, evidencia y vigencia máxima de dos días. Conserva la autorización nativa con CAS e idempotencia. Una revocación anterior, otro canal o una conversación real/intervención humana exigen revisión individual. No crea entradas recibidas ni verifica la existencia del destinatario en Meta. Reutiliza la conversación vacía de importación y habilita IA mediante el control nativo con nuevo epoch sólo si nunca hubo mensajes o intervención humana. Esta preparación no envía mensajes.

El titular amplía después la habilitación a todos los preinscritos del CRM, para completar la revisión de una vez. El botón nativo carga hasta 5.000 fichas con fuente de importación, teléfono válido y programa declarado, y procesa automáticamente grupos de diez con una sola evidencia. Conserva autorizaciones vigentes y pone revocaciones/conflictos de canal/historial en revisión sin detener las demás fichas. Esto no amplía el envío: sólo se activarán Logística y Aduanas. Las fichas originalmente dudosas que no fueron importadas siguen fuera del CRM.

## Etapa después del envío

La campaña permite elegir una etapa activa del CRM con permiso `crm.write`. La etapa se fija en la instantánea de destinatarios. Sólo un recibo auténtico Meta `sent`, `delivered` o `read` dispara la actualización; `accepted`, cola, preparación, fallo e incertidumbre no lo hacen. La operación usa el registro nativo de intentos, una clave idempotente por destinatario y auditoría compartida. Un CAS conserva cambios de etapa posteriores del asesor y no altera contactos fusionados. Si se revoca la autoridad de campaña, el recibo se conserva sin ejecutar el cambio CRM.

Para estas dos campañas se configurará **Seguimiento**. El valor predeterminado de las demás campañas conserva la etapa actual.

## Validación previa a publicar

154 pruebas backend seleccionadas y 25 frontend pasan; TypeScript, ESLint de archivos cambiados, Ruff de módulos/pruebas nuevos y workspace build pasan. Se conserva la advertencia histórica de bundle. Los archivos backend heredados contienen avisos previos de formato fuera del cambio. Sin DDL, seeds, servicios nuevos, escrituras SIIE ni cambios de modelos.

El primer despliegue `6cf1b0a` estuvo saludable, pero la vinculación fue rechazada por la restricción nativa de una conversación por contacto (`23505`); cero mensajes. Un diagnóstico transaccional se revirtió íntegramente. La corrección reutiliza la conversación vacía y agrega regresión para impedir una segunda inserción. Se conserva el intento fallido, sin atribuirle vinculación ni consentimiento completados.

Publicación, vinculación efectiva, activación y resultados reales pendientes en este corte. Los recibos nominales permanecen únicamente en `.local/preinscritos-import/logistica-aduanas/`.
