# P12: puesta online institucional

Plan inicial del 28 de octubre de 2026.

Al 15 de noviembre de 2026 (UTC), **3/6 pasos técnicos completos (50,00 %)** para RinovaPlus. Oracle, Coolify y HTTPS están verificados. La candidata con PostgreSQL se concilió y se activó, con SIIE en su SQL Server. El acceso público entrega el formulario y conserva el control de sesión. Los pasos 1 a 3 se acreditan para el CRM. El paso 5 tiene copia previa y respaldo del corte. Restan la validación real de proveedores, el ejercicio de reversión y la aceptación institucional. [Evidencia del corte](../../deployment/postgresql-migration.md)

P12 es una unidad de ejecución adicional que reúne dependencias ya ponderadas en el roadmap. No cambia la definición de 56 criterios/279 hitos ni otorga doble crédito. El porcentaje de ejecución P12 se mostrará como auxiliar, fuera del denominador general, hasta una revisión humana explícita del alcance.

## Insumos que se completarán

- Servidor Linux, recursos, almacenamiento, DNS y URL pública HTTPS.
- Instancia SQL Server 2019, confianza TLS, base institucional completa y mapeos académicos revisados. HORARIOSSIIE es un fragmento, no prueba de integración completa DBSIIE.
- Administradores institucionales, roles, MFA, custodia y rotación de secretos, retención y autoridad operativa.
- Aplicaciones Meta/TikTok y cuentas de prueba, URLs de callback/webhooks generadas por la aplicación, permisos y verificaciones de proveedor. Las credenciales se entregan por un mecanismo privado, no en documentos ni chat.
- Ventana de puesta en servicio, respaldo y restauración del destino, reversión y autorización humana del alcance externo.

## Dependencias que debe cerrar

P4/P7: catálogo y recepción/entrega externas, OAuth y canales reales. P8/P9: aceptación integrada dependiente de esos canales. P10.close.m4: cierre previo P8/P9. P11.3.m2/m4/m5 y P11.close.m1/m4: despliegue, aceptación y cierre institucional. El inventario final enlazará cada hito pendiente a su evidencia sin reinterpretar su texto.

## Recorrido previsto

1. Revisar infraestructura, dominio, certificados, SQL y autoridad; preparar manifiesto concreto.
2. Crear destino propio, restaurar y verificar catálogo/mapeos/permisos antes de activar consumidores.
3. Configurar proxy HTTPS, cookies seguras, orígenes y callbacks exactos; comprobar accesos y aislamiento.
4. Ensayar OAuth, webhooks, plantillas y recibos reales con alcance de prueba explícito; revisar incertidumbre y presupuestos.
5. Restaurar una copia y comprobar archivos, secretos y pausas; ensayar reversión.
6. Entregar evidencias y obtener aceptación institucional de la puesta en servicio.

La aplicación pública está disponible en [RinovaPlus](https://app.rinovaplus.com). Coolify enruta al frontend y al backend desplegados en Oracle.
