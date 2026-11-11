# Producto CRM CBN

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

FastAPI y React aceptados en ADR-001. Herramientas locales mínimas delegadas mediante ADR-002; integración SQL Server y API diferida expresamente por el propietario.

## Users

Asesores y admisiones, coordinador y administrador, según mapa documental. Aspirante como usuario del formulario público. Perfiles definitivos y permisos pendientes, no autenticación implementada.

## Product Purpose

Plataforma nueva de admisiones y relacionamiento. El corte de fases 0/2/3 es un diseño funcional local revisable, no operación real.

## Operating Context

Revisión en escritorio y móvil, estado temporal y fixtures ficticios. Flujos demostrables: Clientes, Inbox, formulario y borradores de Ajustes. Fase 3 añade atención por hilo, tareas/timeline temporales y Asistente/IA con plantillas revisadas; ninguna respuesta es un modelo de IA. Recargar o restablecer elimina los cambios locales.

## Capabilities and Constraints

SQL Server SIIE es la fuente transaccional única futura. Sin DB/API, auth, IA, envío, datos personales, secretos ni servicios reales en todo el corte local. Creadores es expansión distinta de Clientes, aún condicionada. UI de preview en español neutral propuesto, no decisión de idioma final.

## Brand Commitments

Texto CRM CBN, sin inventar logotipo. Se preservan mockups y referencias de `docs/design/`; dirección Institucional sereno provisional en `docs/design-system.md`.

## Evidence on Hand

ADR-001/002/003/004, mapa de doce módulos, galerías clara/oscura y cuatro referencias Markdown. Referencias UI principalmente estáticas, no contratos internos probados. No datos de clientes reales ni aprobación visual final.

## Product Principles

- Control humano y transparencia del estado de demostración.
- Probar en la capa solicitada sin equiparar build a navegador o integración.
- Preservar SIIE y mantener autorización separada para conexiones/escrituras.
- Compartir sistema visual y contratos, sin duplicar fuentes de verdad.

## Accessibility & Inclusion

Objetivo propuesto WCAG 2.2 AA; fase local comprueba semántica, etiquetas, teclado, foco y adaptación. No certificación ni pruebas de lector de pantalla completas.
