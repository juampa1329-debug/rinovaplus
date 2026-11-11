# Registro de aprobación visual

**Estado:** los 12 mockups están disponibles e inspeccionados por el agente coordinador; **todas las revisiones/aprobaciones humanas pendientes**. **Fecha:** 2026-10-13, America/Bogota. Responsable aprobador: propietario, aún sin firma/confirmación registrada. Una imagen creada/inspeccionada no equivale a aprobación humana.

La tabla original siguiente corresponde al **modo claro** y conserva sus decisiones pendientes. Los 12 PNG del [modo oscuro](dark-mode.md) están disponibles por separado; pedir conservar/ver las propuestas no constituye aprobación de pantalla, tema o implementación.

## Checklist por pantalla

Registrar decisión humana después de ver el [archivo real en la galería](README.md). La inspección del coordinador valida composición/legibilidad principal; no pruebas funcionales ni aprobación por el propietario. Los estados alternos y adaptaciones del [mapa](module-map.md) requieren aceptación textual y, si se solicita, imágenes adicionales. La muestra UI editable sigue pendiente antes de implementación.

| Módulo | Archivo disponible e inspeccionado | Composición/acción aprobada | Estados/permisos/límites aceptados | Responsable / fecha / observaciones |
|---|---|---|---|---|
| M-01 Acceso | Mockup disponible; aprobación pendiente | [ ] Pendiente | [ ] Pendiente | Pendiente. |
| M-02 Resumen | Mockup disponible; aprobación pendiente | [ ] Pendiente | [ ] Pendiente | Pendiente. |
| M-03 Prospectos | Mockup disponible; aprobación pendiente | [ ] Pendiente | [ ] Pendiente | Pendiente. |
| M-04 Conversaciones | Mockup disponible; aprobación pendiente | [ ] Pendiente | [ ] Pendiente | Pendiente; atención especial a carrera de handoff. |
| M-05 Formulario | Mockup disponible; aprobación pendiente | [ ] Pendiente | [ ] Pendiente | Pendiente; token/privacidad/solicitud ≠ matrícula. |
| M-06 Revisión académica | Mockup disponible; aprobación pendiente | [ ] Pendiente | [ ] Pendiente | Pendiente; aprobación visual ≠ autorización core. |
| M-07 Asistente | Mockup disponible revisión 2; aprobación pendiente | [ ] Pendiente | [ ] Pendiente | Pendiente; políticas/invariantes no editables. |
| M-08 Conocimiento | Mockup disponible; aprobación pendiente | [ ] Pendiente | [ ] Pendiente | Pendiente; fuente y RAG diferenciado. |
| M-09 Memoria | Mockup disponible; aprobación pendiente | [ ] Pendiente | [ ] Pendiente | Pendiente; expansión/consentimiento aún no aprobados. |
| M-10 Integraciones | Mockup disponible; aprobación pendiente | [ ] Pendiente | [ ] Pendiente | Pendiente; sin claves/estados reales. |
| M-11 Retención | Mockup disponible; aprobación pendiente | [ ] Pendiente | [ ] Pendiente | Pendiente; intención conceptual, falta descubrimiento. |
| M-12 Corporativo | Mockup disponible; aprobación pendiente | [ ] Pendiente | [ ] Pendiente | Pendiente; intención conceptual, falta descubrimiento. |

## Revisión independiente del modo oscuro

Disponibilidad no equivale a aprobación humana. Registrar decisión, observaciones y versión por módulo sin modificar casillas del claro por inferencia.

