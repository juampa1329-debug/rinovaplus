# Catálogo de declaraciones SQL

Columnas y restricciones de CREATE TABLE, no esquema real ni esquema final reconstruido. Índices UNIQUE/PK declarados como restricciones figuran en la definición de columna o en las restricciones de tabla; el recuento de CREATE INDEX sólo cubre sentencias explícitas. Las definiciones retienen tipos, CHECK, DEFAULT, collation, IDENTITY y claves para revisar el contrato.

## crm.Contact

[Declaración 001:22](../../../backend/migrations/001_local_crm.sql#L22).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| ContactId | uniqueidentifier | No | ContactId uniqueidentifier NOT NULL CONSTRAINT PK_Contact PRIMARY KEY | 23 |
| Name | nvarchar(100) | No | Name nvarchar(100) NOT NULL | 24 |
| Phone | nvarchar(40) | No | Phone nvarchar(40) NOT NULL | 24 |
| City | nvarchar(100) | No | City nvarchar(100) NOT NULL | 25 |
| ProgramId | int | Sí | ProgramId int NULL | 25 |
| Program | nvarchar(200) | No | Program nvarchar(200) NOT NULL | 26 |
| Schedule | nvarchar(100) | No | Schedule nvarchar(100) NOT NULL | 26 |
| Stage | nvarchar(60) | No | Stage nvarchar(60) NOT NULL | 27 |
| Tags | nvarchar(1000) | No | Tags nvarchar(1000) NOT NULL | 27 |
| Notes | nvarchar(1000) | No | Notes nvarchar(1000) NOT NULL | 28 |
| Type | nvarchar(100) | No | Type nvarchar(100) NOT NULL | 28 |
| Interests | nvarchar(300) | No | Interests nvarchar(300) NOT NULL | 29 |
| CustomValues | nvarchar(max) | No | CustomValues nvarchar(max) NOT NULL | 29 |
| CreatedAt | datetime2(7) | No | CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_Contact_CreatedAt DEFAULT SYSUTCDATETIME() | 30 |
| UpdatedAt | datetime2(7) | No | UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_Contact_UpdatedAt DEFAULT SYSUTCDATETIME() | 31 |

**Restricciones de tabla:**

- Línea 32: `CONSTRAINT CK_Contact_Identity CHECK (LEN(LTRIM(RTRIM(Name))) > 0 OR LEN(LTRIM(RTRIM(Phone))) > 0)`
- Línea 33: `CONSTRAINT CK_Contact_Stage CHECK (LEN(LTRIM(RTRIM(Stage))) > 0)`
- Línea 34: `CONSTRAINT CK_Contact_Custom CHECK (ISJSON(CustomValues) = 1 AND LEFT(LTRIM(CustomValues), 1) = N'{')`

**Consumidores literales:** [backend/app/database_connections.py:56](../../../backend/app/database_connections.py#L56), [backend/app/sql_workspace.py:232](../../../backend/app/sql_workspace.py#L232), [backend/app/modules/agents/router.py:82](../../../backend/app/modules/agents/router.py#L82), [backend/app/modules/agents/runtime.py:116](../../../backend/app/modules/agents/runtime.py#L116), [backend/app/modules/campaigns/service.py:85](../../../backend/app/modules/campaigns/service.py#L85), [backend/app/modules/channels/workers.py:216](../../../backend/app/modules/channels/workers.py#L216), [backend/app/modules/inbox/application/service.py:55](../../../backend/app/modules/inbox/application/service.py#L55), [backend/app/modules/crm_configuration/application/service.py:241](../../../backend/app/modules/crm_configuration/application/service.py#L241), [backend/app/modules/conversation_analysis/api/router.py:77](../../../backend/app/modules/conversation_analysis/api/router.py#L77), [backend/app/modules/contacts/api/router.py:144](../../../backend/app/modules/contacts/api/router.py#L144), [backend/app/modules/contacts/application/merge.py:159](../../../backend/app/modules/contacts/application/merge.py#L159), [backend/app/modules/ai/api/admissions.py:145](../../../backend/app/modules/ai/api/admissions.py#L145)

## crm.Conversation

[Declaración 001:36](../../../backend/migrations/001_local_crm.sql#L36).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| ConversationId | uniqueidentifier | No | ConversationId uniqueidentifier NOT NULL CONSTRAINT PK_Conversation PRIMARY KEY | 37 |
| ContactId | uniqueidentifier | No | ContactId uniqueidentifier NOT NULL CONSTRAINT UQ_Conversation_Contact UNIQUE | 38 |
| State | varchar(12) | No | State varchar(12) NOT NULL | 39 |
| Priority | varchar(8) | No | Priority varchar(8) NOT NULL | 39 |
| Assignee | nvarchar(100) | Sí | Assignee nvarchar(100) NULL | 40 |
| ControlMode | varchar(5) | No | ControlMode varchar(5) NOT NULL | 40 |
| Unread | bit | No | Unread bit NOT NULL | 40 |
| CreatedAt | datetime2(7) | No | CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_Conversation_CreatedAt DEFAULT SYSUTCDATETIME() | 41 |
| UpdatedAt | datetime2(7) | No | UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_Conversation_UpdatedAt DEFAULT SYSUTCDATETIME() | 42 |

**Restricciones de tabla:**

- Línea 43: `CONSTRAINT FK_Conversation_Contact FOREIGN KEY (ContactId) REFERENCES crm.Contact(ContactId)`
- Línea 44: `CONSTRAINT CK_Conversation_State CHECK (State IN ('open', 'waiting', 'closed'))`
- Línea 45: `CONSTRAINT CK_Conversation_Priority CHECK (Priority IN ('low', 'normal', 'high', 'urgent'))`
- Línea 46: `CONSTRAINT CK_Conversation_Control CHECK (ControlMode IN ('human', 'ai'))`

**Claves foráneas:**

- Línea 43: `CONSTRAINT FK_Conversation_Contact FOREIGN KEY (ContactId) REFERENCES crm.Contact(ContactId)`

**Consumidores literales:** [backend/app/database_connections.py:56](../../../backend/app/database_connections.py#L56), [backend/app/sql_workspace.py:252](../../../backend/app/sql_workspace.py#L252), [backend/app/modules/agents/operations.py:43](../../../backend/app/modules/agents/operations.py#L43), [backend/app/modules/agents/router.py:82](../../../backend/app/modules/agents/router.py#L82), [backend/app/modules/agents/runtime.py:112](../../../backend/app/modules/agents/runtime.py#L112), [backend/app/modules/agents/service.py:404](../../../backend/app/modules/agents/service.py#L404), [backend/app/modules/campaigns/service.py:85](../../../backend/app/modules/campaigns/service.py#L85), [backend/app/modules/channels/workers.py:223](../../../backend/app/modules/channels/workers.py#L223), [backend/app/modules/inbox/application/media.py:163](../../../backend/app/modules/inbox/application/media.py#L163), [backend/app/modules/inbox/application/operations.py:403](../../../backend/app/modules/inbox/application/operations.py#L403), [backend/app/modules/inbox/application/service.py:55](../../../backend/app/modules/inbox/application/service.py#L55), [backend/app/modules/conversation_strategy/api/router.py:65](../../../backend/app/modules/conversation_strategy/api/router.py#L65), [backend/app/modules/conversation_events/api/router.py:25](../../../backend/app/modules/conversation_events/api/router.py#L25), [backend/app/modules/conversation_analysis/api/router.py:97](../../../backend/app/modules/conversation_analysis/api/router.py#L97), [backend/app/modules/contacts/api/router.py:118](../../../backend/app/modules/contacts/api/router.py#L118), [backend/app/modules/contacts/application/activity.py:120](../../../backend/app/modules/contacts/application/activity.py#L120), [backend/app/modules/contacts/application/merge.py:176](../../../backend/app/modules/contacts/application/merge.py#L176), [backend/app/modules/ai/api/admissions.py:145](../../../backend/app/modules/ai/api/admissions.py#L145), [backend/app/modules/ai/application/admissions.py:67](../../../backend/app/modules/ai/application/admissions.py#L67)

## crm.Message

[Declaración 001:48](../../../backend/migrations/001_local_crm.sql#L48).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| MessageId | uniqueidentifier | No | MessageId uniqueidentifier NOT NULL CONSTRAINT PK_Message PRIMARY KEY | 49 |
| ConversationId | uniqueidentifier | No | ConversationId uniqueidentifier NOT NULL | 50 |
| Sequence | bigint | No | Sequence bigint IDENTITY(1,1) NOT NULL | 51 |
| Body | nvarchar(4000) | No | Body nvarchar(4000) NOT NULL | 51 |
| Direction | varchar(8) | No | Direction varchar(8) NOT NULL | 52 |
| CreatedAt | datetime2(7) | No | CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_Message_CreatedAt DEFAULT SYSUTCDATETIME() | 53 |

**Restricciones de tabla:**

- Línea 54: `CONSTRAINT FK_Message_Conversation FOREIGN KEY (ConversationId) REFERENCES crm.Conversation(ConversationId)`
- Línea 55: `CONSTRAINT CK_Message_Body CHECK (LEN(LTRIM(RTRIM(Body))) > 0)`
- Línea 56: `CONSTRAINT CK_Message_Direction CHECK (Direction IN ('incoming', 'outgoing'))`

**Claves foráneas:**

- Línea 54: `CONSTRAINT FK_Message_Conversation FOREIGN KEY (ConversationId) REFERENCES crm.Conversation(ConversationId)`

**CREATE INDEX explícitos:**

- `IX_Message_Conversation_Sequence`: UNIQUE (ConversationId, Sequence)  · [backend/migrations/001_local_crm.sql:58](../../../backend/migrations/001_local_crm.sql#L58).

**Consumidores literales:** [backend/app/database_connections.py:56](../../../backend/app/database_connections.py#L56), [backend/app/sql_workspace.py:293](../../../backend/app/sql_workspace.py#L293), [backend/app/modules/agents/service.py:998](../../../backend/app/modules/agents/service.py#L998), [backend/app/modules/campaigns/evidence.py:29](../../../backend/app/modules/campaigns/evidence.py#L29), [backend/app/modules/campaigns/service.py:329](../../../backend/app/modules/campaigns/service.py#L329), [backend/app/modules/channels/workers.py:248](../../../backend/app/modules/channels/workers.py#L248), [backend/app/modules/inbox/application/operations.py:41](../../../backend/app/modules/inbox/application/operations.py#L41), [backend/app/modules/inbox/application/service.py:57](../../../backend/app/modules/inbox/application/service.py#L57), [backend/app/modules/inbox/application/state.py:40](../../../backend/app/modules/inbox/application/state.py#L40), [backend/app/modules/conversation_strategy/api/router.py:72](../../../backend/app/modules/conversation_strategy/api/router.py#L72), [backend/app/modules/conversation_events/api/router.py:28](../../../backend/app/modules/conversation_events/api/router.py#L28), [backend/app/modules/conversation_analysis/api/router.py:188](../../../backend/app/modules/conversation_analysis/api/router.py#L188), [backend/app/modules/contacts/application/activity.py:141](../../../backend/app/modules/contacts/application/activity.py#L141), [backend/app/modules/ai/application/admissions.py:76](../../../backend/app/modules/ai/application/admissions.py#L76)

## crm.Operation

[Declaración 001:59](../../../backend/migrations/001_local_crm.sql#L59).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| OperationId | uniqueidentifier | No | OperationId uniqueidentifier NOT NULL CONSTRAINT PK_Operation PRIMARY KEY NONCLUSTERED | 60 |
| Revision | bigint | No | Revision bigint IDENTITY(1,1) NOT NULL CONSTRAINT UQ_Operation_Revision UNIQUE CLUSTERED | 61 |
| Action | varchar(24) | No | Action varchar(24) NOT NULL | 62 |
| PayloadHash | binary(32) | No | PayloadHash binary(32) NOT NULL | 62 |
| ContactId | uniqueidentifier | No | ContactId uniqueidentifier NOT NULL | 63 |
| ConversationId | uniqueidentifier | No | ConversationId uniqueidentifier NOT NULL | 63 |
| MessageId | uniqueidentifier | Sí | MessageId uniqueidentifier NULL | 64 |
| Actor | varchar(32) | No | Actor varchar(32) NOT NULL | 64 |
| CreatedAt | datetime2(7) | No | CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_Operation_CreatedAt DEFAULT SYSUTCDATETIME() | 65 |

**Restricciones de tabla:**

- Línea 66: `CONSTRAINT FK_Operation_Contact FOREIGN KEY (ContactId) REFERENCES crm.Contact(ContactId)`
- Línea 67: `CONSTRAINT FK_Operation_Conversation FOREIGN KEY (ConversationId) REFERENCES crm.Conversation(ConversationId)`
- Línea 68: `CONSTRAINT FK_Operation_Message FOREIGN KEY (MessageId) REFERENCES crm.Message(MessageId)`
- Línea 69: `CONSTRAINT CK_Operation_Action CHECK (Action IN ('create_contact', 'edit_contact', 'update_conversation', 'add_message'))`
- Línea 70: `CONSTRAINT CK_Operation_Message CHECK ((Action = 'add_message' AND MessageId IS NOT NULL) OR (Action <> 'add_message' AND MessageId IS NULL))`
- Línea 71: `CONSTRAINT CK_Operation_Actor CHECK (Actor = 'local-operator')`

**Claves foráneas:**

- Línea 66: `CONSTRAINT FK_Operation_Contact FOREIGN KEY (ContactId) REFERENCES crm.Contact(ContactId)`
- Línea 67: `CONSTRAINT FK_Operation_Conversation FOREIGN KEY (ConversationId) REFERENCES crm.Conversation(ConversationId)`
- Línea 68: `CONSTRAINT FK_Operation_Message FOREIGN KEY (MessageId) REFERENCES crm.Message(MessageId)`

**Consumidores literales:** [backend/app/database_connections.py:56](../../../backend/app/database_connections.py#L56), [backend/app/sql_workspace.py:221](../../../backend/app/sql_workspace.py#L221), [backend/app/modules/conversation_events/api/router.py:31](../../../backend/app/modules/conversation_events/api/router.py#L31), [backend/app/modules/contacts/application/activity.py:138](../../../backend/app/modules/contacts/application/activity.py#L138), [backend/app/modules/contacts/application/merge.py:414](../../../backend/app/modules/contacts/application/merge.py#L414)

## crm_admissions.AdmissionCase

[Declaración 002:22](../../../backend/migrations/002_local_admissions.sql#L22).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| CaseId | uniqueidentifier | No | CaseId uniqueidentifier NOT NULL CONSTRAINT PK_AdmissionCase PRIMARY KEY | 23 |
| AspirantId | int | No | AspirantId int NOT NULL CONSTRAINT UQ_AdmissionCase_Aspirant UNIQUE | 24 |
| CreatedAt | datetime2(7) | No | CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_AdmissionCase_CreatedAt DEFAULT SYSUTCDATETIME() | 25 |

**Consumidores literales:** [backend/app/modules/admissions/application/service.py:299](../../../backend/app/modules/admissions/application/service.py#L299)

## crm_admissions.Followup

[Declaración 002:27](../../../backend/migrations/002_local_admissions.sql#L27).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| FollowupId | uniqueidentifier | No | FollowupId uniqueidentifier NOT NULL CONSTRAINT PK_Followup PRIMARY KEY | 28 |
| CaseId | uniqueidentifier | No | CaseId uniqueidentifier NOT NULL | 29 |
| Body | nvarchar(2000) | No | Body nvarchar(2000) NOT NULL | 30 |
| StateId | int | No | StateId int NOT NULL | 31 |
| DueDate | date | Sí | DueDate date NULL | 31 |
| Revision | int | No | Revision int NOT NULL | 31 |
| CreatedAt | datetime2(7) | No | CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_Followup_CreatedAt DEFAULT SYSUTCDATETIME() | 32 |
| UpdatedAt | datetime2(7) | No | UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_Followup_UpdatedAt DEFAULT SYSUTCDATETIME() | 33 |

**Restricciones de tabla:**

- Línea 34: `CONSTRAINT FK_Followup_Case FOREIGN KEY (CaseId) REFERENCES crm_admissions.AdmissionCase(CaseId)`
- Línea 35: `CONSTRAINT CK_Followup_Body CHECK (LEN(LTRIM(RTRIM(Body)))>0)`
- Línea 36: `CONSTRAINT CK_Followup_Revision CHECK (Revision>0)`

**Claves foráneas:**

- Línea 34: `CONSTRAINT FK_Followup_Case FOREIGN KEY (CaseId) REFERENCES crm_admissions.AdmissionCase(CaseId)`

**CREATE INDEX explícitos:**

- `IX_Followup_Case`: (CaseId,CreatedAt DESC,FollowupId)  · [backend/migrations/002_local_admissions.sql:38](../../../backend/migrations/002_local_admissions.sql#L38).

**Consumidores literales:** [backend/app/modules/admissions/application/service.py:298](../../../backend/app/modules/admissions/application/service.py#L298)

## crm_admissions.Operation

[Declaración 002:39](../../../backend/migrations/002_local_admissions.sql#L39).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| OperationId | uniqueidentifier | No | OperationId uniqueidentifier NOT NULL CONSTRAINT PK_AdmissionOperation PRIMARY KEY | 40 |
| FollowupId | uniqueidentifier | No | FollowupId uniqueidentifier NOT NULL | 41 |
| Action | varchar(6) | No | Action varchar(6) NOT NULL | 41 |
| PayloadHash | binary(32) | No | PayloadHash binary(32) NOT NULL | 42 |
| Actor | varchar(32) | No | Actor varchar(32) NOT NULL CONSTRAINT DF_AdmissionOperation_Actor DEFAULT 'local-operator' | 43 |
| CreatedAt | datetime2(7) | No | CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_AdmissionOperation_CreatedAt DEFAULT SYSUTCDATETIME() | 44 |

**Restricciones de tabla:**

- Línea 45: `CONSTRAINT FK_AdmissionOperation_Followup FOREIGN KEY(FollowupId) REFERENCES crm_admissions.Followup(FollowupId)`
- Línea 46: `CONSTRAINT CK_AdmissionOperation_Action CHECK (Action IN ('create','edit'))`
- Línea 47: `CONSTRAINT CK_AdmissionOperation_Actor CHECK (Actor='local-operator')`

**Claves foráneas:**

- Línea 45: `CONSTRAINT FK_AdmissionOperation_Followup FOREIGN KEY(FollowupId) REFERENCES crm_admissions.Followup(FollowupId)`

**Consumidores literales:** [backend/app/modules/admissions/application/service.py:331](../../../backend/app/modules/admissions/application/service.py#L331)

## crm_inbox.Member

[Declaración 003:39](../../../backend/migrations/003_local_inbox.sql#L39).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| EmployeeId | int | No | EmployeeId int NOT NULL CONSTRAINT PK_InboxMember PRIMARY KEY | 40 |
| Enabled | bit | No | Enabled bit NOT NULL | 41 |
| CreatedAt | datetime2(7) | No | CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_InboxMember_Created DEFAULT SYSUTCDATETIME() | 42 |
| UpdatedAt | datetime2(7) | No | UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_InboxMember_Updated DEFAULT SYSUTCDATETIME() | 43 |

**Consumidores literales:** [backend/app/modules/inbox/application/operations.py:309](../../../backend/app/modules/inbox/application/operations.py#L309), [backend/app/modules/conversation_strategy/api/router.py:239](../../../backend/app/modules/conversation_strategy/api/router.py#L239)

## crm_inbox.Agent

[Declaración 003:45](../../../backend/migrations/003_local_inbox.sql#L45).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| AgentId | uniqueidentifier | No | AgentId uniqueidentifier NOT NULL CONSTRAINT PK_InboxAgent PRIMARY KEY | 46 |
| Name | nvarchar(100) | No | Name nvarchar(100) NOT NULL | 47 |
| Description | nvarchar(1000) | No | Description nvarchar(1000) NOT NULL | 47 |
| Enabled | bit | No | Enabled bit NOT NULL | 48 |
| CreatedAt | datetime2(7) | No | CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_InboxAgent_Created DEFAULT SYSUTCDATETIME() | 49 |
| UpdatedAt | datetime2(7) | No | UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_InboxAgent_Updated DEFAULT SYSUTCDATETIME() | 50 |

**Restricciones de tabla:**

- Línea 51: `CONSTRAINT CK_InboxAgent_Name CHECK(LEN(LTRIM(RTRIM(Name)))>0)`

**Consumidores literales:** [backend/app/modules/agents/service.py:79](../../../backend/app/modules/agents/service.py#L79), [backend/app/modules/inbox/application/operations.py:221](../../../backend/app/modules/inbox/application/operations.py#L221), [backend/app/modules/conversation_strategy/api/router.py:241](../../../backend/app/modules/conversation_strategy/api/router.py#L241)

## crm_inbox.Assignment

[Declaración 003:53](../../../backend/migrations/003_local_inbox.sql#L53).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| ConversationId | uniqueidentifier | No | ConversationId uniqueidentifier NOT NULL CONSTRAINT PK_InboxAssignment PRIMARY KEY | 54 |
| HumanEmployeeId | int | Sí | HumanEmployeeId int NULL | 55 |
| AiAgentId | uniqueidentifier | Sí | AiAgentId uniqueidentifier NULL | 55 |
| UpdatedAt | datetime2(7) | No | UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_InboxAssignment_Updated DEFAULT SYSUTCDATETIME() | 56 |

**Restricciones de tabla:**

- Línea 57: `CONSTRAINT FK_InboxAssignment_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId)`
- Línea 58: `CONSTRAINT FK_InboxAssignment_Human FOREIGN KEY(HumanEmployeeId) REFERENCES crm_inbox.Member(EmployeeId)`
- Línea 59: `CONSTRAINT FK_InboxAssignment_Agent FOREIGN KEY(AiAgentId) REFERENCES crm_inbox.Agent(AgentId)`

**Claves foráneas:**

- Línea 57: `CONSTRAINT FK_InboxAssignment_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId)`
- Línea 58: `CONSTRAINT FK_InboxAssignment_Human FOREIGN KEY(HumanEmployeeId) REFERENCES crm_inbox.Member(EmployeeId)`
- Línea 59: `CONSTRAINT FK_InboxAssignment_Agent FOREIGN KEY(AiAgentId) REFERENCES crm_inbox.Agent(AgentId)`

**Consumidores literales:** [backend/app/modules/agents/service.py:413](../../../backend/app/modules/agents/service.py#L413), [backend/app/modules/inbox/application/operations.py:39](../../../backend/app/modules/inbox/application/operations.py#L39), [backend/app/modules/conversation_strategy/api/router.py:238](../../../backend/app/modules/conversation_strategy/api/router.py#L238), [backend/app/modules/ai/application/admissions.py:365](../../../backend/app/modules/ai/application/admissions.py#L365)

## crm_inbox.Task

[Declaración 003:61](../../../backend/migrations/003_local_inbox.sql#L61).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| TaskId | uniqueidentifier | No | TaskId uniqueidentifier NOT NULL CONSTRAINT PK_InboxTask PRIMARY KEY | 62 |
| ConversationId | uniqueidentifier | No | ConversationId uniqueidentifier NOT NULL | 63 |
| Title | nvarchar(120) | No | Title nvarchar(120) NOT NULL | 63 |
| HumanEmployeeId | int | Sí | HumanEmployeeId int NULL | 64 |
| DueAt | datetime2(7) | Sí | DueAt datetime2(7) NULL | 64 |
| Priority | varchar(8) | No | Priority varchar(8) NOT NULL | 65 |
| Status | varchar(12) | No | Status varchar(12) NOT NULL | 65 |
| CreatedAt | datetime2(7) | No | CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_InboxTask_Created DEFAULT SYSUTCDATETIME() | 66 |
| UpdatedAt | datetime2(7) | No | UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_InboxTask_Updated DEFAULT SYSUTCDATETIME() | 67 |

**Restricciones de tabla:**

- Línea 68: `CONSTRAINT FK_InboxTask_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId)`
- Línea 69: `CONSTRAINT FK_InboxTask_Human FOREIGN KEY(HumanEmployeeId) REFERENCES crm_inbox.Member(EmployeeId)`
- Línea 70: `CONSTRAINT CK_InboxTask_Title CHECK(LEN(LTRIM(RTRIM(Title)))>0)`
- Línea 71: `CONSTRAINT CK_InboxTask_Priority CHECK(Priority IN ('low','normal','high','urgent'))`
- Línea 72: `CONSTRAINT CK_InboxTask_Status CHECK(Status IN ('pending','completed','cancelled'))`

**Claves foráneas:**

- Línea 68: `CONSTRAINT FK_InboxTask_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId)`
- Línea 69: `CONSTRAINT FK_InboxTask_Human FOREIGN KEY(HumanEmployeeId) REFERENCES crm_inbox.Member(EmployeeId)`

**CREATE INDEX explícitos:**

- `IX_InboxTask_Conversation`: (ConversationId,CreatedAt,TaskId)  · [backend/migrations/003_local_inbox.sql:74](../../../backend/migrations/003_local_inbox.sql#L74).

**Consumidores literales:** [backend/app/modules/agents/runtime.py:119](../../../backend/app/modules/agents/runtime.py#L119), [backend/app/modules/inbox/application/operations.py:337](../../../backend/app/modules/inbox/application/operations.py#L337), [backend/app/modules/conversation_strategy/api/router.py:221](../../../backend/app/modules/conversation_strategy/api/router.py#L221), [backend/app/modules/conversation_events/api/router.py:34](../../../backend/app/modules/conversation_events/api/router.py#L34), [backend/app/modules/contacts/application/activity.py:118](../../../backend/app/modules/contacts/application/activity.py#L118), [backend/app/modules/ai/application/admissions.py:365](../../../backend/app/modules/ai/application/admissions.py#L365)

## crm_inbox.SlaPolicy

[Declaración 003:75](../../../backend/migrations/003_local_inbox.sql#L75).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| PolicyId | tinyint | No | PolicyId tinyint NOT NULL CONSTRAINT PK_InboxSlaPolicy PRIMARY KEY | 76 |
| Enabled | bit | No | Enabled bit NOT NULL | 77 |
| ThresholdMinutes | int | No | ThresholdMinutes int NOT NULL | 77 |
| UpdatedAt | datetime2(7) | No | UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_InboxSlaPolicy_Updated DEFAULT SYSUTCDATETIME() | 78 |

**Restricciones de tabla:**

- Línea 79: `CONSTRAINT CK_InboxSlaPolicy_Single CHECK(PolicyId=1)`
- Línea 80: `CONSTRAINT CK_InboxSlaPolicy_Threshold CHECK(ThresholdMinutes BETWEEN 1 AND 525600)`

**Consumidores literales:** [backend/app/modules/inbox/application/operations.py:40](../../../backend/app/modules/inbox/application/operations.py#L40)

## crm_inbox.Operation

[Declaración 003:82](../../../backend/migrations/003_local_inbox.sql#L82).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| OperationId | uniqueidentifier | No | OperationId uniqueidentifier NOT NULL CONSTRAINT PK_InboxOperation PRIMARY KEY NONCLUSTERED | 83 |
| Revision | bigint | No | Revision bigint IDENTITY(1,1) NOT NULL CONSTRAINT UQ_InboxOperation_Revision UNIQUE CLUSTERED | 84 |
| Action | varchar(20) | No | Action varchar(20) NOT NULL | 85 |
| EntityKey | nvarchar(100) | No | EntityKey nvarchar(100) NOT NULL | 85 |
| PayloadHash | binary(32) | No | PayloadHash binary(32) NOT NULL | 86 |
| Actor | varchar(32) | No | Actor varchar(32) NOT NULL | 86 |
| CreatedAt | datetime2(7) | No | CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_InboxOperation_Created DEFAULT SYSUTCDATETIME() | 87 |

**Restricciones de tabla:**

- Línea 88: `CONSTRAINT CK_InboxOperation_Action CHECK(Action IN ('member','agent','assignment','task_create','task_edit','policy'))`
- Línea 89: `CONSTRAINT CK_InboxOperation_Actor CHECK(Actor='local-operator')`

**Consumidores literales:** [backend/app/modules/inbox/application/operations.py:184](../../../backend/app/modules/inbox/application/operations.py#L184), [backend/app/modules/conversation_events/api/router.py:34](../../../backend/app/modules/conversation_events/api/router.py#L34), [backend/app/modules/contacts/application/activity.py:105](../../../backend/app/modules/contacts/application/activity.py#L105), [backend/app/modules/contacts/application/merge.py:390](../../../backend/app/modules/contacts/application/merge.py#L390)

## crm_events.Event

[Declaración 004:146](../../../backend/migrations/004_conversation_events.sql#L146).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| EventId | bigint | No | EventId bigint IDENTITY(1,1) NOT NULL CONSTRAINT PK_Event PRIMARY KEY | 147 |
| SourceKind | varchar(20) | No | SourceKind varchar(20) NOT NULL | 148 |
| SourceId | uniqueidentifier | No | SourceId uniqueidentifier NOT NULL | 148 |
| SourceRevision | bigint | Sí | SourceRevision bigint NULL | 149 |
| SourceAction | varchar(24) | Sí | SourceAction varchar(24) NULL | 149 |
| ConversationId | uniqueidentifier | No | ConversationId uniqueidentifier NOT NULL | 150 |
| SourceOccurredAt | datetime2(7) | No | SourceOccurredAt datetime2(7) NOT NULL | 151 |
| CapturedAt | datetime2(7) | No | CapturedAt datetime2(7) NOT NULL CONSTRAINT DF_Event_Captured DEFAULT SYSUTCDATETIME() | 152 |
| State | varchar(12) | No | State varchar(12) NOT NULL CONSTRAINT DF_Event_State DEFAULT 'pending' | 153 |
| Attempts | int | No | Attempts int NOT NULL CONSTRAINT DF_Event_Attempts DEFAULT 0 | 154 |
| TotalAttempts | int | No | TotalAttempts int NOT NULL CONSTRAINT DF_Event_Total DEFAULT 0 | 155 |
| NextAttemptAt | datetime2(7) | No | NextAttemptAt datetime2(7) NOT NULL CONSTRAINT DF_Event_Next DEFAULT SYSUTCDATETIME() | 156 |
| LeaseToken | uniqueidentifier | Sí | LeaseToken uniqueidentifier NULL | 157 |
| LeaseUntil | datetime2(7) | Sí | LeaseUntil datetime2(7) NULL | 157 |
| PreparedAt | datetime2(7) | Sí | PreparedAt datetime2(7) NULL | 158 |
| ErrorCode | varchar(40) | Sí | ErrorCode varchar(40) NULL | 158 |

**Restricciones de tabla:**

- Línea 159: `CONSTRAINT UQ_Event_Source UNIQUE(SourceKind,SourceId)`
- Línea 160: `CONSTRAINT FK_Event_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId)`
- Línea 161: `CONSTRAINT CK_Event_Source CHECK(SourceKind IN ('baseline','message','crm_operation','inbox_operation'))`
- Línea 162: `CONSTRAINT CK_Event_State CHECK(State IN ('pending','leased','prepared','failed'))`
- Línea 163: `CONSTRAINT CK_Event_Attempts CHECK(Attempts BETWEEN 0 AND 5 AND TotalAttempts>=Attempts)`
- Línea 164: `CONSTRAINT CK_Event_Lease CHECK((State='leased' AND LeaseToken IS NOT NULL AND LeaseUntil IS NOT NULL) OR (State<>'leased' AND LeaseToken IS NULL AND LeaseUntil IS NULL))`

**Claves foráneas:**

- Línea 160: `CONSTRAINT FK_Event_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId)`

**CREATE INDEX explícitos:**

- `IX_Event_Work`: (State,NextAttemptAt,EventId)  · [backend/migrations/004_conversation_events.sql:167](../../../backend/migrations/004_conversation_events.sql#L167).
- `IX_Event_Conversation`: (ConversationId,EventId)  · [backend/migrations/004_conversation_events.sql:168](../../../backend/migrations/004_conversation_events.sql#L168).

**Consumidores literales:** [backend/app/modules/conversation_events/api/router.py:38](../../../backend/app/modules/conversation_events/api/router.py#L38), [backend/app/modules/conversation_analysis/api/router.py:193](../../../backend/app/modules/conversation_analysis/api/router.py#L193)

## crm_events.Preparation

[Declaración 004:169](../../../backend/migrations/004_conversation_events.sql#L169).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| ConversationId | uniqueidentifier | No | ConversationId uniqueidentifier NOT NULL CONSTRAINT PK_Preparation PRIMARY KEY | 170 |
| LastEventId | bigint | No | LastEventId bigint NOT NULL | 171 |
| MessageCount | bigint | No | MessageCount bigint NOT NULL | 171 |
| LatestMessageSequence | bigint | Sí | LatestMessageSequence bigint NULL | 172 |
| SourceCrmRevision | bigint | No | SourceCrmRevision bigint NOT NULL | 172 |
| SourceInboxRevision | bigint | No | SourceInboxRevision bigint NOT NULL | 173 |
| PreparedAt | datetime2(7) | No | PreparedAt datetime2(7) NOT NULL | 173 |

**Restricciones de tabla:**

- Línea 174: `CONSTRAINT FK_Preparation_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId)`
- Línea 175: `CONSTRAINT FK_Preparation_Event FOREIGN KEY(LastEventId) REFERENCES crm_events.Event(EventId)`

**Claves foráneas:**

- Línea 174: `CONSTRAINT FK_Preparation_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId)`
- Línea 175: `CONSTRAINT FK_Preparation_Event FOREIGN KEY(LastEventId) REFERENCES crm_events.Event(EventId)`

**Consumidores literales:** [backend/app/modules/conversation_events/api/router.py:172](../../../backend/app/modules/conversation_events/api/router.py#L172)

## crm_events.RetryOperation

[Declaración 004:177](../../../backend/migrations/004_conversation_events.sql#L177).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| OperationId | uniqueidentifier | No | OperationId uniqueidentifier NOT NULL CONSTRAINT PK_EventRetry PRIMARY KEY | 178 |
| RetriedCount | int | No | RetriedCount int NOT NULL | 179 |
| CreatedAt | datetime2(7) | No | CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_EventRetry_Created DEFAULT SYSUTCDATETIME() | 180 |

**Restricciones de tabla:**

- Línea 181: `CONSTRAINT CK_EventRetry_Count CHECK(RetriedCount BETWEEN 0 AND 25)`

**Consumidores literales:** [backend/app/modules/conversation_events/api/router.py:217](../../../backend/app/modules/conversation_events/api/router.py#L217)

## crm_analysis.Policy

[Declaración 005:204](../../../backend/migrations/005_conversation_analysis.sql#L204).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| PolicyId | tinyint | No | PolicyId tinyint NOT NULL CONSTRAINT PK_AnalysisPolicy PRIMARY KEY | 205 |
| Revision | bigint | No | Revision bigint NOT NULL | 206 |
| Enabled | bit | No | Enabled bit NOT NULL | 206 |
| Provider | varchar(16) | No | Provider varchar(16) NOT NULL | 206 |
| Model | varchar(200) | No | Model varchar(200) NOT NULL | 207 |
| InputScope | varchar(30) | No | InputScope varchar(30) NOT NULL | 207 |
| ScopeAccepted | bit | No | ScopeAccepted bit NOT NULL | 207 |
| DailyRequests | int | No | DailyRequests int NOT NULL | 208 |
| DailyOutputTokens | int | No | DailyOutputTokens int NOT NULL | 208 |
| OutputTokens | int | No | OutputTokens int NOT NULL | 208 |
| UpdatedAt | datetime2(7) | No | UpdatedAt datetime2(7) NOT NULL | 209 |

**Restricciones de tabla:**

- Línea 210: `CONSTRAINT CK_AnalysisPolicy CHECK(PolicyId=1 AND Revision>0 AND Provider IN ('gemini','xai','openrouter') AND InputScope='redacted_messages' AND (Enabled=0 OR ScopeAccepted=1) AND DailyRequests BETWEEN 1 AND 10000 AND DailyOutputTokens BETWEEN 256 AND 10000000 AND OutputTokens BETWEEN 256 AND 8192 AND OutputTokens<=DailyOutputTokens)`

**Consumidores literales:** [backend/app/modules/conversation_analysis/api/router.py:283](../../../backend/app/modules/conversation_analysis/api/router.py#L283)

## crm_analysis.ConversationState

[Declaración 005:215](../../../backend/migrations/005_conversation_analysis.sql#L215).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| ConversationId | uniqueidentifier | No | ConversationId uniqueidentifier NOT NULL CONSTRAINT PK_AnalysisState PRIMARY KEY | 216 |
| Revision | bigint | No | Revision bigint NOT NULL | 217 |
| Generation | bigint | No | Generation bigint NOT NULL | 217 |
| Binding | varchar(200) | No | Binding varchar(200) NOT NULL | 217 |
| ContextGeneration | bigint | Sí | ContextGeneration bigint NULL | 218 |
| ContextJson | nvarchar(max) | Sí | ContextJson nvarchar(max) NULL | 218 |
| AnalyzedAt | datetime2(7) | Sí | AnalyzedAt datetime2(7) NULL | 218 |
| ContextProvider | varchar(16) | Sí | ContextProvider varchar(16) NULL | 219 |
| ContextModel | varchar(200) | Sí | ContextModel varchar(200) NULL | 219 |
| ContextPromptVersion | varchar(40) | Sí | ContextPromptVersion varchar(40) NULL | 220 |
| ContextPolicyRevision | bigint | Sí | ContextPolicyRevision bigint NULL | 220 |
| Fingerprint | char(64) | Sí | Fingerprint char(64) NULL | 221 |
| Status | varchar(20) | No | Status varchar(20) NOT NULL | 221 |
| LeaseToken | uniqueidentifier | Sí | LeaseToken uniqueidentifier NULL | 222 |
| LeaseUntil | datetime2(7) | Sí | LeaseUntil datetime2(7) NULL | 222 |
| Failures | int | No | Failures int NOT NULL | 223 |
| NextAttemptAt | datetime2(7) | No | NextAttemptAt datetime2(7) NOT NULL | 223 |
| ErrorCode | varchar(60) | Sí | ErrorCode varchar(60) NULL | 223 |

**Restricciones de tabla:**

- Línea 224: `CONSTRAINT FK_AnalysisState_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId)`
- Línea 225: `CONSTRAINT CK_AnalysisState CHECK(Revision>=0 AND Generation>0 AND Failures BETWEEN 0 AND 3 AND Status IN ('pending','processing','current','failed','no_messages') AND (ContextJson IS NULL OR ISJSON(ContextJson)=1) AND ((Status='processing' AND LeaseToken IS NOT NULL AND LeaseUntil IS NOT NULL) OR (Status<>'processing' AND LeaseToken IS NULL AND LeaseUntil IS NULL)))`

**Claves foráneas:**

- Línea 224: `CONSTRAINT FK_AnalysisState_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId)`

**Consumidores literales:** [backend/app/modules/conversation_strategy/api/router.py:88](../../../backend/app/modules/conversation_strategy/api/router.py#L88), [backend/app/modules/conversation_analysis/api/router.py:30](../../../backend/app/modules/conversation_analysis/api/router.py#L30)

## crm_analysis.Receipt

[Declaración 005:231](../../../backend/migrations/005_conversation_analysis.sql#L231).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| ConversationId | uniqueidentifier | No | ConversationId uniqueidentifier NOT NULL | 232 |
| Generation | bigint | No | Generation bigint NOT NULL | 232 |
| EventId | bigint | No | EventId bigint NOT NULL | 232 |
| CompletedAt | datetime2(7) | No | CompletedAt datetime2(7) NOT NULL | 233 |

**Restricciones de tabla:**

- Línea 234: `CONSTRAINT PK_AnalysisReceipt PRIMARY KEY(ConversationId,Generation,EventId)`
- Línea 235: `CONSTRAINT FK_AnalysisReceipt_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId)`
- Línea 236: `CONSTRAINT FK_AnalysisReceipt_Event FOREIGN KEY(EventId) REFERENCES crm_events.Event(EventId)`

**Claves foráneas:**

- Línea 235: `CONSTRAINT FK_AnalysisReceipt_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId)`
- Línea 236: `CONSTRAINT FK_AnalysisReceipt_Event FOREIGN KEY(EventId) REFERENCES crm_events.Event(EventId)`

**Consumidores literales:** [backend/app/modules/conversation_analysis/api/router.py:33](../../../backend/app/modules/conversation_analysis/api/router.py#L33)

## crm_analysis.Attempt

[Declaración 005:238](../../../backend/migrations/005_conversation_analysis.sql#L238).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| AttemptId | uniqueidentifier | No | AttemptId uniqueidentifier NOT NULL CONSTRAINT PK_AnalysisAttempt PRIMARY KEY | 239 |
| ConversationId | uniqueidentifier | No | ConversationId uniqueidentifier NOT NULL | 240 |
| Generation | bigint | No | Generation bigint NOT NULL | 240 |
| PolicyRevision | bigint | No | PolicyRevision bigint NOT NULL | 240 |
| ReservedOutputTokens | int | No | ReservedOutputTokens int NOT NULL | 241 |
| Status | varchar(16) | No | Status varchar(16) NOT NULL | 241 |
| CreatedAt | datetime2(7) | No | CreatedAt datetime2(7) NOT NULL | 241 |
| CompletedAt | datetime2(7) | Sí | CompletedAt datetime2(7) NULL | 242 |
| ErrorCode | varchar(60) | Sí | ErrorCode varchar(60) NULL | 242 |

**Restricciones de tabla:**

- Línea 243: `CONSTRAINT FK_AnalysisAttempt_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId)`
- Línea 244: `CONSTRAINT CK_AnalysisAttempt CHECK(ReservedOutputTokens BETWEEN 256 AND 8192 AND Status IN ('reserved','succeeded','failed','stale','expired'))`

**Claves foráneas:**

- Línea 243: `CONSTRAINT FK_AnalysisAttempt_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId)`

**CREATE INDEX explícitos:**

- `IX_AnalysisAttempt_Day`: (CreatedAt) INCLUDE(ReservedOutputTokens) · [backend/migrations/005_conversation_analysis.sql:247](../../../backend/migrations/005_conversation_analysis.sql#L247).

**Consumidores literales:** [backend/app/modules/conversation_analysis/api/router.py:520](../../../backend/app/modules/conversation_analysis/api/router.py#L520), [backend/app/modules/contacts/application/merge.py:266](../../../backend/app/modules/contacts/application/merge.py#L266)

## crm_analysis.Feedback

[Declaración 005:248](../../../backend/migrations/005_conversation_analysis.sql#L248).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| FeedbackId | uniqueidentifier | No | FeedbackId uniqueidentifier NOT NULL CONSTRAINT PK_AnalysisFeedback PRIMARY KEY | 249 |
| ConversationId | uniqueidentifier | No | ConversationId uniqueidentifier NOT NULL | 250 |
| SourceRevision | bigint | No | SourceRevision bigint NOT NULL | 250 |
| Text | nvarchar(1000) | No | Text nvarchar(1000) NOT NULL | 251 |
| CreatedAt | datetime2(7) | No | CreatedAt datetime2(7) NOT NULL | 251 |
| ConsumedGeneration | bigint | No | ConsumedGeneration bigint NOT NULL CONSTRAINT DF_AnalysisFeedback_Generation DEFAULT 0 | 252 |

**Restricciones de tabla:**

- Línea 253: `CONSTRAINT FK_AnalysisFeedback_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId)`

**Claves foráneas:**

- Línea 253: `CONSTRAINT FK_AnalysisFeedback_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId)`

**Consumidores literales:** [backend/app/modules/conversation_strategy/api/router.py:80](../../../backend/app/modules/conversation_strategy/api/router.py#L80), [backend/app/modules/conversation_analysis/api/router.py:212](../../../backend/app/modules/conversation_analysis/api/router.py#L212)

## crm_analysis.Operation

[Declaración 005:255](../../../backend/migrations/005_conversation_analysis.sql#L255).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| OperationId | uniqueidentifier | No | OperationId uniqueidentifier NOT NULL CONSTRAINT PK_AnalysisOperation PRIMARY KEY | 256 |
| Action | varchar(16) | No | Action varchar(16) NOT NULL | 257 |
| RequestHash | char(64) | No | RequestHash char(64) NOT NULL | 257 |
| ResponseJson | nvarchar(max) | No | ResponseJson nvarchar(max) NOT NULL | 257 |
| CreatedAt | datetime2(7) | No | CreatedAt datetime2(7) NOT NULL | 258 |

**Restricciones de tabla:**

- Línea 259: `CONSTRAINT CK_AnalysisOperation CHECK(Action IN ('policy','retry','feedback') AND ISJSON(ResponseJson)=1)`

**Consumidores literales:** [backend/app/modules/conversation_analysis/api/router.py:243](../../../backend/app/modules/conversation_analysis/api/router.py#L243)

## crm_config.Configuration

[Declaración 006:21](../../../backend/migrations/006_crm_configuration.sql#L21).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| ConfigurationId | int | No | ConfigurationId int NOT NULL CONSTRAINT PK_CrmConfiguration PRIMARY KEY | 22 |
| Document | nvarchar(max) | No | Document nvarchar(max) NOT NULL | 23 |
| Revision | bigint | No | Revision bigint NOT NULL | 23 |
| CreatedAt | datetime2(7) | No | CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_CrmConfiguration_Created DEFAULT SYSUTCDATETIME() | 24 |
| UpdatedAt | datetime2(7) | No | UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_CrmConfiguration_Updated DEFAULT SYSUTCDATETIME() | 25 |

**Restricciones de tabla:**

- Línea 26: `CONSTRAINT CK_CrmConfiguration CHECK(ConfigurationId=1 AND Revision>0 AND ISJSON(Document)=1)`

**Consumidores literales:** [backend/app/modules/crm_configuration/application/service.py:121](../../../backend/app/modules/crm_configuration/application/service.py#L121)

## crm_config.Operation

[Declaración 006:28](../../../backend/migrations/006_crm_configuration.sql#L28).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| OperationId | uniqueidentifier | No | OperationId uniqueidentifier NOT NULL CONSTRAINT PK_CrmConfigOperation PRIMARY KEY | 29 |
| PayloadHash | binary(32) | No | PayloadHash binary(32) NOT NULL | 30 |
| Revision | bigint | No | Revision bigint NOT NULL CONSTRAINT UQ_CrmConfigRevision UNIQUE | 30 |
| CreatedAt | datetime2(7) | No | CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_CrmConfigOperation_Created DEFAULT SYSUTCDATETIME() | 31 |

**Restricciones de tabla:**

- Línea 32: `CONSTRAINT CK_CrmConfigOperation CHECK(Revision>1)`

**Consumidores literales:** [backend/app/modules/crm_configuration/application/service.py:212](../../../backend/app/modules/crm_configuration/application/service.py#L212), [backend/app/modules/contacts/application/merge.py:385](../../../backend/app/modules/contacts/application/merge.py#L385)

## crm_identity.Profile

[Declaración 007:21](../../../backend/migrations/007_institutional_identity.sql#L21).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| ContactId | uniqueidentifier | No | ContactId uniqueidentifier NOT NULL CONSTRAINT PK_IdentityProfile PRIMARY KEY | 22 |
| GivenNames | nvarchar(100) | No | GivenNames nvarchar(100) NOT NULL | 23 |
| FirstSurname | nvarchar(30) | No | FirstSurname nvarchar(30) NOT NULL | 23 |
| SecondSurname | nvarchar(30) | No | SecondSurname nvarchar(30) NOT NULL | 23 |
| DocumentTypeId | tinyint | Sí | DocumentTypeId tinyint NULL | 24 |
| Document | nvarchar(16) | No | Document nvarchar(16) NOT NULL | 24 |
| Email | nvarchar(160) | No | Email nvarchar(160) NOT NULL | 24 |
| AspirationPeriodId | int | Sí | AspirationPeriodId int NULL | 24 |
| CreatedAt | datetime2(7) | No | CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_IdentityProfile_Created DEFAULT SYSUTCDATETIME() | 25 |
| UpdatedAt | datetime2(7) | No | UpdatedAt datetime2(7) NOT NULL CONSTRAINT DF_IdentityProfile_Updated DEFAULT SYSUTCDATETIME() | 26 |

**Restricciones de tabla:**

- Línea 27: `CONSTRAINT FK_IdentityProfile_Contact FOREIGN KEY(ContactId) REFERENCES crm.Contact(ContactId)`
- Línea 28: `CONSTRAINT CK_IdentityProfile_Document CHECK((DocumentTypeId IS NULL AND Document=N'') OR (DocumentTypeId IS NOT NULL AND LEN(LTRIM(RTRIM(Document)))>0))`

**Claves foráneas:**

- Línea 27: `CONSTRAINT FK_IdentityProfile_Contact FOREIGN KEY(ContactId) REFERENCES crm.Contact(ContactId)`

**Consumidores literales:** [backend/app/modules/contacts/api/router.py:51](../../../backend/app/modules/contacts/api/router.py#L51), [backend/app/modules/contacts/application/merge.py:575](../../../backend/app/modules/contacts/application/merge.py#L575)

## crm_merge.MergeCase

[Declaración 008:21](../../../backend/migrations/008_contact_merge.sql#L21).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| MergeId | uniqueidentifier | No | MergeId uniqueidentifier NOT NULL CONSTRAINT PK_MergeCase PRIMARY KEY | 22 |
| SourceContactId | uniqueidentifier | No | SourceContactId uniqueidentifier NOT NULL | 23 |
| TargetContactId | uniqueidentifier | No | TargetContactId uniqueidentifier NOT NULL | 23 |
| Active | bit | No | Active bit NOT NULL | 24 |
| BeforeJson | nvarchar(max) | No | BeforeJson nvarchar(max) NOT NULL | 24 |
| AppliedJson | nvarchar(max) | No | AppliedJson nvarchar(max) NOT NULL | 24 |
| ChoicesJson | nvarchar(max) | No | ChoicesJson nvarchar(max) NOT NULL | 25 |
| AppliedCrmRevision | bigint | No | AppliedCrmRevision bigint NOT NULL | 25 |
| UndoBeforeJson | nvarchar(max) | Sí | UndoBeforeJson nvarchar(max) NULL | 26 |
| UndoAppliedJson | nvarchar(max) | Sí | UndoAppliedJson nvarchar(max) NULL | 26 |
| CreatedAt | datetime2(7) | No | CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_MergeCase_Created DEFAULT SYSUTCDATETIME() | 27 |
| UndoneAt | datetime2(7) | Sí | UndoneAt datetime2(7) NULL | 28 |

**Restricciones de tabla:**

- Línea 29: `CONSTRAINT FK_MergeCase_Source FOREIGN KEY(SourceContactId) REFERENCES crm.Contact(ContactId)`
- Línea 30: `CONSTRAINT FK_MergeCase_Target FOREIGN KEY(TargetContactId) REFERENCES crm.Contact(ContactId)`
- Línea 31: `CONSTRAINT CK_MergeCase CHECK(SourceContactId<>TargetContactId AND AppliedCrmRevision>0 AND ISJSON(BeforeJson)=1 AND LEFT(LTRIM(BeforeJson),1)=N'{' AND ISJSON(AppliedJson)=1 AND LEFT(LTRIM(AppliedJson),1)=N'{' AND ISJSON(ChoicesJson)=1 AND LEFT(LTRIM(ChoicesJson),1)=N'{' AND ((Active=1 AND UndoneAt IS NULL AND UndoBeforeJson IS NULL AND UndoAppliedJson IS NULL) OR (Active=0 AND UndoneAt IS NOT NULL AND UndoBeforeJson IS NOT NULL AND UndoAppliedJson IS NOT NULL AND ISJSON(UndoBeforeJson)=1 AND LEFT(LTRIM(UndoBeforeJson),1)=N'{' AND ISJSON(UndoAppliedJson)=1 AND LEFT(LTRIM(UndoAppliedJson),1)=N'{')))`

**Claves foráneas:**

- Línea 29: `CONSTRAINT FK_MergeCase_Source FOREIGN KEY(SourceContactId) REFERENCES crm.Contact(ContactId)`
- Línea 30: `CONSTRAINT FK_MergeCase_Target FOREIGN KEY(TargetContactId) REFERENCES crm.Contact(ContactId)`

**CREATE INDEX explícitos:**

- `UX_MergeCase_ActiveSource`: UNIQUE (SourceContactId) WHERE Active=1 · [backend/migrations/008_contact_merge.sql:40](../../../backend/migrations/008_contact_merge.sql#L40).

**Consumidores literales:** [backend/app/modules/contacts/application/merge.py:204](../../../backend/app/modules/contacts/application/merge.py#L204)

## crm_merge.Operation

[Declaración 008:41](../../../backend/migrations/008_contact_merge.sql#L41).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| OperationId | uniqueidentifier | No | OperationId uniqueidentifier NOT NULL CONSTRAINT PK_MergeOperation PRIMARY KEY NONCLUSTERED | 42 |
| Revision | bigint | No | Revision bigint IDENTITY(1,1) NOT NULL CONSTRAINT UQ_MergeRevision UNIQUE CLUSTERED | 43 |
| Action | varchar(16) | No | Action varchar(16) NOT NULL | 44 |
| MergeId | uniqueidentifier | Sí | MergeId uniqueidentifier NULL | 44 |
| SourceContactId | uniqueidentifier | No | SourceContactId uniqueidentifier NOT NULL | 45 |
| TargetContactId | uniqueidentifier | No | TargetContactId uniqueidentifier NOT NULL | 45 |
| PayloadHash | binary(32) | No | PayloadHash binary(32) NOT NULL | 46 |
| IdentifiersJson | nvarchar(max) | No | IdentifiersJson nvarchar(max) NOT NULL | 46 |
| Actor | varchar(32) | No | Actor varchar(32) NOT NULL | 47 |
| CreatedAt | datetime2(7) | No | CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_MergeOperation_Created DEFAULT SYSUTCDATETIME() | 47 |

**Restricciones de tabla:**

- Línea 48: `CONSTRAINT FK_MergeOperation_Case FOREIGN KEY(MergeId) REFERENCES crm_merge.MergeCase(MergeId)`
- Línea 49: `CONSTRAINT FK_MergeOperation_Source FOREIGN KEY(SourceContactId) REFERENCES crm.Contact(ContactId)`
- Línea 50: `CONSTRAINT FK_MergeOperation_Target FOREIGN KEY(TargetContactId) REFERENCES crm.Contact(ContactId)`
- Línea 51: `CONSTRAINT CK_MergeOperation CHECK(Action IN ('merge','undo','identifiers') AND Actor='local-operator' AND ISJSON(IdentifiersJson)=1 AND LEFT(LTRIM(IdentifiersJson),1)=N'[' AND ((Action='identifiers' AND MergeId IS NULL) OR (Action<>'identifiers' AND MergeId IS NOT NULL)))`

**Claves foráneas:**

- Línea 48: `CONSTRAINT FK_MergeOperation_Case FOREIGN KEY(MergeId) REFERENCES crm_merge.MergeCase(MergeId)`
- Línea 49: `CONSTRAINT FK_MergeOperation_Source FOREIGN KEY(SourceContactId) REFERENCES crm.Contact(ContactId)`
- Línea 50: `CONSTRAINT FK_MergeOperation_Target FOREIGN KEY(TargetContactId) REFERENCES crm.Contact(ContactId)`

**Consumidores literales:** [backend/app/modules/contacts/application/activity.py:147](../../../backend/app/modules/contacts/application/activity.py#L147), [backend/app/modules/contacts/application/merge.py:245](../../../backend/app/modules/contacts/application/merge.py#L245)

## crm_strategy.Policy

[Declaración 009:21](../../../backend/migrations/009_conversation_strategy.sql#L21).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| ScopeKey | varchar(36) | No | ScopeKey varchar(36) NOT NULL CONSTRAINT PK_StrategyPolicy PRIMARY KEY | 22 |
| ConversationId | uniqueidentifier | Sí | ConversationId uniqueidentifier NULL | 23 |
| Enabled | bit | No | Enabled bit NOT NULL | 23 |

**Restricciones de tabla:**

- Línea 24: `CONSTRAINT FK_StrategyPolicy_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId)`
- Línea 25: `CONSTRAINT CK_StrategyPolicy CHECK((ScopeKey='global' AND ConversationId IS NULL) OR (ConversationId IS NOT NULL AND ScopeKey=LOWER(CONVERT(varchar(36),ConversationId))))`

**Claves foráneas:**

- Línea 24: `CONSTRAINT FK_StrategyPolicy_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId)`

**Consumidores literales:** [backend/app/modules/conversation_strategy/api/router.py:165](../../../backend/app/modules/conversation_strategy/api/router.py#L165)

## crm_strategy.EvaluationPlan

[Declaración 009:28](../../../backend/migrations/009_conversation_strategy.sql#L28).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| PlanId | uniqueidentifier | No | PlanId uniqueidentifier NOT NULL CONSTRAINT PK_StrategyPlan PRIMARY KEY | 29 |
| ConversationId | uniqueidentifier | No | ConversationId uniqueidentifier NOT NULL | 30 |
| Generation | bigint | No | Generation bigint NOT NULL | 30 |
| AnalysisRevision | bigint | No | AnalysisRevision bigint NOT NULL | 30 |
| Fingerprint | char(64) | No | Fingerprint char(64) NOT NULL | 31 |
| Binding | varchar(300) | No | Binding varchar(300) NOT NULL | 31 |
| SemanticFingerprint | char(64) | No | SemanticFingerprint char(64) NOT NULL | 31 |
| DocumentJson | nvarchar(max) | No | DocumentJson nvarchar(max) NOT NULL | 32 |
| Provider | varchar(32) | No | Provider varchar(32) NOT NULL | 32 |
| Model | varchar(200) | No | Model varchar(200) NOT NULL | 32 |
| PromptVersion | varchar(40) | No | PromptVersion varchar(40) NOT NULL | 33 |
| PolicyRevision | bigint | No | PolicyRevision bigint NOT NULL | 33 |
| CreatedAt | datetime2(7) | No | CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_StrategyPlan_Created DEFAULT SYSUTCDATETIME() | 34 |

**Restricciones de tabla:**

- Línea 35: `CONSTRAINT FK_StrategyPlan_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId)`
- Línea 36: `CONSTRAINT UQ_StrategyPlan_Revision UNIQUE(ConversationId,Generation,AnalysisRevision)`
- Línea 37: `CONSTRAINT CK_StrategyPlan CHECK(Generation>0 AND AnalysisRevision>0 AND PolicyRevision>0 AND ISJSON(DocumentJson)=1 AND LEFT(LTRIM(DocumentJson),1)=N'{')`

**Claves foráneas:**

- Línea 35: `CONSTRAINT FK_StrategyPlan_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId)`

**Consumidores literales:** [backend/app/modules/conversation_strategy/api/router.py:23](../../../backend/app/modules/conversation_strategy/api/router.py#L23)

## crm_strategy.Operation

[Declaración 009:40](../../../backend/migrations/009_conversation_strategy.sql#L40).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| OperationId | uniqueidentifier | No | OperationId uniqueidentifier NOT NULL CONSTRAINT PK_StrategyOperation PRIMARY KEY NONCLUSTERED | 41 |
| Revision | bigint | No | Revision bigint IDENTITY(1,1) NOT NULL CONSTRAINT UQ_StrategyRevision UNIQUE CLUSTERED | 42 |
| Action | varchar(20) | No | Action varchar(20) NOT NULL | 43 |
| ConversationId | uniqueidentifier | No | ConversationId uniqueidentifier NOT NULL | 43 |
| PlanId | uniqueidentifier | Sí | PlanId uniqueidentifier NULL | 43 |
| TaskId | uniqueidentifier | Sí | TaskId uniqueidentifier NULL | 44 |
| PayloadHash | binary(32) | No | PayloadHash binary(32) NOT NULL | 44 |
| DocumentJson | nvarchar(max) | No | DocumentJson nvarchar(max) NOT NULL | 44 |
| Actor | varchar(32) | No | Actor varchar(32) NOT NULL | 45 |
| CreatedAt | datetime2(7) | No | CreatedAt datetime2(7) NOT NULL CONSTRAINT DF_StrategyOperation_Created DEFAULT SYSUTCDATETIME() | 45 |

**Restricciones de tabla:**

- Línea 46: `CONSTRAINT FK_StrategyOperation_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId)`
- Línea 47: `CONSTRAINT FK_StrategyOperation_Plan FOREIGN KEY(PlanId) REFERENCES crm_strategy.EvaluationPlan(PlanId)`
- Línea 48: `CONSTRAINT FK_StrategyOperation_Task FOREIGN KEY(TaskId) REFERENCES crm_inbox.Task(TaskId)`
- Línea 49: `CONSTRAINT CK_StrategyOperation CHECK(ISJSON(DocumentJson)=1 AND LEFT(LTRIM(DocumentJson),1)=N'{' AND ((Action='task_create' AND Actor='automation' AND PlanId IS NOT NULL AND TaskId IS NOT NULL) OR (Action='feedback' AND Actor='local-operator' AND PlanId IS NOT NULL AND TaskId IS NULL) OR (Action IN ('autonomy','pause') AND Actor='local-operator' AND PlanId IS NULL AND TaskId IS NULL)))`

**Claves foráneas:**

- Línea 46: `CONSTRAINT FK_StrategyOperation_Conversation FOREIGN KEY(ConversationId) REFERENCES crm.Conversation(ConversationId)`
- Línea 47: `CONSTRAINT FK_StrategyOperation_Plan FOREIGN KEY(PlanId) REFERENCES crm_strategy.EvaluationPlan(PlanId)`
- Línea 48: `CONSTRAINT FK_StrategyOperation_Task FOREIGN KEY(TaskId) REFERENCES crm_inbox.Task(TaskId)`

**CREATE INDEX explícitos:**

- `UX_StrategyTaskPlan`: UNIQUE (PlanId) WHERE Action='task_create' · [backend/migrations/009_conversation_strategy.sql:54](../../../backend/migrations/009_conversation_strategy.sql#L54).

**Consumidores literales:** [backend/app/modules/inbox/application/operations.py:190](../../../backend/app/modules/inbox/application/operations.py#L190), [backend/app/modules/conversation_strategy/api/router.py:157](../../../backend/app/modules/conversation_strategy/api/router.py#L157), [backend/app/modules/conversation_events/api/router.py:55](../../../backend/app/modules/conversation_events/api/router.py#L55), [backend/app/modules/contacts/application/activity.py:168](../../../backend/app/modules/contacts/application/activity.py#L168)

## crm_channels.Account

[Declaración 011:12](../../../backend/migrations/011_channels.sql#L12).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| Channel | varchar(12) | No | Channel varchar(12) NOT NULL PRIMARY KEY | 13 |
| Configuration | nvarchar(max) | No | Configuration nvarchar(max) NOT NULL CHECK(ISJSON(Configuration)=1) | 14 |
| State | varchar(24) | No | State varchar(24) NOT NULL DEFAULT 'configured' | 15 |
| Revision | int | No | Revision int NOT NULL DEFAULT 1 | 16 |
| Capabilities | nvarchar(max) | No | Capabilities nvarchar(max) NOT NULL DEFAULT '{}' CHECK(ISJSON(Capabilities)=1) | 17 |
| LastError | varchar(80) | Sí | LastError varchar(80) NULL | 18 |
| VerifiedAt | datetime2 | Sí | VerifiedAt datetime2 NULL | 19 |
| UpdatedAt | datetime2 | No | UpdatedAt datetime2 NOT NULL DEFAULT SYSUTCDATETIME() | 19 |

**Restricciones de tabla:**

- Línea 20: `CHECK(Channel IN('whatsapp','facebook','messenger','instagram','tiktok'))`

**Consumidores literales:** [backend/app/modules/campaigns/service.py:271](../../../backend/app/modules/campaigns/service.py#L271), [backend/app/modules/channels/router.py:219](../../../backend/app/modules/channels/router.py#L219), [backend/app/modules/channels/storage.py:141](../../../backend/app/modules/channels/storage.py#L141), [backend/app/modules/channels/workers.py:304](../../../backend/app/modules/channels/workers.py#L304), [backend/app/modules/webhooks/api/router.py:42](../../../backend/app/modules/webhooks/api/router.py#L42), [backend/app/modules/inbox/application/media.py:84](../../../backend/app/modules/inbox/application/media.py#L84), [backend/app/modules/inbox/application/service.py:251](../../../backend/app/modules/inbox/application/service.py#L251), [backend/app/modules/ai/application/admissions.py:297](../../../backend/app/modules/ai/application/admissions.py#L297)

## crm_channels.Credential

[Declaración 011:22](../../../backend/migrations/011_channels.sql#L22).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| Channel | varchar(12) | No | Channel varchar(12) NOT NULL REFERENCES crm_channels.Account(Channel) | 23 |
| Kind | varchar(24) | No | Kind varchar(24) NOT NULL | 24 |
| KeyId | varchar(32) | No | KeyId varchar(32) NOT NULL | 24 |
| Nonce | binary(12) | No | Nonce binary(12) NOT NULL | 25 |
| Ciphertext | varbinary(max) | No | Ciphertext varbinary(max) NOT NULL | 25 |

**Restricciones de tabla:**

- Línea 26: `PRIMARY KEY(Channel,Kind)`

**Claves foráneas:**

- Línea 23: `Channel varchar(12) NOT NULL REFERENCES crm_channels.Account(Channel)`

**Consumidores literales:** [backend/app/modules/channels/storage.py:72](../../../backend/app/modules/channels/storage.py#L72), [backend/app/modules/webhooks/api/router.py:37](../../../backend/app/modules/webhooks/api/router.py#L37)

## crm_channels.webhook_events

[Declaración 011:28](../../../backend/migrations/011_channels.sql#L28).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| EventId | uniqueidentifier | No | EventId uniqueidentifier NOT NULL PRIMARY KEY | 29 |
| Provider | varchar(12) | No | Provider varchar(12) NOT NULL | 29 |
| Digest | binary(32) | No | Digest binary(32) NOT NULL | 30 |
| Payload | nvarchar(max) | No | Payload nvarchar(max) NOT NULL CHECK(ISJSON(Payload)=1) | 30 |
| State | varchar(16) | No | State varchar(16) NOT NULL DEFAULT 'queued' | 31 |
| Attempts | int | No | Attempts int NOT NULL DEFAULT 0 | 31 |
| DueAt | datetime2 | No | DueAt datetime2 NOT NULL DEFAULT SYSUTCDATETIME() | 32 |
| LeaseId | uniqueidentifier | Sí | LeaseId uniqueidentifier NULL | 32 |
| LastError | varchar(80) | Sí | LastError varchar(80) NULL | 33 |
| ReceivedAt | datetime2 | No | ReceivedAt datetime2 NOT NULL DEFAULT SYSUTCDATETIME() | 33 |

**Restricciones de tabla:**

- Línea 34: `UNIQUE(Provider,Digest)`

**CREATE INDEX explícitos:**

- `IX_Channels_Receipt_Work`: (State,DueAt)  · [backend/migrations/011_channels.sql:36](../../../backend/migrations/011_channels.sql#L36).

**Consumidores literales:** [backend/app/modules/campaigns/evidence.py:49](../../../backend/app/modules/campaigns/evidence.py#L49), [backend/app/modules/channels/receipts.py:63](../../../backend/app/modules/channels/receipts.py#L63), [backend/app/modules/channels/router.py:114](../../../backend/app/modules/channels/router.py#L114), [backend/app/modules/channels/workers.py:532](../../../backend/app/modules/channels/workers.py#L532)

## crm_channels.ExternalIdentity

[Declaración 011:37](../../../backend/migrations/011_channels.sql#L37).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| IdentityId | uniqueidentifier | No | IdentityId uniqueidentifier NOT NULL PRIMARY KEY | 38 |
| Channel | varchar(12) | No | Channel varchar(12) NOT NULL REFERENCES crm_channels.Account(Channel) | 38 |
| ExternalId | nvarchar(128) | No | ExternalId nvarchar(128) NOT NULL | 39 |
| ContactId | uniqueidentifier | No | ContactId uniqueidentifier NOT NULL REFERENCES crm.Contact(ContactId) | 39 |
| ConversationId | uniqueidentifier | No | ConversationId uniqueidentifier NOT NULL REFERENCES crm.Conversation(ConversationId) | 40 |
| LastIncomingAt | datetime2 | Sí | LastIncomingAt datetime2 NULL | 41 |

**Restricciones de tabla:**

- Línea 41: `UNIQUE(Channel,ExternalId)`

**Claves foráneas:**

- Línea 38: `Channel varchar(12) NOT NULL REFERENCES crm_channels.Account(Channel)`
- Línea 39: `ContactId uniqueidentifier NOT NULL REFERENCES crm.Contact(ContactId)`
- Línea 40: `ConversationId uniqueidentifier NOT NULL REFERENCES crm.Conversation(ConversationId)`

**ALTER históricos posteriores (revisar además de CREATE):**

- [backend/migrations/012_channels_identity_collation.sql:20](../../../backend/migrations/012_channels_identity_collation.sql#L20): `ALTER TABLE crm_channels.ExternalIdentity ALTER COLUMN ExternalId nvarchar(128) COLLATE Latin1_General_100_BIN2 NOT NULL`
- [backend/migrations/012_channels_identity_collation.sql:25](../../../backend/migrations/012_channels_identity_collation.sql#L25): `ALTER TABLE crm_channels.ExternalIdentity ADD CONSTRAINT UQ_Channels_Identity UNIQUE(Channel,ExternalId)`

**Consumidores literales:** [backend/app/sql_workspace.py:276](../../../backend/app/sql_workspace.py#L276), [backend/app/modules/campaigns/evidence.py:31](../../../backend/app/modules/campaigns/evidence.py#L31), [backend/app/modules/campaigns/service.py:271](../../../backend/app/modules/campaigns/service.py#L271), [backend/app/modules/channels/router.py:209](../../../backend/app/modules/channels/router.py#L209), [backend/app/modules/channels/workers.py:181](../../../backend/app/modules/channels/workers.py#L181), [backend/app/modules/inbox/application/media.py:497](../../../backend/app/modules/inbox/application/media.py#L497), [backend/app/modules/inbox/application/operations.py:43](../../../backend/app/modules/inbox/application/operations.py#L43), [backend/app/modules/inbox/application/service.py:86](../../../backend/app/modules/inbox/application/service.py#L86), [backend/app/modules/ai/application/admissions.py:296](../../../backend/app/modules/ai/application/admissions.py#L296)

## crm_channels.ExternalMessage

[Declaración 011:43](../../../backend/migrations/011_channels.sql#L43).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| Channel | varchar(12) | No | Channel varchar(12) NOT NULL REFERENCES crm_channels.Account(Channel) | 44 |
| ExternalId | nvarchar(200) | No | ExternalId nvarchar(200) NOT NULL | 44 |
| MessageId | uniqueidentifier | Sí | MessageId uniqueidentifier NULL REFERENCES crm.Message(MessageId) | 45 |
| Payload | nvarchar(max) | No | Payload nvarchar(max) NOT NULL CHECK(ISJSON(Payload)=1) | 46 |

**Restricciones de tabla:**

- Línea 46: `PRIMARY KEY(Channel,ExternalId)`

**Claves foráneas:**

- Línea 44: `Channel varchar(12) NOT NULL REFERENCES crm_channels.Account(Channel)`
- Línea 45: `MessageId uniqueidentifier NULL REFERENCES crm.Message(MessageId)`

**ALTER históricos posteriores (revisar además de CREATE):**

- [backend/migrations/012_channels_identity_collation.sql:21](../../../backend/migrations/012_channels_identity_collation.sql#L21): `ALTER TABLE crm_channels.ExternalMessage ALTER COLUMN ExternalId nvarchar(200) COLLATE Latin1_General_100_BIN2 NOT NULL`
- [backend/migrations/012_channels_identity_collation.sql:26](../../../backend/migrations/012_channels_identity_collation.sql#L26): `ALTER TABLE crm_channels.ExternalMessage ADD CONSTRAINT PK_Channels_ExternalMessage PRIMARY KEY(Channel,ExternalId)`

**Consumidores literales:** [backend/app/modules/campaigns/evidence.py:39](../../../backend/app/modules/campaigns/evidence.py#L39), [backend/app/modules/channels/workers.py:175](../../../backend/app/modules/channels/workers.py#L175), [backend/app/modules/inbox/application/service.py:342](../../../backend/app/modules/inbox/application/service.py#L342)

## crm_channels.outbound_queue

[Declaración 011:48](../../../backend/migrations/011_channels.sql#L48).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| QueueId | uniqueidentifier | No | QueueId uniqueidentifier NOT NULL PRIMARY KEY | 49 |
| Channel | varchar(12) | No | Channel varchar(12) NOT NULL REFERENCES crm_channels.Account(Channel) | 49 |
| IdentityId | uniqueidentifier | Sí | IdentityId uniqueidentifier NULL REFERENCES crm_channels.ExternalIdentity(IdentityId) | 50 |
| MessageId | uniqueidentifier | Sí | MessageId uniqueidentifier NULL REFERENCES crm.Message(MessageId) | 51 |
| Payload | nvarchar(max) | No | Payload nvarchar(max) NOT NULL CHECK(ISJSON(Payload)=1) | 52 |
| State | varchar(16) | No | State varchar(16) NOT NULL DEFAULT 'queued' | 52 |
| Attempts | int | No | Attempts int NOT NULL DEFAULT 0 | 53 |
| DueAt | datetime2 | No | DueAt datetime2 NOT NULL DEFAULT SYSUTCDATETIME() | 53 |
| LeaseId | uniqueidentifier | Sí | LeaseId uniqueidentifier NULL | 54 |
| ExternalId | nvarchar(200) | Sí | ExternalId nvarchar(200) NULL | 54 |
| LastError | varchar(80) | Sí | LastError varchar(80) NULL | 54 |
| CreatedAt | datetime2 | No | CreatedAt datetime2 NOT NULL DEFAULT SYSUTCDATETIME() | 55 |

**Restricciones de tabla:**

- Línea 56: `CHECK(State IN('queued','sending','sent','delivered','read','failed','uncertain'))`

**Claves foráneas:**

- Línea 49: `Channel varchar(12) NOT NULL REFERENCES crm_channels.Account(Channel)`
- Línea 50: `IdentityId uniqueidentifier NULL REFERENCES crm_channels.ExternalIdentity(IdentityId)`
- Línea 51: `MessageId uniqueidentifier NULL REFERENCES crm.Message(MessageId)`

**CREATE INDEX explícitos:**

- `IX_Channels_Outbound_Work`: (State,DueAt)  · [backend/migrations/011_channels.sql:58](../../../backend/migrations/011_channels.sql#L58).
- `IX_Channels_Queue_Message`: UNIQUE (MessageId) WHERE MessageId IS NOT NULL · [backend/migrations/011_channels.sql:59](../../../backend/migrations/011_channels.sql#L59).

**ALTER históricos posteriores (revisar además de CREATE):**

- [backend/migrations/012_channels_identity_collation.sql:22](../../../backend/migrations/012_channels_identity_collation.sql#L22): `ALTER TABLE crm_channels.outbound_queue ALTER COLUMN ExternalId nvarchar(200) COLLATE Latin1_General_100_BIN2 NULL`

**Consumidores literales:** [backend/app/modules/agents/service.py:210](../../../backend/app/modules/agents/service.py#L210), [backend/app/modules/campaigns/evidence.py:40](../../../backend/app/modules/campaigns/evidence.py#L40), [backend/app/modules/channels/router.py:110](../../../backend/app/modules/channels/router.py#L110), [backend/app/modules/channels/workers.py:315](../../../backend/app/modules/channels/workers.py#L315), [backend/app/modules/inbox/application/operations.py:44](../../../backend/app/modules/inbox/application/operations.py#L44), [backend/app/modules/inbox/application/service.py:280](../../../backend/app/modules/inbox/application/service.py#L280), [backend/app/modules/inbox/application/state.py:39](../../../backend/app/modules/inbox/application/state.py#L39), [backend/app/modules/ai/api/admissions.py:135](../../../backend/app/modules/ai/api/admissions.py#L135), [backend/app/modules/ai/application/admissions.py:78](../../../backend/app/modules/ai/application/admissions.py#L78)

## crm_channels.social_comments

[Declaración 011:60](../../../backend/migrations/011_channels.sql#L60).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| CommentId | uniqueidentifier | No | CommentId uniqueidentifier NOT NULL PRIMARY KEY | 61 |
| Channel | varchar(12) | No | Channel varchar(12) NOT NULL REFERENCES crm_channels.Account(Channel) | 61 |
| ExternalId | nvarchar(200) | No | ExternalId nvarchar(200) NOT NULL | 62 |
| AuthorId | nvarchar(128) | No | AuthorId nvarchar(128) NOT NULL | 62 |
| Body | nvarchar(max) | No | Body nvarchar(max) NOT NULL | 62 |
| Payload | nvarchar(max) | No | Payload nvarchar(max) NOT NULL CHECK(ISJSON(Payload)=1) | 63 |
| ReceivedAt | datetime2 | No | ReceivedAt datetime2 NOT NULL DEFAULT SYSUTCDATETIME() | 63 |

**Restricciones de tabla:**

- Línea 64: `UNIQUE(Channel,ExternalId)`

**Claves foráneas:**

- Línea 61: `Channel varchar(12) NOT NULL REFERENCES crm_channels.Account(Channel)`

**ALTER históricos posteriores (revisar además de CREATE):**

- [backend/migrations/012_channels_identity_collation.sql:23](../../../backend/migrations/012_channels_identity_collation.sql#L23): `ALTER TABLE crm_channels.social_comments ALTER COLUMN ExternalId nvarchar(200) COLLATE Latin1_General_100_BIN2 NOT NULL`
- [backend/migrations/012_channels_identity_collation.sql:24](../../../backend/migrations/012_channels_identity_collation.sql#L24): `ALTER TABLE crm_channels.social_comments ALTER COLUMN AuthorId nvarchar(128) COLLATE Latin1_General_100_BIN2 NOT NULL`
- [backend/migrations/012_channels_identity_collation.sql:27](../../../backend/migrations/012_channels_identity_collation.sql#L27): `ALTER TABLE crm_channels.social_comments ADD CONSTRAINT UQ_Channels_Comment UNIQUE(Channel,ExternalId)`

**Consumidores literales:** [backend/app/modules/channels/router.py:209](../../../backend/app/modules/channels/router.py#L209), [backend/app/modules/channels/workers.py:344](../../../backend/app/modules/channels/workers.py#L344)

## crm_channels.Audit

[Declaración 011:66](../../../backend/migrations/011_channels.sql#L66).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| Revision | bigint | No | Revision bigint IDENTITY PRIMARY KEY | 67 |
| Channel | varchar(12) | No | Channel varchar(12) NOT NULL | 67 |
| Action | varchar(40) | No | Action varchar(40) NOT NULL | 68 |
| EntityId | uniqueidentifier | Sí | EntityId uniqueidentifier NULL | 68 |
| CreatedAt | datetime2 | No | CreatedAt datetime2 NOT NULL DEFAULT SYSUTCDATETIME() | 69 |

**Consumidores literales:** [backend/app/sql_workspace.py:223](../../../backend/app/sql_workspace.py#L223), [backend/app/modules/channels/router.py:234](../../../backend/app/modules/channels/router.py#L234), [backend/app/modules/channels/workers.py:292](../../../backend/app/modules/channels/workers.py#L292), [backend/app/modules/ai/application/admissions.py:367](../../../backend/app/modules/ai/application/admissions.py#L367)

## crm_ai.Configuration

[Declaración 013:12](../../../backend/migrations/013_ai_providers.sql#L12).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| ConfigurationId | tinyint | No | ConfigurationId tinyint NOT NULL PRIMARY KEY CHECK(ConfigurationId=1) | 13 |
| Revision | int | No | Revision int NOT NULL CHECK(Revision>=0) | 14 |
| Document | nvarchar(max) | No | Document nvarchar(max) NOT NULL CHECK(ISJSON(Document)=1) | 15 |
| UpdatedAt | datetime2 | No | UpdatedAt datetime2 NOT NULL DEFAULT SYSUTCDATETIME() | 16 |

**Consumidores literales:** [backend/app/modules/ai/application/admissions.py:200](../../../backend/app/modules/ai/application/admissions.py#L200), [backend/app/modules/ai/infrastructure/sql_repository.py:92](../../../backend/app/modules/ai/infrastructure/sql_repository.py#L92)

## crm_ai.Connection

[Declaración 013:18](../../../backend/migrations/013_ai_providers.sql#L18).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| ConnectionId | tinyint | No | ConnectionId tinyint NOT NULL PRIMARY KEY CHECK(ConnectionId=1) | 19 |
| Revision | int | No | Revision int NOT NULL DEFAULT 0 CHECK(Revision>=0) | 20 |
| Outbound | bit | No | Outbound bit NOT NULL DEFAULT 0 | 21 |
| UpdatedAt | datetime2 | No | UpdatedAt datetime2 NOT NULL DEFAULT SYSUTCDATETIME() | 22 |

**Consumidores literales:** [backend/app/modules/ai/application/admissions.py:200](../../../backend/app/modules/ai/application/admissions.py#L200), [backend/app/modules/ai/infrastructure/sql_repository.py:126](../../../backend/app/modules/ai/infrastructure/sql_repository.py#L126)

## crm_ai.Credential

[Declaración 013:24](../../../backend/migrations/013_ai_providers.sql#L24).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| Provider | varchar(24) | No | Provider varchar(24) COLLATE Latin1_General_100_BIN2 NOT NULL PRIMARY KEY | 25 |
| KeyId | varchar(32) | No | KeyId varchar(32) NOT NULL | 26 |
| Nonce | binary(12) | No | Nonce binary(12) NOT NULL | 26 |
| Ciphertext | varbinary(max) | No | Ciphertext varbinary(max) NOT NULL | 26 |
| UpdatedAt | datetime2 | No | UpdatedAt datetime2 NOT NULL DEFAULT SYSUTCDATETIME() | 27 |

**Restricciones de tabla:**

- Línea 28: `CHECK(Provider IN('gemini','groq','mistral','xai','openrouter','elevenlabs','google_tts','tavily','brave','serpapi'))`

**ALTER históricos posteriores (revisar además de CREATE):**

- [backend/migrations/014_ai_provider_catalog.sql:11](../../../backend/migrations/014_ai_provider_catalog.sql#L11): `ALTER TABLE crm_ai.Credential DROP CONSTRAINT '+QUOTENAME(@constraint)`
- [backend/migrations/014_ai_provider_catalog.sql:13](../../../backend/migrations/014_ai_provider_catalog.sql#L13): `ALTER TABLE crm_ai.Credential WITH CHECK ADD CONSTRAINT CK_crm_ai_Credential_Provider CHECK(Provider IN('gemini','nvidia','openai','anthropic','hermes','groq','mistral','openrouter','kimi','xai','elevenlabs','google_tts','tavily','brave','serpapi'))`

**Consumidores literales:** [backend/app/modules/ai/infrastructure/sql_repository.py:61](../../../backend/app/modules/ai/infrastructure/sql_repository.py#L61)

## crm_channels.ConversationProfile

[Declaración 015:11](../../../backend/migrations/015_inbox_unified.sql#L11).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| ConversationId | uniqueidentifier | No | ConversationId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm.Conversation(ConversationId) | 12 |
| LeadScore | tinyint | Sí | LeadScore tinyint NULL CHECK(LeadScore BETWEEN 0 AND 100) | 13 |
| Temperature | varchar(4) | Sí | Temperature varchar(4) NULL CHECK(Temperature IN('cold','warm','hot')) | 14 |
| UpdatedAt | datetime2(7) | No | UpdatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME() | 15 |

**Claves foráneas:**

- Línea 12: `ConversationId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm.Conversation(ConversationId)`

**Consumidores literales:** [backend/app/modules/campaigns/service.py:85](../../../backend/app/modules/campaigns/service.py#L85), [backend/app/modules/inbox/application/service.py:271](../../../backend/app/modules/inbox/application/service.py#L271), [backend/app/modules/inbox/application/state.py:81](../../../backend/app/modules/inbox/application/state.py#L81)

## crm_channels.ConversationControl

[Declaración 015:17](../../../backend/migrations/015_inbox_unified.sql#L17).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| ConversationId | uniqueidentifier | No | ConversationId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm.Conversation(ConversationId) | 18 |
| Epoch | bigint | No | Epoch bigint NOT NULL DEFAULT 0 CHECK(Epoch>=0) | 19 |
| ReadSequence | bigint | No | ReadSequence bigint NOT NULL DEFAULT 0 CHECK(ReadSequence>=0) | 20 |

**Claves foráneas:**

- Línea 18: `ConversationId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm.Conversation(ConversationId)`

**Consumidores literales:** [backend/app/modules/campaigns/service.py:271](../../../backend/app/modules/campaigns/service.py#L271), [backend/app/modules/channels/workers.py:455](../../../backend/app/modules/channels/workers.py#L455), [backend/app/modules/inbox/application/service.py:275](../../../backend/app/modules/inbox/application/service.py#L275), [backend/app/modules/inbox/application/state.py:11](../../../backend/app/modules/inbox/application/state.py#L11), [backend/app/modules/ai/application/admissions.py:295](../../../backend/app/modules/ai/application/admissions.py#L295)

## crm_channels.MessageRoute

[Declaración 015:22](../../../backend/migrations/015_inbox_unified.sql#L22).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| MessageId | uniqueidentifier | No | MessageId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm.Message(MessageId) | 23 |
| IdentityId | uniqueidentifier | No | IdentityId uniqueidentifier NOT NULL REFERENCES crm_channels.ExternalIdentity(IdentityId) | 24 |
| QueueId | uniqueidentifier | Sí | QueueId uniqueidentifier NULL REFERENCES crm_channels.outbound_queue(QueueId) | 25 |
| ActorKind | varchar(8) | No | ActorKind varchar(8) NOT NULL CHECK(ActorKind IN('human','external','bot')) | 26 |
| ControlEpoch | bigint | Sí | ControlEpoch bigint NULL CHECK(ControlEpoch>=0) | 27 |
| StartedAt | datetime2(7) | Sí | StartedAt datetime2(7) NULL | 28 |
| CompletedAt | datetime2(7) | Sí | CompletedAt datetime2(7) NULL | 29 |

**Restricciones de tabla:**

- Línea 30: `CHECK((ActorKind='bot' AND ControlEpoch IS NOT NULL) OR (ActorKind IN('human','external') AND ControlEpoch IS NULL))`

**Claves foráneas:**

- Línea 23: `MessageId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm.Message(MessageId)`
- Línea 24: `IdentityId uniqueidentifier NOT NULL REFERENCES crm_channels.ExternalIdentity(IdentityId)`
- Línea 25: `QueueId uniqueidentifier NULL REFERENCES crm_channels.outbound_queue(QueueId)`

**CREATE INDEX explícitos:**

- `IX_Inbox_MessageRoute_Queue`: UNIQUE (QueueId) WHERE QueueId IS NOT NULL · [backend/migrations/015_inbox_unified.sql:32](../../../backend/migrations/015_inbox_unified.sql#L32).
- `IX_Inbox_MessageRoute_Identity`: (IdentityId,MessageId)  · [backend/migrations/015_inbox_unified.sql:33](../../../backend/migrations/015_inbox_unified.sql#L33).

**Consumidores literales:** [backend/app/modules/agents/service.py:211](../../../backend/app/modules/agents/service.py#L211), [backend/app/modules/campaigns/evidence.py:38](../../../backend/app/modules/campaigns/evidence.py#L38), [backend/app/modules/channels/workers.py:261](../../../backend/app/modules/channels/workers.py#L261), [backend/app/modules/inbox/application/service.py:279](../../../backend/app/modules/inbox/application/service.py#L279), [backend/app/modules/inbox/application/state.py:39](../../../backend/app/modules/inbox/application/state.py#L39), [backend/app/modules/ai/api/admissions.py:135](../../../backend/app/modules/ai/api/admissions.py#L135), [backend/app/modules/ai/application/admissions.py:77](../../../backend/app/modules/ai/application/admissions.py#L77)

## crm_channels.MediaAsset

[Declaración 016:9](../../../backend/migrations/016_inbox_media.sql#L9).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| MediaId | uniqueidentifier | No | MediaId uniqueidentifier NOT NULL PRIMARY KEY | 10 |
| ConversationId | uniqueidentifier | No | ConversationId uniqueidentifier NOT NULL REFERENCES crm.Conversation(ConversationId) | 11 |
| MessageId | uniqueidentifier | Sí | MessageId uniqueidentifier NULL REFERENCES crm.Message(MessageId) | 12 |
| IdentityId | uniqueidentifier | Sí | IdentityId uniqueidentifier NULL REFERENCES crm_channels.ExternalIdentity(IdentityId) | 13 |
| Channel | varchar(12) | Sí | Channel varchar(12) NULL REFERENCES crm_channels.Account(Channel) | 14 |
| SourceKind | varchar(8) | No | SourceKind varchar(8) NOT NULL CHECK(SourceKind IN('upload','provider')) | 15 |
| State | varchar(12) | No | State varchar(12) NOT NULL CHECK(State IN('uploading','pending','processing','ready','rejected','failed','deleted')) | 16 |
| Kind | varchar(8) | Sí | Kind varchar(8) NULL CHECK(Kind IN('image','audio','document')) | 17 |
| FileName | nvarchar(160) | No | FileName nvarchar(160) NOT NULL | 18 |
| ActualMime | varchar(100) | Sí | ActualMime varchar(100) NULL | 19 |
| StorageKey | varchar(40) | Sí | StorageKey varchar(40) NULL | 19 |
| ByteLength | bigint | Sí | ByteLength bigint NULL CHECK(ByteLength>0 AND ByteLength<=5000000) | 20 |
| ContentHash | binary(32) | Sí | ContentHash binary(32) NULL | 21 |
| SourceHash | binary(32) | Sí | SourceHash binary(32) NULL | 21 |
| DurationSeconds | decimal(9,3) | Sí | DurationSeconds decimal(9,3) NULL CHECK(DurationSeconds>0 AND DurationSeconds<=300) | 22 |
| ProviderReference | nvarchar(max) | No | ProviderReference nvarchar(max) NOT NULL DEFAULT '{}' CHECK(ISJSON(ProviderReference)=1) | 23 |
| Attempts | int | No | Attempts int NOT NULL DEFAULT 0 | 24 |
| DueAt | datetime2(7) | No | DueAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME() | 24 |
| LeaseId | uniqueidentifier | Sí | LeaseId uniqueidentifier NULL | 25 |
| LastError | varchar(80) | Sí | LastError varchar(80) NULL | 25 |
| CreatedAt | datetime2(7) | No | CreatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME() | 26 |
| ExpiresAt | datetime2(7) | Sí | ExpiresAt datetime2(7) NULL | 27 |

**Restricciones de tabla:**

- Línea 28: `CHECK(State<>'ready' OR (ActualMime IS NOT NULL AND StorageKey IS NOT NULL AND ByteLength IS NOT NULL AND ContentHash IS NOT NULL AND Kind IS NOT NULL))`
- Línea 29: `CHECK((SourceKind='upload' AND IdentityId IS NULL AND Channel IS NULL) OR (SourceKind='provider' AND IdentityId IS NOT NULL AND Channel IS NOT NULL))`

**Claves foráneas:**

- Línea 11: `ConversationId uniqueidentifier NOT NULL REFERENCES crm.Conversation(ConversationId)`
- Línea 12: `MessageId uniqueidentifier NULL REFERENCES crm.Message(MessageId)`
- Línea 13: `IdentityId uniqueidentifier NULL REFERENCES crm_channels.ExternalIdentity(IdentityId)`
- Línea 14: `Channel varchar(12) NULL REFERENCES crm_channels.Account(Channel)`

**CREATE INDEX explícitos:**

- `IX_InboxMedia_Message`: UNIQUE (MessageId) WHERE MessageId IS NOT NULL · [backend/migrations/016_inbox_media.sql:31](../../../backend/migrations/016_inbox_media.sql#L31).
- `IX_InboxMedia_Work`: (State,DueAt)  · [backend/migrations/016_inbox_media.sql:32](../../../backend/migrations/016_inbox_media.sql#L32).
- `IX_InboxMedia_Conversation`: (ConversationId,CreatedAt)  · [backend/migrations/016_inbox_media.sql:33](../../../backend/migrations/016_inbox_media.sql#L33).

**Consumidores literales:** [backend/app/modules/channels/workers.py:727](../../../backend/app/modules/channels/workers.py#L727), [backend/app/modules/inbox/application/media.py:22](../../../backend/app/modules/inbox/application/media.py#L22), [backend/app/modules/inbox/application/service.py:340](../../../backend/app/modules/inbox/application/service.py#L340)

## crm_ai.AdmissionsPolicy

[Declaración 017:12](../../../backend/migrations/017_ai_admissions.sql#L12).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| PolicyId | tinyint | No | PolicyId tinyint NOT NULL PRIMARY KEY CHECK(PolicyId=1) | 13 |
| Revision | bigint | No | Revision bigint NOT NULL DEFAULT 0 | 13 |
| Enabled | bit | No | Enabled bit NOT NULL DEFAULT 0 | 14 |
| ActivationSequence | bigint | No | ActivationSequence bigint NOT NULL DEFAULT 0 | 14 |
| KnowledgeRevision | bigint | No | KnowledgeRevision bigint NOT NULL DEFAULT 0 | 15 |
| Document | nvarchar(max) | No | Document nvarchar(max) NOT NULL CHECK(ISJSON(Document)=1) | 15 |
| UpdatedAt | datetime2(7) | No | UpdatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME() | 16 |

**Consumidores literales:** [backend/app/modules/channels/workers.py:272](../../../backend/app/modules/channels/workers.py#L272), [backend/app/modules/ai/api/admissions.py:133](../../../backend/app/modules/ai/api/admissions.py#L133), [backend/app/modules/ai/application/admissions.py:56](../../../backend/app/modules/ai/application/admissions.py#L56)

## crm_ai.KnowledgeDocument

[Declaración 017:19](../../../backend/migrations/017_ai_admissions.sql#L19).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| DocumentId | uniqueidentifier | No | DocumentId uniqueidentifier NOT NULL PRIMARY KEY | 20 |
| Title | nvarchar(160) | No | Title nvarchar(160) NOT NULL | 20 |
| FileName | nvarchar(160) | No | FileName nvarchar(160) NOT NULL | 21 |
| ContentHash | binary(32) | No | ContentHash binary(32) NOT NULL | 21 |
| ByteLength | int | No | ByteLength int NOT NULL CHECK(ByteLength BETWEEN 1 AND 5000000) | 21 |
| State | varchar(10) | No | State varchar(10) NOT NULL CHECK(State IN('draft','published','disabled','deleted')) | 22 |
| Revision | bigint | No | Revision bigint NOT NULL DEFAULT 0 | 23 |
| CreatedAt | datetime2(7) | No | CreatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME() | 23 |
| UpdatedAt | datetime2(7) | No | UpdatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME() | 24 |

**Consumidores literales:** [backend/app/modules/agents/operations.py:133](../../../backend/app/modules/agents/operations.py#L133), [backend/app/modules/agents/service.py:253](../../../backend/app/modules/agents/service.py#L253), [backend/app/modules/knowledge/service.py:63](../../../backend/app/modules/knowledge/service.py#L63), [backend/app/modules/ai/api/admissions.py:82](../../../backend/app/modules/ai/api/admissions.py#L82)

## crm_ai.KnowledgeChunk

[Declaración 017:26](../../../backend/migrations/017_ai_admissions.sql#L26).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| ChunkId | uniqueidentifier | No | ChunkId uniqueidentifier NOT NULL PRIMARY KEY | 27 |
| DocumentId | uniqueidentifier | No | DocumentId uniqueidentifier NOT NULL REFERENCES crm_ai.KnowledgeDocument(DocumentId) | 27 |
| Ordinal | int | No | Ordinal int NOT NULL | 28 |
| PageNumber | int | No | PageNumber int NOT NULL | 28 |
| Body | nvarchar(1800) | No | Body nvarchar(1800) NOT NULL | 28 |

**Restricciones de tabla:**

- Línea 29: `UNIQUE(DocumentId,Ordinal)`

**Claves foráneas:**

- Línea 27: `DocumentId uniqueidentifier NOT NULL REFERENCES crm_ai.KnowledgeDocument(DocumentId)`

**Consumidores literales:** [backend/app/modules/agents/operations.py:133](../../../backend/app/modules/agents/operations.py#L133), [backend/app/modules/agents/service.py:253](../../../backend/app/modules/agents/service.py#L253), [backend/app/modules/knowledge/service.py:88](../../../backend/app/modules/knowledge/service.py#L88), [backend/app/modules/ai/api/admissions.py:82](../../../backend/app/modules/ai/api/admissions.py#L82)

## crm_ai.KnowledgeTerm

[Declaración 017:31](../../../backend/migrations/017_ai_admissions.sql#L31).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| Term | nvarchar(64) | No | Term nvarchar(64) COLLATE Latin1_General_100_CI_AI NOT NULL | 32 |
| ChunkId | uniqueidentifier | No | ChunkId uniqueidentifier NOT NULL REFERENCES crm_ai.KnowledgeChunk(ChunkId) | 33 |
| Frequency | smallint | No | Frequency smallint NOT NULL CHECK(Frequency>0) | 33 |

**Restricciones de tabla:**

- Línea 34: `PRIMARY KEY(Term,ChunkId)`

**Claves foráneas:**

- Línea 33: `ChunkId uniqueidentifier NOT NULL REFERENCES crm_ai.KnowledgeChunk(ChunkId)`

**CREATE INDEX explícitos:**

- `IX_KnowledgeTerm_Chunk`: (ChunkId)  · [backend/migrations/017_ai_admissions.sql:36](../../../backend/migrations/017_ai_admissions.sql#L36).

**Consumidores literales:** [backend/app/modules/agents/operations.py:137](../../../backend/app/modules/agents/operations.py#L137), [backend/app/modules/agents/service.py:267](../../../backend/app/modules/agents/service.py#L267), [backend/app/modules/knowledge/service.py:90](../../../backend/app/modules/knowledge/service.py#L90), [backend/app/modules/ai/api/admissions.py:137](../../../backend/app/modules/ai/api/admissions.py#L137)

## crm_ai.ProspectMemory

[Declaración 017:37](../../../backend/migrations/017_ai_admissions.sql#L37).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| ConversationId | uniqueidentifier | No | ConversationId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm.Conversation(ConversationId) | 38 |
| Revision | bigint | No | Revision bigint NOT NULL DEFAULT 0 | 39 |
| Generation | bigint | No | Generation bigint NOT NULL DEFAULT 0 | 39 |
| BaselineSequence | bigint | No | BaselineSequence bigint NOT NULL DEFAULT 0 | 40 |
| Document | nvarchar(max) | No | Document nvarchar(max) NOT NULL DEFAULT '{}' CHECK(ISJSON(Document)=1) | 41 |
| UpdatedAt | datetime2(7) | No | UpdatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME() | 42 |

**Claves foráneas:**

- Línea 38: `ConversationId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm.Conversation(ConversationId)`

**Consumidores literales:** [backend/app/modules/ai/api/admissions.py:145](../../../backend/app/modules/ai/api/admissions.py#L145), [backend/app/modules/ai/application/admissions.py:70](../../../backend/app/modules/ai/application/admissions.py#L70)

## crm_ai.ResponseJob

[Declaración 017:44](../../../backend/migrations/017_ai_admissions.sql#L44).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| MessageId | uniqueidentifier | No | MessageId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm.Message(MessageId) | 45 |
| ConversationId | uniqueidentifier | No | ConversationId uniqueidentifier NOT NULL REFERENCES crm.Conversation(ConversationId) | 46 |
| IdentityId | uniqueidentifier | No | IdentityId uniqueidentifier NOT NULL REFERENCES crm_channels.ExternalIdentity(IdentityId) | 47 |
| State | varchar(12) | No | State varchar(12) NOT NULL DEFAULT 'queued' CHECK(State IN('queued','processing','completed','cancelled','failed','handoff')) | 48 |
| Attempts | int | No | Attempts int NOT NULL DEFAULT 0 | 49 |
| LeaseId | uniqueidentifier | Sí | LeaseId uniqueidentifier NULL | 49 |
| DueAt | datetime2(7) | No | DueAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME() | 50 |
| CreatedAt | datetime2(7) | No | CreatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME() | 50 |
| ResponseMessageId | uniqueidentifier | Sí | ResponseMessageId uniqueidentifier NULL REFERENCES crm.Message(MessageId) | 51 |
| TaskId | uniqueidentifier | Sí | TaskId uniqueidentifier NULL REFERENCES crm_inbox.Task(TaskId) | 52 |
| Result | nvarchar(max) | No | Result nvarchar(max) NOT NULL DEFAULT '{}' CHECK(ISJSON(Result)=1) | 53 |
| LastError | varchar(80) | Sí | LastError varchar(80) NULL | 53 |

**Claves foráneas:**

- Línea 45: `MessageId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm.Message(MessageId)`
- Línea 46: `ConversationId uniqueidentifier NOT NULL REFERENCES crm.Conversation(ConversationId)`
- Línea 47: `IdentityId uniqueidentifier NOT NULL REFERENCES crm_channels.ExternalIdentity(IdentityId)`
- Línea 51: `ResponseMessageId uniqueidentifier NULL REFERENCES crm.Message(MessageId)`
- Línea 52: `TaskId uniqueidentifier NULL REFERENCES crm_inbox.Task(TaskId)`

**CREATE INDEX explícitos:**

- `IX_AdmissionsJob_Work`: (State,DueAt)  · [backend/migrations/017_ai_admissions.sql:55](../../../backend/migrations/017_ai_admissions.sql#L55).

**Consumidores literales:** [backend/app/modules/agents/router.py:179](../../../backend/app/modules/agents/router.py#L179), [backend/app/modules/agents/service.py:210](../../../backend/app/modules/agents/service.py#L210), [backend/app/modules/campaigns/evidence.py:41](../../../backend/app/modules/campaigns/evidence.py#L41), [backend/app/modules/channels/workers.py:274](../../../backend/app/modules/channels/workers.py#L274), [backend/app/modules/inbox/application/operations.py:186](../../../backend/app/modules/inbox/application/operations.py#L186), [backend/app/modules/ai/api/admissions.py:135](../../../backend/app/modules/ai/api/admissions.py#L135), [backend/app/modules/ai/application/admissions.py:122](../../../backend/app/modules/ai/application/admissions.py#L122)

## crm_marketing.ChurnAssessment

[Declaración 018:16](../../../backend/migrations/018_campaigns.sql#L16).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| AssessmentId | uniqueidentifier | No | AssessmentId uniqueidentifier NOT NULL PRIMARY KEY | 17 |
| ConversationId | uniqueidentifier | No | ConversationId uniqueidentifier NOT NULL REFERENCES crm.Conversation(ConversationId) | 18 |
| IdentityId | uniqueidentifier | Sí | IdentityId uniqueidentifier NULL REFERENCES crm_channels.ExternalIdentity(IdentityId) | 19 |
| AsOfUtc | datetime2(7) | No | AsOfUtc datetime2(7) NOT NULL | 20 |
| InputSequence | bigint | Sí | InputSequence bigint NULL CHECK(InputSequence>0) | 20 |
| FormulaVersion | varchar(40) | No | FormulaVersion varchar(40) NOT NULL | 21 |
| ComputedLeadScore | tinyint | Sí | ComputedLeadScore tinyint NULL CHECK(ComputedLeadScore BETWEEN 0 AND 100) | 22 |
| LeadReasonsJson | nvarchar(max) | No | LeadReasonsJson nvarchar(max) NOT NULL DEFAULT '[]' CHECK(ISJSON(LeadReasonsJson)=1) | 23 |
| Status | varchar(16) | No | Status varchar(16) NOT NULL CHECK(Status IN('known','unknown','not_applicable')) | 24 |
| RiskScore | tinyint | Sí | RiskScore tinyint NULL | 25 |
| RiskLevel | varchar(16) | No | RiskLevel varchar(16) NOT NULL | 25 |
| StageSnapshot | nvarchar(60) | Sí | StageSnapshot nvarchar(60) COLLATE Latin1_General_100_BIN2 NULL | 26 |
| WaitingSinceUtc | datetime2(7) | Sí | WaitingSinceUtc datetime2(7) NULL | 27 |
| ReasonsJson | nvarchar(max) | No | ReasonsJson nvarchar(max) NOT NULL CHECK(ISJSON(ReasonsJson)=1 AND LEFT(LTRIM(ReasonsJson),1)=N'[') | 28 |
| EvidenceJson | nvarchar(max) | No | EvidenceJson nvarchar(max) NOT NULL CHECK(ISJSON(EvidenceJson)=1 AND LEFT(LTRIM(EvidenceJson),1)=N'{') | 29 |
| CreatedAtUtc | datetime2(7) | No | CreatedAtUtc datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME() | 30 |

**Restricciones de tabla:**

- Línea 31: `CHECK((Status='known' AND IdentityId IS NOT NULL AND StageSnapshot IS NOT NULL AND InputSequence IS NOT NULL AND RiskScore IS NOT NULL AND RiskScore BETWEEN 0 AND 100 AND WaitingSinceUtc IS NOT NULL AND ((RiskScore<35 AND RiskLevel='low') OR (RiskScore BETWEEN 35 AND 69 AND RiskLevel='medium') OR (RiskScore>=70 AND RiskLevel='high'))) OR (Status='unknown' AND RiskScore IS NULL AND RiskLevel='unknown') OR (Status='not_applicable' AND RiskScore IS NULL AND RiskLevel='not_applicable'))`
- Línea 35: `CHECK(WaitingSinceUtc IS NULL OR WaitingSinceUtc<=AsOfUtc)`
- Línea 36: `UNIQUE(ConversationId,IdentityId,AsOfUtc,FormulaVersion,InputSequence)`

**Claves foráneas:**

- Línea 18: `ConversationId uniqueidentifier NOT NULL REFERENCES crm.Conversation(ConversationId)`
- Línea 19: `IdentityId uniqueidentifier NULL REFERENCES crm_channels.ExternalIdentity(IdentityId)`

**CREATE INDEX explícitos:**

- `IX_Marketing_Churn_Recent`: (ConversationId,AsOfUtc DESC)  · [backend/migrations/018_campaigns.sql:38](../../../backend/migrations/018_campaigns.sql#L38).

**ALTER históricos posteriores (revisar además de CREATE):**

- [backend/migrations/018_campaigns.sql:172](../../../backend/migrations/018_campaigns.sql#L172): `ALTER TABLE crm_marketing.ChurnAssessment ADD RunId uniqueidentifier NULL REFERENCES crm_marketing.EvaluationRun(RunId)`

**Consumidores literales:** [backend/app/modules/campaigns/service.py:86](../../../backend/app/modules/campaigns/service.py#L86)

## crm_marketing.MessageTemplate

[Declaración 018:40](../../../backend/migrations/018_campaigns.sql#L40).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| TemplateId | uniqueidentifier | No | TemplateId uniqueidentifier NOT NULL PRIMARY KEY | 41 |
| Channel | varchar(12) | No | Channel varchar(12) NOT NULL REFERENCES crm_channels.Account(Channel) | 42 |
| AccountScope | nvarchar(128) | No | AccountScope nvarchar(128) NOT NULL | 43 |
| AccountRevision | int | No | AccountRevision int NOT NULL CHECK(AccountRevision>0) | 44 |
| ProviderTemplateId | nvarchar(128) | No | ProviderTemplateId nvarchar(128) NOT NULL | 45 |
| Name | nvarchar(128) | No | Name nvarchar(128) NOT NULL | 46 |
| Language | varchar(20) | No | Language varchar(20) NOT NULL | 46 |
| Status | varchar(16) | No | Status varchar(16) NOT NULL DEFAULT 'unknown' CHECK(Status IN('unknown','pending','approved','rejected','paused','disabled','deleted')) | 47 |
| Version | bigint | No | Version bigint NOT NULL CHECK(Version>0) | 48 |
| StatusRevision | bigint | No | StatusRevision bigint NOT NULL DEFAULT 0 CHECK(StatusRevision>=0) | 48 |
| ComponentsJson | nvarchar(max) | No | ComponentsJson nvarchar(max) NOT NULL CHECK(ISJSON(ComponentsJson)=1 AND LEFT(LTRIM(ComponentsJson),1)=N'[') | 49 |
| SyncedAtUtc | datetime2(7) | Sí | SyncedAtUtc datetime2(7) NULL | 50 |

**Restricciones de tabla:**

- Línea 51: `UNIQUE(Channel,AccountScope,ProviderTemplateId,Version)`
- Línea 52: `UNIQUE(Channel,AccountScope,Name,Language,Version)`
- Línea 53: `UNIQUE(TemplateId,Version,Channel,AccountScope)`
- Línea 54: `CHECK(LEN(LTRIM(RTRIM(AccountScope)))>0 AND LEN(LTRIM(RTRIM(Name)))>0 AND LEN(Language)>0)`

**Claves foráneas:**

- Línea 42: `Channel varchar(12) NOT NULL REFERENCES crm_channels.Account(Channel)`

**Consumidores literales:** [backend/app/modules/campaigns/service.py:119](../../../backend/app/modules/campaigns/service.py#L119)

## crm_marketing.ContactConsent

[Declaración 018:57](../../../backend/migrations/018_campaigns.sql#L57).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| ConsentId | uniqueidentifier | No | ConsentId uniqueidentifier NOT NULL PRIMARY KEY | 58 |
| IdentityId | uniqueidentifier | No | IdentityId uniqueidentifier NOT NULL REFERENCES crm_channels.ExternalIdentity(IdentityId) | 59 |
| Channel | varchar(12) | No | Channel varchar(12) NOT NULL REFERENCES crm_channels.Account(Channel) | 60 |
| AccountScope | nvarchar(128) | No | AccountScope nvarchar(128) NOT NULL | 60 |
| Purpose | varchar(24) | No | Purpose varchar(24) NOT NULL CHECK(Purpose IN('marketing','service')) | 61 |
| Status | varchar(10) | No | Status varchar(10) NOT NULL DEFAULT 'unknown' CHECK(Status IN('unknown','granted','revoked','expired')) | 62 |
| Version | bigint | No | Version bigint NOT NULL CHECK(Version>0) | 63 |
| RevokesVersion | bigint | Sí | RevokesVersion bigint NULL | 63 |
| EvidenceJson | nvarchar(max) | No | EvidenceJson nvarchar(max) NOT NULL CHECK(ISJSON(EvidenceJson)=1 AND LEFT(LTRIM(EvidenceJson),1)=N'{') | 64 |
| DecisionAtUtc | datetime2(7) | Sí | DecisionAtUtc datetime2(7) NULL | 65 |
| ExpiresAtUtc | datetime2(7) | Sí | ExpiresAtUtc datetime2(7) NULL | 65 |
| CreatedAtUtc | datetime2(7) | No | CreatedAtUtc datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME() | 66 |

**Restricciones de tabla:**

- Línea 67: `UNIQUE(IdentityId,Channel,AccountScope,Purpose,Version)`
- Línea 68: `UNIQUE(ConsentId,Version)`
- Línea 69: `FOREIGN KEY(IdentityId,Channel,AccountScope,Purpose,RevokesVersion) REFERENCES crm_marketing.ContactConsent(IdentityId,Channel,AccountScope,Purpose,Version)`
- Línea 71: `CHECK(RevokesVersion IS NULL OR (Status='revoked' AND RevokesVersion<Version))`
- Línea 72: `CHECK(Status='unknown' OR DecisionAtUtc IS NOT NULL)`
- Línea 73: `CHECK(ExpiresAtUtc IS NULL OR (DecisionAtUtc IS NOT NULL AND ExpiresAtUtc>DecisionAtUtc))`

**Claves foráneas:**

- Línea 59: `IdentityId uniqueidentifier NOT NULL REFERENCES crm_channels.ExternalIdentity(IdentityId)`
- Línea 60: `Channel varchar(12) NOT NULL REFERENCES crm_channels.Account(Channel)`
- Línea 69: `FOREIGN KEY(IdentityId,Channel,AccountScope,Purpose,RevokesVersion) REFERENCES crm_marketing.ContactConsent(IdentityId,Channel,AccountScope,Purpose,Version)`

**CREATE INDEX explícitos:**

- `IX_Marketing_Consent_Current`: (IdentityId,Channel,AccountScope,Purpose,Version DESC)  · [backend/migrations/018_campaigns.sql:75](../../../backend/migrations/018_campaigns.sql#L75).

**Consumidores literales:** [backend/app/modules/campaigns/service.py:298](../../../backend/app/modules/campaigns/service.py#L298)

## crm_marketing.RemarketingRule

[Declaración 018:77](../../../backend/migrations/018_campaigns.sql#L77).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| RuleId | uniqueidentifier | No | RuleId uniqueidentifier NOT NULL PRIMARY KEY | 78 |
| Name | nvarchar(160) | No | Name nvarchar(160) NOT NULL | 78 |
| StageValue | nvarchar(60) | No | StageValue nvarchar(60) COLLATE Latin1_General_100_BIN2 NOT NULL | 79 |
| Channel | varchar(12) | Sí | Channel varchar(12) NULL REFERENCES crm_channels.Account(Channel) | 80 |
| AccountScope | nvarchar(128) | Sí | AccountScope nvarchar(128) NULL | 80 |
| TemplateId | uniqueidentifier | Sí | TemplateId uniqueidentifier NULL | 81 |
| TemplateVersion | bigint | Sí | TemplateVersion bigint NULL | 81 |
| InactivityDays | smallint | No | InactivityDays smallint NOT NULL CHECK(InactivityDays BETWEEN 1 AND 3650) | 82 |
| CooldownHours | int | No | CooldownHours int NOT NULL CHECK(CooldownHours BETWEEN 1 AND 87600) | 83 |
| MinimumRisk | tinyint | No | MinimumRisk tinyint NOT NULL DEFAULT 70 CHECK(MinimumRisk BETWEEN 0 AND 100) | 84 |
| Enabled | bit | No | Enabled bit NOT NULL DEFAULT 0 | 85 |
| Revision | bigint | No | Revision bigint NOT NULL DEFAULT 0 CHECK(Revision>=0) | 85 |
| NextEvaluationAtUtc | datetime2(7) | No | NextEvaluationAtUtc datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME() | 86 |
| CreatedAtUtc | datetime2(7) | No | CreatedAtUtc datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME() | 87 |
| UpdatedAtUtc | datetime2(7) | No | UpdatedAtUtc datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME() | 87 |

**Restricciones de tabla:**

- Línea 88: `FOREIGN KEY(TemplateId,TemplateVersion,Channel,AccountScope) REFERENCES crm_marketing.MessageTemplate(TemplateId,Version,Channel,AccountScope)`
- Línea 90: `CHECK(LEN(LTRIM(RTRIM(StageValue)))>0)`
- Línea 91: `CHECK((TemplateId IS NULL AND TemplateVersion IS NULL) OR (TemplateId IS NOT NULL AND TemplateVersion IS NOT NULL))`
- Línea 92: `CHECK(Enabled=0 OR (TemplateId IS NOT NULL AND Channel IS NOT NULL AND AccountScope IS NOT NULL))`

**Claves foráneas:**

- Línea 80: `Channel varchar(12) NULL REFERENCES crm_channels.Account(Channel)`
- Línea 88: `FOREIGN KEY(TemplateId,TemplateVersion,Channel,AccountScope) REFERENCES crm_marketing.MessageTemplate(TemplateId,Version,Channel,AccountScope)`

**Consumidores literales:** [backend/app/modules/campaigns/service.py:108](../../../backend/app/modules/campaigns/service.py#L108)

## crm_marketing.AccountCadence

[Declaración 018:96](../../../backend/migrations/018_campaigns.sql#L96).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| Channel | varchar(12) | No | Channel varchar(12) NOT NULL REFERENCES crm_channels.Account(Channel) | 97 |
| AccountScope | nvarchar(128) | No | AccountScope nvarchar(128) NOT NULL | 97 |
| MinIntervalSeconds | int | No | MinIntervalSeconds int NOT NULL CHECK(MinIntervalSeconds BETWEEN 1 AND 86400) | 98 |
| DailyRecipientLimit | int | No | DailyRecipientLimit int NOT NULL CHECK(DailyRecipientLimit BETWEEN 1 AND 100000) | 99 |
| WindowStartedAtUtc | datetime2(7) | No | WindowStartedAtUtc datetime2(7) NOT NULL | 100 |
| ReservedInWindow | int | No | ReservedInWindow int NOT NULL DEFAULT 0 CHECK(ReservedInWindow>=0) | 100 |
| NextAllowedAtUtc | datetime2(7) | No | NextAllowedAtUtc datetime2(7) NOT NULL | 101 |
| Revision | bigint | No | Revision bigint NOT NULL DEFAULT 0 CHECK(Revision>=0) | 101 |
| LeaseId | uniqueidentifier | Sí | LeaseId uniqueidentifier NULL | 102 |
| LeaseUntilUtc | datetime2(7) | Sí | LeaseUntilUtc datetime2(7) NULL | 102 |

**Restricciones de tabla:**

- Línea 103: `PRIMARY KEY(Channel,AccountScope)`
- Línea 104: `CHECK((LeaseId IS NULL AND LeaseUntilUtc IS NULL) OR (LeaseId IS NOT NULL AND LeaseUntilUtc IS NOT NULL))`

**Claves foráneas:**

- Línea 97: `Channel varchar(12) NOT NULL REFERENCES crm_channels.Account(Channel)`

**Consumidores literales:** [backend/app/modules/campaigns/service.py:229](../../../backend/app/modules/campaigns/service.py#L229)

## crm_marketing.Campaign

[Declaración 018:107](../../../backend/migrations/018_campaigns.sql#L107).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| CampaignId | uniqueidentifier | No | CampaignId uniqueidentifier NOT NULL PRIMARY KEY | 108 |
| Name | nvarchar(160) | No | Name nvarchar(160) NOT NULL | 108 |
| Kind | varchar(12) | No | Kind varchar(12) NOT NULL CHECK(Kind IN('bulk','remarketing')) | 109 |
| Status | varchar(12) | No | Status varchar(12) NOT NULL DEFAULT 'draft' CHECK(Status IN('draft','scheduled','running','paused','completed','cancelled')) | 110 |
| Channel | varchar(12) | Sí | Channel varchar(12) NULL | 111 |
| AccountScope | nvarchar(128) | Sí | AccountScope nvarchar(128) NULL | 111 |
| TemplateId | uniqueidentifier | Sí | TemplateId uniqueidentifier NULL | 112 |
| TemplateVersion | bigint | Sí | TemplateVersion bigint NULL | 112 |
| RuleId | uniqueidentifier | Sí | RuleId uniqueidentifier NULL REFERENCES crm_marketing.RemarketingRule(RuleId) | 113 |
| SegmentJson | nvarchar(max) | No | SegmentJson nvarchar(max) NOT NULL CHECK(ISJSON(SegmentJson)=1 AND LEFT(LTRIM(SegmentJson),1)=N'{') | 114 |
| ScheduledAtUtc | datetime2(7) | Sí | ScheduledAtUtc datetime2(7) NULL | 115 |
| PausedAtUtc | datetime2(7) | Sí | PausedAtUtc datetime2(7) NULL | 115 |
| LastPreparedAtUtc | datetime2(7) | Sí | LastPreparedAtUtc datetime2(7) NULL | 115 |
| Revision | bigint | No | Revision bigint NOT NULL DEFAULT 0 CHECK(Revision>=0) | 116 |
| InclusionEpoch | bigint | No | InclusionEpoch bigint NOT NULL DEFAULT 0 CHECK(InclusionEpoch>=0) | 116 |
| CreatedAtUtc | datetime2(7) | No | CreatedAtUtc datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME() | 117 |
| UpdatedAtUtc | datetime2(7) | No | UpdatedAtUtc datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME() | 117 |

**Restricciones de tabla:**

- Línea 118: `FOREIGN KEY(Channel,AccountScope) REFERENCES crm_marketing.AccountCadence(Channel,AccountScope)`
- Línea 119: `FOREIGN KEY(TemplateId,TemplateVersion,Channel,AccountScope) REFERENCES crm_marketing.MessageTemplate(TemplateId,Version,Channel,AccountScope)`
- Línea 121: `UNIQUE(CampaignId,Channel,AccountScope)`
- Línea 122: `CHECK((Kind='bulk' AND RuleId IS NULL) OR (Kind='remarketing' AND RuleId IS NOT NULL))`
- Línea 123: `CHECK((TemplateId IS NULL AND TemplateVersion IS NULL) OR (TemplateId IS NOT NULL AND TemplateVersion IS NOT NULL))`
- Línea 124: `CHECK(Status NOT IN('scheduled','running') OR (ScheduledAtUtc IS NOT NULL AND TemplateId IS NOT NULL AND Channel IS NOT NULL AND AccountScope IS NOT NULL))`

**Claves foráneas:**

- Línea 113: `RuleId uniqueidentifier NULL REFERENCES crm_marketing.RemarketingRule(RuleId)`
- Línea 118: `FOREIGN KEY(Channel,AccountScope) REFERENCES crm_marketing.AccountCadence(Channel,AccountScope)`
- Línea 119: `FOREIGN KEY(TemplateId,TemplateVersion,Channel,AccountScope) REFERENCES crm_marketing.MessageTemplate(TemplateId,Version,Channel,AccountScope)`

**CREATE INDEX explícitos:**

- `IX_Marketing_Campaign_Due`: (Status,ScheduledAtUtc)  · [backend/migrations/018_campaigns.sql:126](../../../backend/migrations/018_campaigns.sql#L126).

**Consumidores literales:** [backend/app/modules/agents/runtime.py:107](../../../backend/app/modules/agents/runtime.py#L107), [backend/app/modules/campaigns/service.py:106](../../../backend/app/modules/campaigns/service.py#L106)

## crm_marketing.CampaignRecipient

[Declaración 018:129](../../../backend/migrations/018_campaigns.sql#L129).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| RecipientId | uniqueidentifier | No | RecipientId uniqueidentifier NOT NULL PRIMARY KEY | 130 |
| CampaignId | uniqueidentifier | No | CampaignId uniqueidentifier NOT NULL | 131 |
| Channel | varchar(12) | No | Channel varchar(12) NOT NULL | 131 |
| AccountScope | nvarchar(128) | Sí | AccountScope nvarchar(128) NULL | 131 |
| IdentityId | uniqueidentifier | No | IdentityId uniqueidentifier NOT NULL REFERENCES crm_channels.ExternalIdentity(IdentityId) | 132 |
| ContactId | uniqueidentifier | No | ContactId uniqueidentifier NOT NULL REFERENCES crm.Contact(ContactId) | 133 |
| ConversationId | uniqueidentifier | No | ConversationId uniqueidentifier NOT NULL REFERENCES crm.Conversation(ConversationId) | 134 |
| Status | varchar(12) | No | Status varchar(12) NOT NULL DEFAULT 'pending' CHECK(Status IN('pending','prepared','blocked','leased','queued','sent','delivered','read','failed','uncertain','cancelled')) | 135 |
| QueueId | uniqueidentifier | Sí | QueueId uniqueidentifier NULL REFERENCES crm_channels.outbound_queue(QueueId) | 137 |
| ConsentId | uniqueidentifier | Sí | ConsentId uniqueidentifier NULL | 138 |
| ConsentVersion | bigint | Sí | ConsentVersion bigint NULL | 138 |
| CampaignRevision | bigint | No | CampaignRevision bigint NOT NULL CHECK(CampaignRevision>=0) | 139 |
| RuleRevision | bigint | Sí | RuleRevision bigint NULL CHECK(RuleRevision>=0) | 139 |
| AccountRevision | int | No | AccountRevision int NOT NULL CHECK(AccountRevision>0) | 140 |
| ControlEpoch | bigint | No | ControlEpoch bigint NOT NULL CHECK(ControlEpoch>=0) | 140 |
| InclusionEpoch | bigint | No | InclusionEpoch bigint NOT NULL CHECK(InclusionEpoch>=0) | 141 |
| InputSequence | bigint | No | InputSequence bigint NOT NULL CHECK(InputSequence>=0) | 141 |
| EvidenceJson | nvarchar(max) | No | EvidenceJson nvarchar(max) NOT NULL CHECK(ISJSON(EvidenceJson)=1 AND LEFT(LTRIM(EvidenceJson),1)=N'{') | 142 |
| DueAtUtc | datetime2(7) | No | DueAtUtc datetime2(7) NOT NULL | 143 |
| Attempts | int | No | Attempts int NOT NULL DEFAULT 0 CHECK(Attempts BETWEEN 0 AND 20) | 143 |
| LeaseId | uniqueidentifier | Sí | LeaseId uniqueidentifier NULL | 144 |
| LeaseUntilUtc | datetime2(7) | Sí | LeaseUntilUtc datetime2(7) NULL | 144 |
| LastError | varchar(80) | Sí | LastError varchar(80) NULL | 145 |
| CreatedAtUtc | datetime2(7) | No | CreatedAtUtc datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME() | 146 |
| UpdatedAtUtc | datetime2(7) | No | UpdatedAtUtc datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME() | 146 |

**Restricciones de tabla:**

- Línea 147: `FOREIGN KEY(CampaignId) REFERENCES crm_marketing.Campaign(CampaignId)`
- Línea 148: `FOREIGN KEY(CampaignId,Channel,AccountScope) REFERENCES crm_marketing.Campaign(CampaignId,Channel,AccountScope)`
- Línea 149: `FOREIGN KEY(ConsentId,ConsentVersion) REFERENCES crm_marketing.ContactConsent(ConsentId,Version)`
- Línea 150: `UNIQUE(CampaignId,IdentityId)`
- Línea 151: `CHECK((ConsentId IS NULL AND ConsentVersion IS NULL) OR (ConsentId IS NOT NULL AND ConsentVersion IS NOT NULL))`
- Línea 152: `CHECK(Status NOT IN('queued','sent','delivered','read','uncertain') OR (QueueId IS NOT NULL AND ConsentId IS NOT NULL))`
- Línea 153: `CHECK((Status='leased' AND LeaseId IS NOT NULL AND LeaseUntilUtc IS NOT NULL) OR (Status<>'leased' AND LeaseId IS NULL AND LeaseUntilUtc IS NULL))`

**Claves foráneas:**

- Línea 132: `IdentityId uniqueidentifier NOT NULL REFERENCES crm_channels.ExternalIdentity(IdentityId)`
- Línea 133: `ContactId uniqueidentifier NOT NULL REFERENCES crm.Contact(ContactId)`
- Línea 134: `ConversationId uniqueidentifier NOT NULL REFERENCES crm.Conversation(ConversationId)`
- Línea 137: `QueueId uniqueidentifier NULL REFERENCES crm_channels.outbound_queue(QueueId)`
- Línea 147: `FOREIGN KEY(CampaignId) REFERENCES crm_marketing.Campaign(CampaignId)`
- Línea 148: `FOREIGN KEY(CampaignId,Channel,AccountScope) REFERENCES crm_marketing.Campaign(CampaignId,Channel,AccountScope)`
- Línea 149: `FOREIGN KEY(ConsentId,ConsentVersion) REFERENCES crm_marketing.ContactConsent(ConsentId,Version)`

**CREATE INDEX explícitos:**

- `IX_Marketing_Recipient_Queue`: UNIQUE (QueueId) WHERE QueueId IS NOT NULL · [backend/migrations/018_campaigns.sql:156](../../../backend/migrations/018_campaigns.sql#L156).
- `IX_Marketing_Recipient_Due`: (Status,DueAtUtc)  · [backend/migrations/018_campaigns.sql:157](../../../backend/migrations/018_campaigns.sql#L157).
- `IX_Marketing_Recipient_Identity`: (IdentityId,UpdatedAtUtc DESC)  · [backend/migrations/018_campaigns.sql:158](../../../backend/migrations/018_campaigns.sql#L158).

**Consumidores literales:** [backend/app/modules/campaigns/service.py:213](../../../backend/app/modules/campaigns/service.py#L213), [backend/app/modules/campaigns/transport.py:9](../../../backend/app/modules/campaigns/transport.py#L9)

## crm_marketing.EvaluationRun

[Declaración 018:159](../../../backend/migrations/018_campaigns.sql#L159).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| RunId | uniqueidentifier | No | RunId uniqueidentifier NOT NULL PRIMARY KEY | 160 |
| Kind | varchar(16) | No | Kind varchar(16) NOT NULL CHECK(Kind IN('predictions','remarketing','preparation')) | 161 |
| TriggerKind | varchar(8) | No | TriggerKind varchar(8) NOT NULL CHECK(TriggerKind IN('manual','worker')) | 162 |
| RuleId | uniqueidentifier | Sí | RuleId uniqueidentifier NULL REFERENCES crm_marketing.RemarketingRule(RuleId) | 163 |
| CampaignId | uniqueidentifier | Sí | CampaignId uniqueidentifier NULL REFERENCES crm_marketing.Campaign(CampaignId) | 164 |
| State | varchar(12) | No | State varchar(12) NOT NULL DEFAULT 'queued' CHECK(State IN('queued','processing','completed','failed')) | 165 |
| DueAtUtc | datetime2(7) | No | DueAtUtc datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME() | 166 |
| RequestedAtUtc | datetime2(7) | No | RequestedAtUtc datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME() | 166 |
| StartedAtUtc | datetime2(7) | Sí | StartedAtUtc datetime2(7) NULL | 167 |
| CompletedAtUtc | datetime2(7) | Sí | CompletedAtUtc datetime2(7) NULL | 167 |
| LeaseId | uniqueidentifier | Sí | LeaseId uniqueidentifier NULL | 168 |
| LeaseUntilUtc | datetime2(7) | Sí | LeaseUntilUtc datetime2(7) NULL | 168 |
| Attempts | int | No | Attempts int NOT NULL DEFAULT 0 CHECK(Attempts BETWEEN 0 AND 3) | 168 |
| CountsJson | nvarchar(max) | No | CountsJson nvarchar(max) NOT NULL DEFAULT '{}' CHECK(ISJSON(CountsJson)=1) | 169 |
| LastError | varchar(80) | Sí | LastError varchar(80) NULL | 169 |

**Claves foráneas:**

- Línea 163: `RuleId uniqueidentifier NULL REFERENCES crm_marketing.RemarketingRule(RuleId)`
- Línea 164: `CampaignId uniqueidentifier NULL REFERENCES crm_marketing.Campaign(CampaignId)`

**CREATE INDEX explícitos:**

- `IX_Marketing_Run_Due`: (State,DueAtUtc)  · [backend/migrations/018_campaigns.sql:171](../../../backend/migrations/018_campaigns.sql#L171).

**Consumidores literales:** [backend/app/modules/campaigns/service.py:60](../../../backend/app/modules/campaigns/service.py#L60)

## crm_marketing.Policy

[Declaración 018:173](../../../backend/migrations/018_campaigns.sql#L173).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| PolicyId | tinyint | No | PolicyId tinyint NOT NULL PRIMARY KEY CHECK(PolicyId=1) | 174 |
| Revision | bigint | No | Revision bigint NOT NULL DEFAULT 0 CHECK(Revision>=0) | 174 |
| StageWeightsJson | nvarchar(max) | No | StageWeightsJson nvarchar(max) NOT NULL DEFAULT '{}' CHECK(ISJSON(StageWeightsJson)=1) | 175 |
| EvaluationEnabled | bit | No | EvaluationEnabled bit NOT NULL DEFAULT 1 | 176 |
| IntervalMinutes | int | No | IntervalMinutes int NOT NULL DEFAULT 60 CHECK(IntervalMinutes BETWEEN 1 AND 1440) | 176 |
| NextRunAtUtc | datetime2(7) | No | NextRunAtUtc datetime2(7) NOT NULL DEFAULT DATEADD(minute,60,SYSUTCDATETIME()) | 177 |
| UpdatedAtUtc | datetime2(7) | No | UpdatedAtUtc datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME() | 177 |

**Consumidores literales:** [backend/app/modules/campaigns/service.py:59](../../../backend/app/modules/campaigns/service.py#L59)

## crm_agents.Stage

[Declaración 019:13](../../../backend/migrations/019_admissions_agents.sql#L13).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| StageId | uniqueidentifier | No | StageId uniqueidentifier NOT NULL PRIMARY KEY | 14 |
| ProgramId | int | No | ProgramId int NOT NULL | 14 |
| Name | nvarchar(100) | No | Name nvarchar(100) NOT NULL | 15 |
| EntryRule | nvarchar(1000) | No | EntryRule nvarchar(1000) NOT NULL | 15 |
| ExitRule | nvarchar(1000) | No | ExitRule nvarchar(1000) NOT NULL | 15 |
| EvidenceRequired | nvarchar(1000) | No | EvidenceRequired nvarchar(1000) NOT NULL | 16 |
| Revision | bigint | No | Revision bigint NOT NULL CHECK(Revision>0) | 16 |
| ApprovedRevision | bigint | Sí | ApprovedRevision bigint NULL | 17 |
| ApprovedAt | datetime2(7) | Sí | ApprovedAt datetime2(7) NULL | 17 |

**Restricciones de tabla:**

- Línea 18: `UNIQUE(ProgramId,Name)`
- Línea 18: `UNIQUE(StageId,ProgramId)`
- Línea 18: `CHECK(ApprovedRevision IS NULL OR ApprovedRevision=Revision)`

**Consumidores literales:** [backend/app/modules/agents/service.py:115](../../../backend/app/modules/agents/service.py#L115)

## crm_agents.Profile

[Declaración 019:20](../../../backend/migrations/019_admissions_agents.sql#L20).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| AgentId | uniqueidentifier | No | AgentId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm_inbox.Agent(AgentId) | 21 |
| Level | varchar(10) | No | Level varchar(10) NOT NULL CHECK(Level IN('guide','program','stage')) | 22 |
| ParentId | uniqueidentifier | Sí | ParentId uniqueidentifier NULL REFERENCES crm_agents.Profile(AgentId) | 23 |
| ProgramId | int | Sí | ProgramId int NULL | 23 |
| StageId | uniqueidentifier | Sí | StageId uniqueidentifier NULL | 24 |
| State | varchar(10) | No | State varchar(10) NOT NULL DEFAULT 'draft' CHECK(State IN('draft','active','paused','archived')) | 24 |
| Version | bigint | No | Version bigint NOT NULL CHECK(Version>0) | 25 |
| Revision | bigint | No | Revision bigint NOT NULL DEFAULT 1 CHECK(Revision>0) | 25 |
| ApprovedVersion | bigint | Sí | ApprovedVersion bigint NULL | 25 |
| Document | nvarchar(max) | No | Document nvarchar(max) NOT NULL CHECK(ISJSON(Document)=1) | 26 |
| UpdatedAt | datetime2(7) | No | UpdatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME() | 27 |

**Restricciones de tabla:**

- Línea 28: `FOREIGN KEY(StageId,ProgramId) REFERENCES crm_agents.Stage(StageId,ProgramId)`
- Línea 29: `CHECK((Level='guide' AND ParentId IS NULL AND ProgramId IS NULL AND StageId IS NULL) OR (Level='program' AND ParentId IS NOT NULL AND ProgramId IS NOT NULL AND StageId IS NULL) OR (Level='stage' AND ParentId IS NOT NULL AND ProgramId IS NOT NULL AND StageId IS NOT NULL))`
- Línea 32: `CHECK(ParentId IS NULL OR ParentId<>AgentId)`
- Línea 32: `CHECK(State<>'active' OR (ApprovedVersion IS NOT NULL AND ApprovedVersion=Version))`

**Claves foráneas:**

- Línea 21: `AgentId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm_inbox.Agent(AgentId)`
- Línea 23: `ParentId uniqueidentifier NULL REFERENCES crm_agents.Profile(AgentId)`
- Línea 28: `FOREIGN KEY(StageId,ProgramId) REFERENCES crm_agents.Stage(StageId,ProgramId)`

**CREATE INDEX explícitos:**

- `UX_Agents_Program`: UNIQUE (ProgramId) WHERE Level='program' AND State<>'archived' · [backend/migrations/019_admissions_agents.sql:34](../../../backend/migrations/019_admissions_agents.sql#L34).
- `UX_Agents_Stage`: UNIQUE (StageId) WHERE Level='stage' AND State<>'archived' · [backend/migrations/019_admissions_agents.sql:35](../../../backend/migrations/019_admissions_agents.sql#L35).
- `UX_Agents_Guide`: UNIQUE (Level) WHERE Level='guide' AND State<>'archived' · [backend/migrations/019_admissions_agents.sql:36](../../../backend/migrations/019_admissions_agents.sql#L36).

**Consumidores literales:** [backend/app/modules/agents/runtime.py:93](../../../backend/app/modules/agents/runtime.py#L93), [backend/app/modules/agents/service.py:50](../../../backend/app/modules/agents/service.py#L50), [backend/app/modules/inbox/application/operations.py:443](../../../backend/app/modules/inbox/application/operations.py#L443)

## crm_agents.Context

[Declaración 019:37](../../../backend/migrations/019_admissions_agents.sql#L37).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| ContextId | uniqueidentifier | No | ContextId uniqueidentifier NOT NULL PRIMARY KEY | 38 |
| ConversationId | uniqueidentifier | No | ConversationId uniqueidentifier NOT NULL REFERENCES crm.Conversation(ConversationId) | 39 |
| ProgramId | int | No | ProgramId int NOT NULL | 40 |
| ApplicantId | int | Sí | ApplicantId int NULL | 40 |
| PeriodId | int | Sí | PeriodId int NULL | 40 |
| StageId | uniqueidentifier | Sí | StageId uniqueidentifier NULL | 40 |
| Revision | bigint | No | Revision bigint NOT NULL CHECK(Revision>0) | 41 |
| StageRevision | bigint | Sí | StageRevision bigint NULL | 41 |
| Evidence | nvarchar(1000) | No | Evidence nvarchar(1000) NOT NULL | 42 |
| ApprovedAt | datetime2(7) | No | ApprovedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME() | 42 |
| MemoryJson | nvarchar(max) | No | MemoryJson nvarchar(max) NOT NULL DEFAULT '{}' CHECK(ISJSON(MemoryJson)=1) | 43 |
| BaselineSequence | bigint | No | BaselineSequence bigint NOT NULL | 43 |

**Restricciones de tabla:**

- Línea 44: `FOREIGN KEY(StageId,ProgramId) REFERENCES crm_agents.Stage(StageId,ProgramId)`
- Línea 45: `UNIQUE(ContextId,ConversationId)`
- Línea 45: `CHECK((ApplicantId IS NULL AND PeriodId IS NULL) OR (ApplicantId IS NOT NULL AND PeriodId IS NOT NULL))`

**Claves foráneas:**

- Línea 39: `ConversationId uniqueidentifier NOT NULL REFERENCES crm.Conversation(ConversationId)`
- Línea 44: `FOREIGN KEY(StageId,ProgramId) REFERENCES crm_agents.Stage(StageId,ProgramId)`

**Consumidores literales:** [backend/app/modules/agents/operations.py:43](../../../backend/app/modules/agents/operations.py#L43), [backend/app/modules/agents/router.py:82](../../../backend/app/modules/agents/router.py#L82), [backend/app/modules/agents/runtime.py:112](../../../backend/app/modules/agents/runtime.py#L112), [backend/app/modules/agents/service.py:64](../../../backend/app/modules/agents/service.py#L64), [backend/app/modules/ai/application/admissions.py:355](../../../backend/app/modules/ai/application/admissions.py#L355)

## crm_agents.SourceScope

[Declaración 019:47](../../../backend/migrations/019_admissions_agents.sql#L47).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| DocumentId | uniqueidentifier | No | DocumentId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm_ai.KnowledgeDocument(DocumentId) | 48 |
| ProgramId | int | Sí | ProgramId int NULL | 49 |
| StageId | uniqueidentifier | Sí | StageId uniqueidentifier NULL | 49 |
| Owner | nvarchar(100) | No | Owner nvarchar(100) NOT NULL | 49 |
| ValidUntil | date | No | ValidUntil date NOT NULL | 50 |
| Revision | bigint | No | Revision bigint NOT NULL CHECK(Revision>0) | 50 |
| DocumentRevision | bigint | No | DocumentRevision bigint NOT NULL | 50 |
| ApprovedAt | datetime2(7) | No | ApprovedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME() | 50 |

**Restricciones de tabla:**

- Línea 51: `FOREIGN KEY(StageId,ProgramId) REFERENCES crm_agents.Stage(StageId,ProgramId)`
- Línea 52: `CHECK(StageId IS NULL OR ProgramId IS NOT NULL)`

**Claves foráneas:**

- Línea 48: `DocumentId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm_ai.KnowledgeDocument(DocumentId)`
- Línea 51: `FOREIGN KEY(StageId,ProgramId) REFERENCES crm_agents.Stage(StageId,ProgramId)`

**Consumidores literales:** [backend/app/modules/agents/operations.py:133](../../../backend/app/modules/agents/operations.py#L133), [backend/app/modules/agents/service.py:239](../../../backend/app/modules/agents/service.py#L239)

## crm_agents.Assignment

[Declaración 019:54](../../../backend/migrations/019_admissions_agents.sql#L54).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| ConversationId | uniqueidentifier | No | ConversationId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm.Conversation(ConversationId) | 55 |
| Mode | varchar(10) | No | Mode varchar(10) NOT NULL CHECK(Mode IN('automatic','manual','human')) | 56 |
| ContextId | uniqueidentifier | Sí | ContextId uniqueidentifier NULL | 57 |
| Revision | bigint | No | Revision bigint NOT NULL CHECK(Revision>0) | 57 |
| Reason | nvarchar(1000) | No | Reason nvarchar(1000) NOT NULL | 58 |
| BaselineSequence | bigint | No | BaselineSequence bigint NOT NULL | 58 |

**Restricciones de tabla:**

- Línea 59: `FOREIGN KEY(ContextId,ConversationId) REFERENCES crm_agents.Context(ContextId,ConversationId)`

**Claves foráneas:**

- Línea 55: `ConversationId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm.Conversation(ConversationId)`
- Línea 59: `FOREIGN KEY(ContextId,ConversationId) REFERENCES crm_agents.Context(ContextId,ConversationId)`

**Consumidores literales:** [backend/app/modules/agents/operations.py:43](../../../backend/app/modules/agents/operations.py#L43), [backend/app/modules/agents/router.py:82](../../../backend/app/modules/agents/router.py#L82), [backend/app/modules/agents/service.py:63](../../../backend/app/modules/agents/service.py#L63), [backend/app/modules/inbox/application/operations.py:520](../../../backend/app/modules/inbox/application/operations.py#L520)

## crm_agents.History

[Declaración 019:61](../../../backend/migrations/019_admissions_agents.sql#L61).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| EventId | bigint | No | EventId bigint IDENTITY PRIMARY KEY | 62 |
| OperationId | uniqueidentifier | No | OperationId uniqueidentifier NOT NULL UNIQUE | 62 |
| EntityId | uniqueidentifier | No | EntityId uniqueidentifier NOT NULL | 63 |
| Kind | varchar(24) | No | Kind varchar(24) NOT NULL | 63 |
| PayloadHash | char(64) | No | PayloadHash char(64) NOT NULL | 63 |
| Document | nvarchar(max) | No | Document nvarchar(max) NOT NULL CHECK(ISJSON(Document)=1) | 64 |
| Note | nvarchar(1000) | No | Note nvarchar(1000) NOT NULL | 64 |
| Actor | varchar(30) | No | Actor varchar(30) NOT NULL DEFAULT 'local-operator' | 65 |
| CreatedAt | datetime2(7) | No | CreatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME() | 65 |

**CREATE INDEX explícitos:**

- `IX_Agents_History_Entity`: (EntityId,EventId DESC)  · [backend/migrations/019_admissions_agents.sql:67](../../../backend/migrations/019_admissions_agents.sql#L67).

**Consumidores literales:** [backend/app/modules/agents/operations.py:27](../../../backend/app/modules/agents/operations.py#L27), [backend/app/modules/agents/router.py:81](../../../backend/app/modules/agents/router.py#L81), [backend/app/modules/agents/runtime.py:32](../../../backend/app/modules/agents/runtime.py#L32), [backend/app/modules/agents/service.py:179](../../../backend/app/modules/agents/service.py#L179)

## crm_agents.Usage

[Declaración 019:68](../../../backend/migrations/019_admissions_agents.sql#L68).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| RequestId | uniqueidentifier | No | RequestId uniqueidentifier NOT NULL PRIMARY KEY | 69 |
| AgentId | uniqueidentifier | No | AgentId uniqueidentifier NOT NULL REFERENCES crm_agents.Profile(AgentId) | 69 |
| ChainJson | nvarchar(max) | No | ChainJson nvarchar(max) NOT NULL CHECK(ISJSON(ChainJson)=1) | 70 |
| TokensReserved | int | No | TokensReserved int NOT NULL CHECK(TokensReserved>0) | 70 |
| TokensUsed | int | Sí | TokensUsed int NULL CHECK(TokensUsed>=0) | 71 |
| State | varchar(12) | No | State varchar(12) NOT NULL CHECK(State IN('reserved','completed','uncertain')) | 71 |
| CreatedAt | datetime2(7) | No | CreatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME() | 72 |

**Claves foráneas:**

- Línea 69: `AgentId uniqueidentifier NOT NULL REFERENCES crm_agents.Profile(AgentId)`

**Consumidores literales:** [backend/app/modules/agents/router.py:192](../../../backend/app/modules/agents/router.py#L192), [backend/app/modules/agents/runtime.py:150](../../../backend/app/modules/agents/runtime.py#L150), [backend/app/modules/agents/service.py:1160](../../../backend/app/modules/agents/service.py#L1160)

## crm_agents.Execution

[Declaración 020:12](../../../backend/migrations/020_agent_execution.sql#L12).

| Columna | Tipo | NULL explícito | Definición | Línea |
|---|---|---|---|---:|
| RequestId | uniqueidentifier | No | RequestId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm_agents.Usage(RequestId) | 13 |
| AgentId | uniqueidentifier | No | AgentId uniqueidentifier NOT NULL REFERENCES crm_agents.Profile(AgentId) | 14 |
| AgentVersion | bigint | No | AgentVersion bigint NOT NULL CHECK(AgentVersion>0) | 15 |
| ConversationId | uniqueidentifier | Sí | ConversationId uniqueidentifier NULL REFERENCES crm.Conversation(ConversationId) | 16 |
| Provider | varchar(30) | No | Provider varchar(30) NOT NULL | 17 |
| ModelId | nvarchar(200) | No | ModelId nvarchar(200) NOT NULL | 17 |
| Route | varchar(30) | No | Route varchar(30) NOT NULL | 18 |
| Variant | nvarchar(40) | No | Variant nvarchar(40) NOT NULL | 18 |
| FallbackUsed | bit | No | FallbackUsed bit NOT NULL DEFAULT 0 | 19 |
| PricingJson | nvarchar(max) | No | PricingJson nvarchar(max) NOT NULL CHECK(ISJSON(PricingJson)=1) | 20 |
| AttemptsJson | nvarchar(max) | No | AttemptsJson nvarchar(max) NOT NULL DEFAULT '[]' CHECK(ISJSON(AttemptsJson)=1) | 21 |
| CostReserved | decimal(20,8) | Sí | CostReserved decimal(20,8) NULL CHECK(CostReserved>=0) | 22 |
| CostEstimated | decimal(20,8) | Sí | CostEstimated decimal(20,8) NULL CHECK(CostEstimated>=0) | 23 |
| InputTokens | bigint | Sí | InputTokens bigint NULL CHECK(InputTokens>=0) | 24 |
| OutputTokens | bigint | Sí | OutputTokens bigint NULL CHECK(OutputTokens>=0) | 24 |
| LatencyMs | bigint | Sí | LatencyMs bigint NULL CHECK(LatencyMs>=0) | 25 |
| State | varchar(12) | No | State varchar(12) NOT NULL CHECK(State IN('reserved','completed','failed','uncertain')) | 26 |
| ErrorCode | varchar(80) | Sí | ErrorCode varchar(80) NULL | 27 |
| SourceFingerprint | varchar(64) | No | SourceFingerprint varchar(64) NOT NULL | 27 |
| CreatedAt | datetime2(7) | No | CreatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME() | 28 |
| FinishedAt | datetime2(7) | Sí | FinishedAt datetime2(7) NULL | 28 |

**Claves foráneas:**

- Línea 13: `RequestId uniqueidentifier NOT NULL PRIMARY KEY REFERENCES crm_agents.Usage(RequestId)`
- Línea 14: `AgentId uniqueidentifier NOT NULL REFERENCES crm_agents.Profile(AgentId)`
- Línea 16: `ConversationId uniqueidentifier NULL REFERENCES crm.Conversation(ConversationId)`

**CREATE INDEX explícitos:**

- `IX_AgentExecution_AgentCreated`: (AgentId,CreatedAt DESC)  · [backend/migrations/020_agent_execution.sql:30](../../../backend/migrations/020_agent_execution.sql#L30).
- `IX_AgentExecution_Conversation`: (ConversationId,CreatedAt DESC)  · [backend/migrations/020_agent_execution.sql:31](../../../backend/migrations/020_agent_execution.sql#L31).

**Consumidores literales:** [backend/app/modules/agents/router.py:187](../../../backend/app/modules/agents/router.py#L187), [backend/app/modules/agents/runtime.py:19](../../../backend/app/modules/agents/runtime.py#L19), [backend/app/modules/agents/service.py:1175](../../../backend/app/modules/agents/service.py#L1175)
