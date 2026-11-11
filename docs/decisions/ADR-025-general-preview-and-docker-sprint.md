# ADR-025 · Preview C13 independiente y cierre del sprint P1.4

Estado: aceptada para ensayo local, 2026-10-25.

El propietario pidió reunir los avances en un preview general y alcanzar P1 al100%. Al confirmar que HORARIOSSIIE sigue siendo un fragmento, autorizó cerrar el sprint más cercano cuando falte información y continuar con P2. Se conserva el criterio canónico de cierre SQL2019 y se acepta únicamente P1.4 con evidencia propia: P1 queda4/5,80%.

La solución usa una restauración de C12, login/perfil/ticket propios, API/entrada React/build nuevos y puerto loopback4176. No se redirigen C5/C9 ni se modifican sus fuentes. El workspace hereda las operaciones foundation probadas y reemplaza sólo la transacción por el guard C13. Canales se proyecta en lectura segura. La navegación de productos pendientes muestra su aceptación pendiente y no monta esos productos.

Una imagen autónoma de fuentes oficiales separa ejecución de HMR/desarrollo. Perfiles/CA quedan fuera de la imagen; los volúmenes IA/media y los permisos son exclusivos de esta composición. La recuperación se prueba con operaciones SQL durables y un efecto local idempotente, sin reutilizar workers de proveedores ni afirmar entrega externa.

El cierre P1.close permanece pendiente de motor15 real, paquete/guards/conflictos/reintentos y reversión probados en una copia SQL2019 restaurable. Renombrar una base, cambiar compatibilidad160→150 o arrancar un contenedor vacío no acreditan ese cierre. Los mapeos académicos se preparan como datos revisables sin activación automática; nombres, columnas, claves y relaciones se validarán al confirmarse.

La reversión conserva fuentes, perfiles, releases, imagen anterior, respaldos y operaciones. No se borran filas ni se cambian guardas históricas. P2 y P11 mantienen sus alcances propios; el nuevo control de propietario local no sustituye identidad institucional.

[Informe y evidencia C13](../adaptation/sql/SQL_C13_REVIEW.md) · [Enlaces académicos](../adaptation/sql/SQL_C13_BINDINGS.md).