| Módulo | Disponibilidad oscura | Apariencia/legibilidad aprobada por propietario | Observaciones / fecha |
|---|---|---|---|
| M-01 | PNG disponible | [ ] Pendiente | Pendiente. |
| M-02 | PNG disponible | [ ] Pendiente | Pendiente. |
| M-03 | PNG disponible | [ ] Pendiente | Pendiente. |
| M-04 | PNG disponible | [ ] Pendiente | Pendiente. |
| M-05 | PNG disponible | [ ] Pendiente | Pendiente; referencia móvil. |
| M-06 | PNG disponible | [ ] Pendiente | Pendiente. |
| M-07 | PNG disponible | [ ] Pendiente | Pendiente. |
| M-08 | PNG disponible | [ ] Pendiente | Pendiente. |
| M-09 | PNG disponible | [ ] Pendiente | Pendiente; expansión condicionada. |
| M-10 | PNG disponible | [ ] Pendiente | Pendiente. |
| M-11 | PNG disponible | [ ] Pendiente | Pendiente; futuro no especificado. |
| M-12 | PNG disponible | [ ] Pendiente | Pendiente; futuro no especificado. |

## Ampliación M-10 — alternativas de ajustes

[Análisis y diseños propuestos](settings-ai.md), tres PNG disponibles e inspeccionados por el coordinador; los antiguos M-10 claro/oscuro no se reemplazan. Ninguna alternativa, proveedor/modelo ni flujo de activación está aprobado.

- [ ] Revisar A: lista de proveedores e inspector persistente.
- [ ] Revisar B: catálogo compacto con drawer.
- [ ] Revisar C: alta guiada de credencial.
- [ ] Registrar selección/ajustes con archivo/versión y palabras del propietario en P-018.
- [ ] Aceptar borrador/auth-discovery/selección modelo/test sintético final/activación separados; autenticación no prueba modelo y API sin listado usa catálogo validado del adapter. Write-only keys, roles/egress/coste y controles reales siguen pendientes de prueba.

## Decisiones globales separadas

**Decisión humana registrada:** estructura de [Ajustes](settings.md) con IA, Canales, APIs, Diagnóstico, Usuarios, Perfil y Seguridad; excluir Industria y pestaña Plan. Es aprobación de **alcance de secciones para diseño**, no de checks/layouts/funciones existentes, nombre o implementación. Las casillas anteriores se conservan pendientes.

- [ ] Revisar adaptación de [SET-01 IA](settings-assistant.md): estilo, parámetros por modelo, ritmo transparente y referencia a APIs.
- [ ] Revisar knowledge M-08: fuentes/aliases/versionado, evaluación y autorización de publicación en 7C.
- [ ] Revisar [matriz integral desde MD](settings-specification.md) de Canales/Diagnóstico/Usuarios/Perfil/Seguridad; referencias textuales ya recibidas, capturas opcionales para fidelidad. Fuente no aprobación de backend/roles/operaciones.
- [ ] Aceptar gates de firma/OAuth/registro número, aislamiento de simulación, invitación/permisos, perfil/2FA/export/baja revisada antes de cualquier implementación.

- [ ] Aceptar o ajustar dirección “Institucional sereno” y valores de referencia de [diseño](../design-system.md).
- [ ] Registrar preferencia/aprobación explícita de variante clara, oscura o ambas; ninguna seleccionada definitivamente.
- [ ] Confirmar marca oficial o mantener nombre provisional CRM CBN; no se ha recibido logotipo oficial.
- [ ] Confirmar idioma de UI; español neutral solo como preview propuesto.
- [ ] Aceptar navegación, densidad y comportamiento desktop/mobile descrito; no declarar todos los viewports renderizados.
- [ ] Revisar aviso IA, control humano, límites de datos y confirmaciones sensibles.
- [ ] Registrar alcance inicial y expansión; M-11/M-12 requieren descubrimiento independiente, no alcance aprobado por aprobar apariencia.

## Registro de resultado

Por pantalla: **pendiente**, **ajustes solicitados** o **aprobado visualmente**, con palabras del propietario, fecha y versión/archivo revisado. Registrar observaciones concretas y mantener evidencia anterior. No completar casillas en nombre del propietario.

La aprobación visual no elige una fuente/biblioteca de UI, no demuestra cumplimiento/accesibilidad, no autoriza DB/Git/despliegue y **no inicia implementación**. [P-015](../pending.md) se cierra solo con aceptación registrada; puertas técnicas de [fases](../roadmap.md) permanecen.
