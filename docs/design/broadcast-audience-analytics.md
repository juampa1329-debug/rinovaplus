# Campañas: destinatarios y resultados

Ampliación solicitada el 17 de noviembre de 2026. Conserva cola, permisos, consentimiento y aprobación Meta existentes. Sin nuevas tablas ni lectura SIIE.

Diseño: paleta institucional #12343B, #C4F04D, #F5F7F2, #52666B y blanco, mediante los tokens de tema existentes; tipografía Manrope/Source Sans de la aplicación. Formulario alineado a la izquierda, filtros agrupados y desplegables, selección múltiple con casillas. El informe destaca el recorrido real de entrega con cifras y barras horizontales rotuladas, más una tabla accesible. No usa medidores con metas inventadas, colores como única explicación ni una librería adicional de gráficos.

Revisión contra el encargo: se mantiene la identidad CBN y se reduce el peso visual de tarjetas repetidas; el único énfasis es el alcance de la campaña. El selector de personas consulta sólo la cuenta elegida, con búsqueda y paginación. Los grupos son etiquetas del CRM; los estados se administran en Configurar CRM y la ficha asigna el estado a la persona. Estudiante activo/Aspirante son tipos declarados, no una matrícula verificada.

Filtros combinados por intersección; alternativas del mismo grupo por unión. Etiquetas admiten Todas/Cualquiera. Edad, género y ubicación ampliada requieren mapear campos CRM activos; edad exige una fecha válida. No se deducen del nombre, foto ni número. Los valores ausentes quedan Sin dato. Al preparar se conserva un perfil agregado en el snapshot existente, sin copiar la fecha de nacimiento. Las campañas históricas sin ese snapshot no se reinterpretan con los datos de hoy.

Gráficos bajo demanda, máximo 5.000 destinatarios sin truncamiento, usando los filtros del informe y fechas observadas. Leído requiere un recibo real; no hay evento separado de apertura. Exportación y lista permiten identificar destinatarios y fechas. La creación/gestión de plantillas se integra en el editor de campaña sin formularios anidados y conserva su borrador. Guardar no activa envíos; programación usa fecha local y zona IANA explícita.

Interaction Design guía la entrada de 260 ms, crecimiento de barras de 420 ms con escala (sin animar ancho), retraso de 25–75 ms y skeleton pulsante durante la consulta. Todo movimiento se limita a `prefers-reduced-motion: no-preference`. No se añade una dependencia de animación para estas transiciones.

Validación local: 134 pruebas backend y 16 frontend; TypeScript, ESLint de componentes/pruebas, Ruff F y build aprobados. Se corrigieron dos selectores ambiguos del arnés y una sincronización de input que lint detectó; no se debilitaron validaciones. Build conserva el aviso previo de bundle >500 kB. No se crearon contenedores ni se ejecutaron migraciones. Pendiente registrar despliegue y prueba visual publicada.
