# P12: puesta online institucional

Fecha: 2026-10-28. Solicitada por el usuario al confirmar que aún no dispone de URL. Estado: pendiente, sin ejecución externa autorizada por este documento.

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

La aplicación local acumulada sigue en el puerto 4178. La preparación local no acredita que el producto esté disponible en Internet.
