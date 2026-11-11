# ADR-006 — Persistencia local de Clientes e Inbox en DBSIIE

**Fecha:** 2026-10-15, America/Bogota. **Estado: ACEPTADO y APLICADO en DBSIIE local el 2026-10-15.** El propietario autorizó también la auditoría automática existente. Cuatro tablas vacías, repetición no-op, ocho auditorías automáticas y preservación del resto del core comprobadas. API/UI pendientes. [Evidencia](../reports/crm-local-migration.md). Complementa [ADR-001](ADR-001-skeleton-architecture.md) y la [puerta de diseño de datos](../architecture.md#sql-server-integración-protegida).

Se autoriza crear únicamente el esquema `crm` y cuatro tablas en la **copia local `DBSIIE` de `SQLEXPRESS`**. Contactos, conversaciones y mensajes tendrán identidad propia, sin modificar ni referenciar mediante FK tablas core. SQL Server sigue siendo la fuente transaccional; no se añade otro motor, servicio, framework o dependencia.

## Evidencia y autorización vigente

El diagnóstico autorizado comprobó login `sa`, TLS validado y lecturas desde Windows y Docker: 32 períodos, 12 escuelas, 2 modalidades y 228 programas. Ambos clientes verificaron INSERT y ROLLBACK de una tabla temporal, sin transacción restante. Docker rechazó el certificado sin confianza adicional y funcionó con PEM público, `SSL_CERT_FILE` y `HostnameInCertificate=localhost`. Esa confianza pertenece al harness; **todavía no está integrada en el runtime**. No se encontraron esquemas `CRM`/`CRM_*` ni objetos `CRM_*`; el chequeo previo al DDL volverá a detectar colisiones sin distinguir mayúsculas. Evidencia local saneada: `.local/sql-real-20261015/result.md` y JSON asociados.

El propietario aceptó expresamente este contrato, la creación local de sus cuatro tablas, la recuperación previa y la continuación de Clientes/Inbox. El backup COPY_ONLY/CHECKSUM y su restauración real pasaron. El propietario autorizó posteriormente los INSERT automáticos del trigger DDL existente; la aplicación local pasó y conservó el trigger activo. No autoriza escritura core, publicación, Oracle, acceso compartido ni canales. No sustituye autenticación/RBAC ni convierte `sa` en identidad productiva.

## Primer entregable y contrato

| Objeto propuesto | Responsabilidad y límites |
|---|---|
| `crm.Contact` | UUID propio; conserva nombre, teléfono, ciudad, programa, jornada, etapa, etiquetas, notas, tipo, intereses y valores personalizados actuales. El teléfono no es único. Solo `CustomValues` usa JSON, como objeto de campos dinámicos tipados/limitados por servidor. |
| `crm.Conversation` | UUID separado del contacto, un hilo local por contacto en este corte. Estado, prioridad, responsable como etiqueta local, control humano/IA y no leído. No representa una cuenta Meta ni una identidad autenticada. |
| `crm.Message` | UUID propio, conversación, texto, dirección y orden de inserción. Agregar un mensaje local no significa envío ni entrega; el primer endpoint solo agrega texto saliente confirmado por el operador. |
| `crm.Operation` | UUID de operación único, hash SHA-256 del payload canónico, revisión global, acción, referencias y fecha/actor local. Registro compartido de idempotencia y auditoría de operaciones confirmadas, sin duplicar texto de mensajes ni fichas. |

`ProgramId` es nullable y, cuando se selecciona, se valida mediante el catálogo de programas; `Program` conserva la etiqueta. No es oferta, matrícula ni jornada. `Schedule` conserva texto informado, sin presentarlo como jornada académica validada. Los cuatro catálogos siguen siendo lecturas SIIE. No se importan fixtures ni se unen contactos a `ACAspirante`, `ACAspirantePorOferta` o `GEEstudiante` por teléfono/documento.

Cada confirmación envía `operationId`, UUID de entidad estable y `expectedRevision` como cadena decimal. La revisión inicial es `"0"`; las confirmaciones devuelven revisión y recursos actuales. Una transacción pyodbc con autocommit desactivado y `XACT_ABORT ON` obtiene `sp_getapplock` exclusivo, recurso `crm.local.commit`, propietario Transaction, timeout 5000 ms. Primero busca `operationId`: mismo hash devuelve los mismos IDs sin repetir la escritura, con estado/revisión actuales; hash distinto devuelve 409. Después compara `expectedRevision` con `COALESCE(MAX(Revision),0)`; diferencia devuelve 409 sin efectos.

El payload canónico incluye acción, IDs y valores normalizados; excluye `expectedRevision`. La misma intención conserva `operationId` ante timeout/reintento; cambiar datos crea otra intención. Crear contacto crea también su conversación en la misma transacción. Editar contacto, cambiar estado/control del hilo o agregar mensaje actualizan sus recursos y añaden `Operation` antes de COMMIT. Cualquier error revierte todo. Una respuesta incierta se resuelve reintentando la misma operación, nunca inventando otro ID. No se borran ni podan operaciones en este corte.

Las lecturas de recursos y revisión comparten una transacción con el mismo applock en modo Shared; no mezclan snapshots. La revisión global puede causar conflictos entre fichas distintas: se acepta para esta copia local de un proceso y bajo volumen; no se añade concurrencia por entidad hasta que una necesidad medida lo justifique. Las comprobaciones de relación y estado se hacen de nuevo dentro de la transacción. Hilo cerrado no admite mensajes; control humano evita que una sugerencia agregue texto sin confirmación. Las rutas usan consultas fijas parametrizadas, límites y errores saneados; no reciben SQL libre.

## Integración posterior a la aceptación

- Reutilizar pyodbc y los contratos de `clientsApi`/`useClients`, sustituyendo el store de `install_local_clients` por operaciones SQL en un módulo responsable, sin repositorio genérico ni ORM. La revisión conserva su forma string; IDs dejan de exigir `demo-*`. Las rutas SQL quedan separadas del contrato sintético mientras coexistan modos.
- Proponer `CRM_APP_MODE=local_sql_copy` como activación explícita futura, limitada a loopback y al destino comprobado. Mantener `local_demo` y `local_readonly_catalog`; no relajar `verify_principal` ni reutilizar su rechazo de SA como permiso de escritura. El adaptador del nuevo modo validará DB/instancia y la identidad del destino local comprobado antes de operar. Credenciales solo en entorno/archivo privado, nunca en frontend.
- Incorporar confianza de certificado público al runtime antes de activarlo: `Encrypt=Yes`, `TrustServerCertificate=No`, nombre esperado validado y cadena confiable. El diagnóstico aislado no acredita todavía esa integración. No montar claves privadas ni ampliar confianza global. `.env` y preview actuales no cambian por este ADR.
- El nuevo modo comienza con colecciones vacías: sin `seedClients`, `seedThreads`, valores de programa/jornada ficticios ni fallback tras error. Eliminar el reset destructivo de esa superficie. Conservar V6, navegación, filtros, confirmaciones y borradores en `WorkspaceSessionProvider`/`InboxSessionProvider`; los borradores no van a SQL. Un 409 refresca confirmados y conserva el borrador para revisión humana.
- Estado, prioridad, control y mensajes locales son el alcance Inbox persistente. Tareas, comentarios sociales, formulario y revisión académica no se migran en este corte ni se anuncian conectados; sus acciones ajenas al alcance quedan identificadas y deshabilitadas en el modo SQL. El modo local existente conserva sus flujos. No Meta, outbox, workers, envíos, RBAC nuevo o migración de datos demo.

## Migración 001 aceptada y aplicada localmente

**Aplicada mediante ejecución explícita; nunca al arranque del producto.** La fuente explícita está en [001_local_crm.sql](../../backend/migrations/001_local_crm.sql); conserva el contrato SQL mostrado aquí y se ensayó en la restauración cambiando únicamente el guard del nombre de base en memoria. El nombre de base/instancia no demuestra por sí solo que sea la copia autorizada: el preflight debe contrastar además servidor/listener local y el inventario aprobado. Debe existir SQL Server con compatibilidad 130 o superior. No hay `USE`, `GO`, runner ni aplicación automática al arrancar. La transacción crea todo o nada; un esquema ajeno o alterado provoca rechazo, no reparación.

```sql
SET XACT_ABORT ON;
IF @@TRANCOUNT <> 0 THROW 51000, 'Open transaction refused.', 1;
IF DB_NAME() COLLATE Latin1_General_100_BIN2 <> N'DBSIIE'
   OR ISNULL(CONVERT(nvarchar(128), SERVERPROPERTY('InstanceName')), N'') COLLATE Latin1_General_100_BIN2 <> N'SQLEXPRESS'
   THROW 51001, 'Unexpected database or instance.', 1;
IF (SELECT compatibility_level FROM sys.databases WHERE database_id = DB_ID()) < 130
   THROW 51002, 'SQL compatibility 130 or later required.', 1;
BEGIN TRY
    BEGIN TRANSACTION;
    DECLARE @lock int, @created bit = 0, @schema int;
    EXEC @lock = sys.sp_getapplock @Resource = N'crm.local.commit',
        @LockMode = 'Exclusive', @LockOwner = 'Transaction', @LockTimeout = 5000;
    IF @lock < 0 THROW 51003, 'Migration lock unavailable.', 1;
    IF EXISTS (SELECT 1 FROM sys.schemas WHERE LOWER(name) = N'crm'
               AND name COLLATE Latin1_General_100_BIN2 <> N'crm')
        THROW 51004, 'Schema name collision.', 1;
    IF SCHEMA_ID(N'crm') IS NULL
    BEGIN
        EXEC(N'CREATE SCHEMA crm AUTHORIZATION dbo;');
        SET @created = 1;
        CREATE TABLE crm.Contact (
            ContactId uniqueidentifier NOT NULL CONSTRAINT PK_Contact PRIMARY KEY,
            Name nvarchar(100) NOT NULL, Phone nvarchar(40) NOT NULL,
            City nvarchar(100) NOT NULL, ProgramId int NULL,
            Program nvarchar(200) NOT NULL, Schedule nvarchar(100) NOT NULL,
            Stage nvarchar(60) NOT NULL, Tags nvarchar(1000) NOT NULL,
            Notes nvarchar(1000) NOT NULL, Type nvarchar(100) NOT NULL,
            Interests nvarchar(300) NOT NULL, CustomValues nvarchar(max) NOT NULL,
            CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_Contact_CreatedAt DEFAULT SYSUTCDATETIME(),
            UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_Contact_UpdatedAt DEFAULT SYSUTCDATETIME(),
            CONSTRAINT CK_Contact_Identity CHECK (LEN(LTRIM(RTRIM(Name))) > 0 OR LEN(LTRIM(RTRIM(Phone))) > 0),
            CONSTRAINT CK_Contact_Stage CHECK (LEN(LTRIM(RTRIM(Stage))) > 0),
            CONSTRAINT CK_Contact_Custom CHECK (ISJSON(CustomValues) = 1 AND LEFT(LTRIM(CustomValues), 1) = N'{')
        );
        CREATE TABLE crm.Conversation (
            ConversationId uniqueidentifier NOT NULL CONSTRAINT PK_Conversation PRIMARY KEY,
            ContactId uniqueidentifier NOT NULL CONSTRAINT UQ_Conversation_Contact UNIQUE,
            State varchar(12) NOT NULL, Priority varchar(8) NOT NULL,
            Assignee nvarchar(100) NULL, ControlMode varchar(5) NOT NULL, Unread bit NOT NULL,
            CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_Conversation_CreatedAt DEFAULT SYSUTCDATETIME(),
            UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_Conversation_UpdatedAt DEFAULT SYSUTCDATETIME(),
            CONSTRAINT FK_Conversation_Contact FOREIGN KEY (ContactId) REFERENCES crm.Contact(ContactId),
            CONSTRAINT CK_Conversation_State CHECK (State IN ('open', 'waiting', 'closed')),
            CONSTRAINT CK_Conversation_Priority CHECK (Priority IN ('low', 'normal', 'high', 'urgent')),
            CONSTRAINT CK_Conversation_Control CHECK (ControlMode IN ('human', 'ai'))
        );
        CREATE TABLE crm.Message (
            MessageId uniqueidentifier NOT NULL CONSTRAINT PK_Message PRIMARY KEY,
            ConversationId uniqueidentifier NOT NULL,
            Sequence bigint IDENTITY(1,1) NOT NULL, Body nvarchar(4000) NOT NULL,
            Direction varchar(8) NOT NULL,
            CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_Message_CreatedAt DEFAULT SYSUTCDATETIME(),
            CONSTRAINT FK_Message_Conversation FOREIGN KEY (ConversationId) REFERENCES crm.Conversation(ConversationId),
            CONSTRAINT CK_Message_Body CHECK (LEN(LTRIM(RTRIM(Body))) > 0),
            CONSTRAINT CK_Message_Direction CHECK (Direction IN ('incoming', 'outgoing'))
        );
        CREATE UNIQUE INDEX IX_Message_Conversation_Sequence ON crm.Message(ConversationId, Sequence);
        CREATE TABLE crm.Operation (
            OperationId uniqueidentifier NOT NULL CONSTRAINT PK_Operation PRIMARY KEY NONCLUSTERED,
            Revision bigint IDENTITY(1,1) NOT NULL CONSTRAINT UQ_Operation_Revision UNIQUE CLUSTERED,
            Action varchar(24) NOT NULL, PayloadHash binary(32) NOT NULL,
            ContactId uniqueidentifier NOT NULL, ConversationId uniqueidentifier NOT NULL,
            MessageId uniqueidentifier NULL, Actor varchar(32) NOT NULL,
            CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_Operation_CreatedAt DEFAULT SYSUTCDATETIME(),
            CONSTRAINT FK_Operation_Contact FOREIGN KEY (ContactId) REFERENCES crm.Contact(ContactId),
            CONSTRAINT FK_Operation_Conversation FOREIGN KEY (ConversationId) REFERENCES crm.Conversation(ConversationId),
            CONSTRAINT FK_Operation_Message FOREIGN KEY (MessageId) REFERENCES crm.Message(MessageId),
            CONSTRAINT CK_Operation_Action CHECK (Action IN ('create_contact', 'edit_contact', 'update_conversation', 'add_message')),
            CONSTRAINT CK_Operation_Message CHECK ((Action = 'add_message' AND MessageId IS NOT NULL) OR (Action <> 'add_message' AND MessageId IS NULL)),
            CONSTRAINT CK_Operation_Actor CHECK (Actor = 'local-operator')
        );
    END;
    SET @schema = SCHEMA_ID(N'crm');
    DECLARE @version nvarchar(128), @stored binary(32), @manifest nvarchar(max), @hash binary(32);
    SELECT @version = CONVERT(nvarchar(128), value) FROM sys.extended_properties
        WHERE class = 3 AND major_id = @schema AND name = N'crm.contract';
    SELECT @stored = CONVERT(binary(32), value) FROM sys.extended_properties
        WHERE class = 3 AND major_id = @schema AND name = N'crm.shape';
    IF @created = 0 AND (@version IS NULL OR @version <> N'ADR-006-v1' OR @stored IS NULL)
        THROW 51005, 'Unrecognized existing schema.', 1;
    SET @manifest = (
        SELECT USER_NAME(s.principal_id) AS schema_owner,
          (SELECT o.name, o.type, OBJECT_DEFINITION(o.object_id) AS definition,
                  cc.is_disabled, cc.is_not_trusted
           FROM sys.objects o LEFT JOIN sys.check_constraints cc ON cc.object_id = o.object_id
           WHERE o.schema_id = @schema ORDER BY o.name FOR JSON PATH) AS objects,
          (SELECT OBJECT_NAME(c.object_id) AS object_name, c.name, c.column_id,
                  TYPE_NAME(c.user_type_id) AS type_name, c.max_length, c.precision, c.scale,
                  c.is_nullable, c.is_identity, c.collation_name,
                  CONVERT(nvarchar(128), ic.seed_value) AS identity_seed,
                  CONVERT(nvarchar(128), ic.increment_value) AS identity_increment
           FROM sys.columns c JOIN sys.objects o ON o.object_id = c.object_id
           LEFT JOIN sys.identity_columns ic ON ic.object_id = c.object_id AND ic.column_id = c.column_id
           WHERE o.schema_id = @schema ORDER BY o.name, c.column_id FOR JSON PATH) AS columns,
          (SELECT o.name AS object_name, i.name, i.type, i.is_unique, i.is_primary_key,
                  i.is_unique_constraint, i.is_disabled, i.filter_definition,
                  c.name AS column_name, ic.key_ordinal, ic.is_descending_key, ic.is_included_column
           FROM sys.indexes i JOIN sys.objects o ON o.object_id = i.object_id
           LEFT JOIN sys.index_columns ic ON ic.object_id = i.object_id AND ic.index_id = i.index_id
           LEFT JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id = ic.column_id
           WHERE o.schema_id = @schema ORDER BY o.name, i.name, ic.index_column_id FOR JSON PATH) AS indexes,
          (SELECT fk.name, OBJECT_NAME(fk.parent_object_id) AS source_table,
                  COL_NAME(fc.parent_object_id, fc.parent_column_id) AS source_column,
                  OBJECT_SCHEMA_NAME(fc.referenced_object_id) AS target_schema,
                  OBJECT_NAME(fc.referenced_object_id) AS target_table,
                  COL_NAME(fc.referenced_object_id, fc.referenced_column_id) AS target_column,
                  fk.delete_referential_action, fk.update_referential_action, fk.is_disabled, fk.is_not_trusted
           FROM sys.foreign_keys fk JOIN sys.foreign_key_columns fc ON fc.constraint_object_id = fk.object_id
           WHERE fk.schema_id = @schema ORDER BY fk.name, fc.constraint_column_id FOR JSON PATH) AS relations
        FROM sys.schemas s WHERE s.schema_id = @schema FOR JSON PATH, WITHOUT_ARRAY_WRAPPER
    );
    SET @hash = HASHBYTES('SHA2_256', @manifest);
    IF @created = 0 AND @stored <> @hash THROW 51006, 'Existing schema shape differs.', 1;
    IF @created = 1
    BEGIN
        EXEC sys.sp_addextendedproperty @name=N'crm.contract', @value=N'ADR-006-v1',
            @level0type=N'SCHEMA', @level0name=N'crm';
        EXEC sys.sp_addextendedproperty @name=N'crm.shape', @value=@hash,
            @level0type=N'SCHEMA', @level0name=N'crm';
    END;
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
```

La huella registra únicamente forma de objetos/columnas/índices/FK/checks, no filas ni valores de identidad actuales. Repetir el mismo contrato sobre su esquema intacto es no-op; cualquier diferencia detectada aborta. No es un framework ni una firma contra un administrador malicioso: una versión distinta o reparación requerirá otra migración revisada. Defaults y constraints tienen nombres fijos; las FK son internas y no tienen cascadas. El `sa` de la copia puede alterar cualquier objeto, por lo que el aislamiento depende además del alcance aprobado, consultas fijas y verificación de efectos.

## Reversión y aceptación antes de activar

El **down de este corte no elimina objetos ni filas**: desactivar el modo SQL, detener sus escritores y volver al modo local conserva toda la información durable. No ejecutar DELETE, TRUNCATE, DROP ni restaurar la base sobre cambios posteriores. Si se solicita retirar físicamente el esquema, será una operación aparte: respaldo/restauración verificados, aplicación detenida, identidad del destino comprobada y rechazo si cualquiera de las cuatro tablas contiene filas o hay dependencias/objetos no reconocidos. No se pierde historial para obtener un rollback aparente.

Antes de aplicar: aceptar este ADR y creación local; obtener respaldo completo de la copia, probar restauración en destino separado y conservar evidencia de recuperabilidad; capturar metadata/huella de objetos core; comprobar ausencia de colisiones, compatibilidad, destino y transacciones abiertas. Si la prueba de restauración no está disponible, no aplicar todavía el DDL. El respaldo no se usa como permiso para borrar datos.

Después de aceptar: ensayar la migración y su repetición, rechazo por forma alterada y rollback ante fallo parcial; comprobar que el core permanece intacto y las tablas empiezan vacías. Luego implementar API/UI del corte y verificar recarga/reinicio durable, relaciones UUID, operación repetida, hash diferente, conflictos concurrentes 409, pérdida de respuesta tras commit y fallos sin escrituras parciales. Verificar borradores, estados vacíos/error, ausencia de reset destructivo y cero llamadas a proveedores. El control TLS negativo y positivo debe repetirse en el runtime real del producto antes de declararlo conectado.

**Pendientes explícitos:** implementación y pruebas API/UI/TLS. Contrato, cuatro tablas locales, recuperación y excepción de INSERT automáticos de auditoría están autorizados y comprobados. No se autorizan cambios de negocio core, deshabilitar el trigger, borrar auditorías ni publicar.
