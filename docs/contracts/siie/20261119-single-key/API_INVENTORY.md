# Cobertura de clave única: 21 operaciones

Inventario del 19 de noviembre de 2026. Las 21 operaciones siguientes usan la misma clave original y la validación central ApiSecurity. Las lecturas, cuerpos y reglas de negocio no cambian. OPTIONS se gestiona como preflight y no se cuenta como otra operación de negocio.

| Familia | Método y ruta relativa a la raíz SIIEWEBPLUS |
|---|---|
| CRM | GET /Api/CRM/v1/Periodos.aspx |
| CRM | GET /Api/CRM/v1/EstadosSeguimiento.aspx |
| CRM | GET /Api/CRM/v1/FiltrosAdmisiones.aspx |
| CRM | GET /Api/CRM/v1/Aspirantes.aspx |
| CRM | GET /Api/CRM/v1/Aspirante.aspx |
| CRM | GET /Api/CRM/v1/HistorialSeguimiento.aspx |
| CRM | POST /Api/CRM/v1/Seguimientos.aspx |
| CRM | PUT /Api/CRM/v1/Seguimientos.aspx |
| CRM | GET /Api/CRM/v1/Estudiantes.aspx |
| CRM | GET /Api/CRM/v1/Estudiante.aspx |
| CRM | GET /Api/CRM/v1/FiltrosEstudiantes.aspx |
| CRM Commercial | GET /Api/CRM/v1/Commercial/Programs.aspx |
| CRM Commercial | GET /Api/CRM/v1/Commercial/ProgramOffers.aspx |
| CRM Commercial | GET /Api/CRM/v1/Commercial/Offer.aspx |
| Preinscripciones | GET /Api/Preinscripciones/v1/Escuelas.aspx |
| Preinscripciones | GET /Api/Preinscripciones/v1/TiposDocumento.aspx |
| Preinscripciones | GET /Api/Preinscripciones/v1/ProgramasAcademicos.aspx |
| Preinscripciones | POST /Api/Preinscripciones/v1/RecibirPreinscripcion.aspx |
| Moodle | GET /Api/Moodle/v1/Programas.aspx |
| Moodle | GET /Api/Moodle/v1/Asignaturas.aspx |
| Moodle | GET /Api/Moodle/v1/EstudiantesMatriculados.aspx |

Las rutas antiguas conservan FriendlyURLs: GET .aspx puede responder 301 hacia su equivalente sin extensión. Para POST RecibirPreinscripcion, la colección usa directamente /Api/Preinscripciones/v1/RecibirPreinscripcion y evita convertir POST en GET por una redirección. RouteConfig no se modifica.

## Enlace central comprobado en código

- App_Code/CrmAdmissionsApi.cs:58: Autorizar, 120 lecturas/minuto y 30 escrituras/minuto.
- App_Code/CrmStudentsApi.cs:53: Autorizar, 120 lecturas/minuto.
- App_Code/CrmCommercialApi.cs:49: AutorizarCatalogoCrm, 60 lecturas/minuto; el wrapper ahora delega a Autorizar.
- Api/Preinscripciones/v1/Escuelas.aspx.cs:26, TiposDocumento.aspx.cs:26 y ProgramasAcademicos.aspx.cs:26: Autorizar, 120 lecturas/minuto.
- Api/Preinscripciones/v1/RecibirPreinscripcion.aspx.cs:35: Autorizar, 30 escrituras/minuto. DatosCompletos se ejecuta antes de GuardarAspirante; cuerpo {} se rechaza con HTTP 200 y status:error, conservando el contrato original.
- Api/Moodle/v1/Programas.aspx.cs:26, Asignaturas.aspx.cs:26 y EstudiantesMatriculados.aspx.cs:26: Autorizar, 120 lecturas/minuto. Parámetros ausentes se rechazan después de autenticar, antes de consultar personas.
- App_Code/ApiSecurity.cs:71: entrada compartida. API_Key contiene SHA-256; API_CRM es alias de la misma huella. No existe respaldo de claves por entorno o DPAPI.
- App_Code/Startup.Auth.cs:66: exención OWIN ampliada únicamente a /Api/Moodle/ para conservar 401 JSON. No omite ApiSecurity ni cambia el login de páginas del sitio.

## Límites del inventario

Los catálogos públicos /Aspirantes/ProgramasAcademicos.aspx y /Aspirantes/TiposDocumento.aspx no son las APIs protegidas /Api/Preinscripciones/v1/. Usan el helper de respuesta/catálogo, pero no invocan Autorizar. Son parte del formulario público y no se modifican. Tampoco se cambian formularios, webhooks, pagos, campañas públicas ni FormsAuth del sitio.

No se crean rutas nuevas ni se cambian SQL/negocio. La integración consumidora externa no se refactoriza: si conserva dos variables, puede recibir la misma clave original en ambas. Publicación remota pendiente.
