# P18 · Seguridad y ciberseguridad

Plan solicitado el 18 de noviembre de 2026. **0/8 unidades aceptadas; ejecución de esta fase 0%.** Existen controles previos de identidad, roles, sesiones, 2FA, CSRF y consultas; esta cifra no los declara ausentes ni auditados integralmente. Se inventariarán y probarán con evidencia específica. No añade peso al denominador original ni reemplaza arreglos críticos de P11. P15 es correos/notificaciones, P16 SIIE y P17 TikTok; no se renumeran.

## P18.1 · Inventario y amenazas

Inventariar rutas, datos, actores, proveedores, secretos y superficies públicas. Clasificar protecciones existentes, vacíos y riesgos con alcance de prueba autorizado; separar auditoría técnica de certificación.

## P18.2 · Tokens, sesiones y secretos

Validar expiración, revocación, rotación, fijación de sesión, cookies Secure/HttpOnly/SameSite, CSRF, OAuth state/PKCE según flujo, tokens de un uso, firmas de webhooks, cifrado/custodia de claves y ausencia de secretos en URLs/logs/builds.

## P18.3 · Rate limit y abuso por IP/cuenta

Límites por IP confiable del proxy, cuenta, sesión y acción; ventanas, espera progresiva y recuperación. Probar spoofing de X-Forwarded-For, NAT, concurrencia, reinicios, password spraying, enumeración y límites de carga; evitar bloquear al equipo por el tráfico normal.

## P18.4 · 2FA y recuperación

Activar 2FA con confirmación del factor, exigir verificación reciente al desactivar/cambiar, códigos de recuperación de un solo uso, revocación y auditoría. Probar reloj/reuso/intentos y pérdida del factor con cuentas de ensayo; conservar acceso de emergencia del propietario. Ningún factor se desactiva automáticamente para ensayar.

## P18.5 · CAPTCHA y fricción adaptativa

Elegir proveedor y condiciones de riesgo; validación en servidor, expiración, reuso, fallos, privacidad y alternativa accesible. Aplicar donde aporte a login/recuperación sin penalizar al usuario legítimo; no sustituye rate limit ni autorización.

## P18.6 · Inyecciones y entradas no confiables

Revisar parámetros SQL e identificadores de lista cerrada, consultas dinámicas, roles mínimos y errores. Probar XSS/HTML de plantillas, SSRF/URLs de medios y crawl, rutas/adjuntos, inyección de cabeceras y comandos. Revisar aislamiento de prompts/herramientas IA y fuentes RAG. Sin ataques destructivos a datos reales.

## P18.7 · Infraestructura y monitoreo

HTTPS/TLS, dominios/cabeceras, redes y puertos privados, permisos de base/roles/archivos, dependencias/imágenes y secretos, trazas/auditoría, alertas P15 y respaldo cifrado/custodiado. Reportar hallazgos con severidad y verificación de corrección.

## P18.8 · Aceptación, regresión y respuesta

Matriz por control/rol/ruta con evidencias, pruebas de abuso en entorno autorizado, corrección y repetición, riesgos aceptados explícitos, runbooks de incidente/rotación/revocación y plan periódico. No declarar ausencia de vulnerabilidades por una suite verde.

## Criterio de cierre

Cada control tendrá estado implementado/probado/pendiente/no aplicable con razón, evidencia reproducible y revisión de riesgo residual. Un nombre de herramienta, CAPTCHA o firewall no acredita seguridad por sí mismo. Separar pruebas controladas de evidencia real, y no ejecutar fuerza bruta, inyección destructiva ni escaneo de terceros en producción. Antes de una prueba que cambie acceso, credenciales o factores, preparar reversión y obtener la autorización correspondiente.

## Referencias técnicas

El plan toma como guía las hojas de [autenticación](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html), [autenticación multifactor](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html) y [prevención de inyección SQL](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html) de OWASP, consultadas el 18 de noviembre de 2026. Su uso no equivale a certificación ni a una auditoría externa.
