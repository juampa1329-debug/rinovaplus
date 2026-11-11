# Canales · matriz vinculante de campos y acciones

SQL-C10 · definición; no demuestra que la pantalla C9 ya solicite estos campos ni que SQL/proveedores estén activos. La referencia es el código Scentra, sin reducirlo al DTO actual CBN.

Se inventariaron 115 contextos de campos/salidas y 83 instancias de acciones. Hay controles compartidos y botones repetidos; no son capacidades únicas.

| Grupo | Etiqueta de la fuente | Clave/control | Destino/uso |
|---|---|---|---|
| whatsapp | Proveedor | provider | sql: crm_channels2.Integration.Provider |
| whatsapp | Canal | channel | sql: crm_channels2.Integration.Channel |
| whatsapp | Estado | status | sql: crm_channels2.Integration.RequestedStatus |
| whatsapp | Modo de envío | dispatch_mode | sql: crm_channels2.Integration.DispatchMode |
| whatsapp | Phone Number ID | phone_number_id | sql: crm_channels2.Integration.ExternalAccountId |
| whatsapp | WABA ID | business_account_id | sql: crm_channels2.Integration.ParentExternalId |
| whatsapp | Meta App ID | app_id | sql: crm_channels2.Application.ClientId |
| whatsapp | Graph API | graph_api_version | sql: crm_channels2.Integration.ApiVersion |
| whatsapp | Meta App Secret | app_secret | vault: crm_channels2.SecretVersion.Ciphertext, crm_channels2.SecretVersion.Nonce, crm_channels2.SecretVersion.KeyVersion, crm_channels2.SecretVersion.Kind, crm_channels2.SecretVersion.VersionNo |
| whatsapp | Token permanente de Meta | access_token | vault: crm_channels2.SecretVersion.Ciphertext, crm_channels2.SecretVersion.Nonce, crm_channels2.SecretVersion.KeyVersion, crm_channels2.SecretVersion.Kind, crm_channels2.SecretVersion.VersionNo |
| instagram | Instagram App ID | app_id | sql: crm_channels2.Application.ClientId |
| instagram | Graph API | graph_api_version | sql: crm_channels2.Integration.ApiVersion |
| instagram | Instagram App Secret | app_secret | vault: crm_channels2.SecretVersion.Ciphertext, crm_channels2.SecretVersion.Nonce, crm_channels2.SecretVersion.KeyVersion, crm_channels2.SecretVersion.Kind, crm_channels2.SecretVersion.VersionNo |
| instagram | Estado | status | sql: crm_channels2.Integration.RequestedStatus |
| instagram | Modo envío | dispatch_mode | sql: crm_channels2.Integration.DispatchMode |
| instagram | Page ID | page_id | sql: crm_channels2.Integration.ParentExternalId |
| instagram | Instagram Business ID | instagram_business_account_id | sql: crm_channels2.Integration.ExternalAccountId |
| instagram | Nombre página | page_name | sql: crm_channels2.Integration.PageName |
| instagram | Usuario Instagram | instagram_username | sql: crm_channels2.Integration.UserName |
| instagram | Business Portfolio ID | business_id | sql: crm_channels2.Integration.PortfolioId |
| instagram | Token manual | page_access_token | vault: crm_channels2.SecretVersion.Ciphertext, crm_channels2.SecretVersion.Nonce, crm_channels2.SecretVersion.KeyVersion, crm_channels2.SecretVersion.Kind, crm_channels2.SecretVersion.VersionNo |
| facebook | Facebook App ID | app_id | sql: crm_channels2.Application.ClientId |
| facebook | Graph API | graph_api_version | sql: crm_channels2.Integration.ApiVersion |
| facebook | Facebook App Secret | app_secret | vault: crm_channels2.SecretVersion.Ciphertext, crm_channels2.SecretVersion.Nonce, crm_channels2.SecretVersion.KeyVersion, crm_channels2.SecretVersion.Kind, crm_channels2.SecretVersion.VersionNo |
| facebook | Estado | status | sql: crm_channels2.Integration.RequestedStatus |
| facebook | Modo envío | dispatch_mode | sql: crm_channels2.Integration.DispatchMode |
| facebook | Page ID | page_id | sql: crm_channels2.Integration.ExternalAccountId |
| facebook | Nombre página | page_name | sql: crm_channels2.Integration.PageName |
| facebook | Business Portfolio ID | business_id | sql: crm_channels2.Integration.PortfolioId |
| facebook | Page Access Token manual | page_access_token | vault: crm_channels2.SecretVersion.Ciphertext, crm_channels2.SecretVersion.Nonce, crm_channels2.SecretVersion.KeyVersion, crm_channels2.SecretVersion.Kind, crm_channels2.SecretVersion.VersionNo |
| whatsapp_number | Selecciona un número sincronizado... | phone_number_id | sql_selection: crm_channels2.ProviderAsset.ExternalId, crm_channels2.Integration.ExternalAccountId |
| whatsapp_number | PIN de 6 dígitos | whatsapp_number_pin | transient: PhoneRegisterIn.pin |
| meta_secret_rotation | (salida o etiqueta dinámica) | access_token | vault: crm_channels2.SecretVersion.Ciphertext, crm_channels2.SecretVersion.Nonce, crm_channels2.SecretVersion.KeyVersion, crm_channels2.SecretVersion.Kind, crm_channels2.SecretVersion.VersionNo |
| meta_secret_rotation | (salida o etiqueta dinámica) | app_secret | vault: crm_channels2.SecretVersion.Ciphertext, crm_channels2.SecretVersion.Nonce, crm_channels2.SecretVersion.KeyVersion, crm_channels2.SecretVersion.Kind, crm_channels2.SecretVersion.VersionNo |
| meta_secret_rotation | (salida o etiqueta dinámica) | meta_secret_rotation_current_password | transient_auth: SecretChangesIn.current_password |
| tiktok | Estado | tiktokForm.status | sql: crm_channels2.Integration.RequestedStatus |
| tiktok | Modo | tiktokForm.dispatch_mode | sql: crm_channels2.Integration.DispatchMode |
| tiktok | Client Key | tiktokForm.client_key | sql: crm_channels2.Application.ClientId |
| tiktok | Open ID | tiktokForm.open_id | sql: crm_channels2.Integration.ExternalAccountId |
| tiktok | Business / Shop ID | tiktokForm.business_account_id | sql: crm_channels2.Integration.BusinessAccountId |
| tiktok | Advertiser ID | tiktokForm.advertiser_id | sql: crm_channels2.Integration.AdvertiserId |
| tiktok | Scopes | tiktokForm.scopes | sql: crm_channels2.TikTokPolicy.ConfiguredScopes |
| tiktok | App Review | tiktokForm.app_review_status | sql: crm_channels2.TikTokPolicy.ReviewStatus |
| tiktok | Productos aprobados | tiktokForm.approved_products | sql: crm_channels2.TikTokPolicy.ApprovedProducts |
| tiktok | Scopes aprobados | tiktokForm.approved_scopes | sql: crm_channels2.TikTokPolicy.ApprovedScopes |
| tiktok | Eventos reales validados | tiktokForm.payload_samples_validated | sql: crm_channels2.TikTokPolicy.OperatorAttestedEvents |
| tiktok | Modo de envíos | tiktokForm.outbound_mode | sql: crm_channels2.TikTokPolicy.OutboundMode |
| tiktok | Activación % | tiktokForm.rollout_percent | sql: crm_channels2.TikTokPolicy.RolloutPercent |
| tiktok | Cuota diaria de envios | tiktokForm.daily_outbound_quota | sql: crm_channels2.TikTokPolicy.DailyOutboundQuota |
| tiktok | Cuota IA diaria | tiktokForm.daily_ai_quota | sql: crm_channels2.TikTokPolicy.DailyAiQuota |
| tiktok | Business Messaging | tiktokForm.business_messaging_enabled | sql: crm_channels2.TikTokPolicy.BusinessMessagingEnabled |
| tiktok | Responder comentarios | tiktokForm.comment_reply_enabled | sql: crm_channels2.TikTokPolicy.CommentReplyEnabled |
| tiktok | IA TikTok | tiktokForm.ai_enabled | sql: crm_channels2.TikTokPolicy.AiEnabled |
| tiktok | Agentes TikTok | tiktokForm.agents_enabled | sql: crm_channels2.TikTokPolicy.AgentsEnabled |
| tiktok | Activadores TikTok | tiktokForm.triggers_enabled | sql: crm_channels2.TikTokPolicy.TriggersEnabled |
| tiktok | Remarketing TikTok | tiktokForm.remarketing_enabled | sql: crm_channels2.TikTokPolicy.RemarketingEnabled |
| tiktok | Business API base | tiktokForm.business_api_base_url | sql: crm_channels2.TikTokPolicy.BusinessApiBaseUrl |
| tiktok | Business API version | tiktokForm.business_api_version | sql: crm_channels2.TikTokPolicy.BusinessApiVersion |
| tiktok | Send message path | tiktokForm.send_message_path | sql: crm_channels2.TikTokPolicy.SendMessagePath |
| tiktok | Comment reply path | tiktokForm.comment_reply_path | sql: crm_channels2.TikTokPolicy.CommentReplyPath |
| tiktok | Access token env opcional | tiktokForm.access_token_env | sql: crm_channels2.TikTokPolicy.AccessTokenAlias |
| tiktok | Notas operativas | tiktokForm.runtime_notes | sql: crm_channels2.TikTokPolicy.RuntimeNotes |
| tiktok | Client Secret | tiktokClientSecretRef | vault: crm_channels2.SecretVersion.Ciphertext, crm_channels2.SecretVersion.Nonce, crm_channels2.SecretVersion.KeyVersion, crm_channels2.SecretVersion.Kind, crm_channels2.SecretVersion.VersionNo |
| tiktok | Webhook Secret | tiktokWebhookSecretRef | vault: crm_channels2.SecretVersion.Ciphertext, crm_channels2.SecretVersion.Nonce, crm_channels2.SecretVersion.KeyVersion, crm_channels2.SecretVersion.Kind, crm_channels2.SecretVersion.VersionNo |
| tiktok | Nuevo Access Token TikTok | integrationSecretModal.access_token | vault: crm_channels2.SecretVersion.Ciphertext, crm_channels2.SecretVersion.Nonce, crm_channels2.SecretVersion.KeyVersion, crm_channels2.SecretVersion.Kind, crm_channels2.SecretVersion.VersionNo |
| tiktok | Nuevo Client Secret TikTok | integrationSecretModal.app_secret | vault: crm_channels2.SecretVersion.Ciphertext, crm_channels2.SecretVersion.Nonce, crm_channels2.SecretVersion.KeyVersion, crm_channels2.SecretVersion.Kind, crm_channels2.SecretVersion.VersionNo |
| tiktok | Nuevo Webhook Secret TikTok | integrationSecretModal.webhook_secret | vault: crm_channels2.SecretVersion.Ciphertext, crm_channels2.SecretVersion.Nonce, crm_channels2.SecretVersion.KeyVersion, crm_channels2.SecretVersion.Kind, crm_channels2.SecretVersion.VersionNo |
| tiktok | Tu contrasena | integrationSecretModal.current_password | transient_auth: SecretChangesIn.current_password |
| tiktok | TikTok actual: | selectedTikTokConfig.open_id // selectedTikTokConfig.business_account_id | derived: crm_channels2.Integration.ExternalAccountId, crm_channels2.Integration.BusinessAccountId |
| tiktok | (salida o etiqueta dinámica) | selectedTikTokIntegration.status / selectedTikTokConfig.dispatch_mode / selectedTikTokConfig.client_key | derived: crm_channels2.Integration.RequestedStatus, crm_channels2.Integration.DispatchMode, crm_channels2.Application.ClientId |
| tiktok | Client secret: | selectedTikTokConfig.has_client_secret / selectedTikTokConfig.client_secret_hint | derived: crm_channels2.SecretVersion.Hint, crm_channels2.SecretVersion.State |
| tiktok | Access token: | selectedTikTokConfig.has_access_token / selectedTikTokConfig.access_token_hint | derived: crm_channels2.SecretVersion.Hint, crm_channels2.SecretVersion.State |
| tiktok | Webhook: | selectedTikTokConfig.has_webhook_secret / selectedTikTokConfig.webhook_secret_hint | derived: crm_channels2.SecretVersion.Hint, crm_channels2.SecretVersion.State |
| tiktok | Callback URL | fullWebhookUrl(lastWebhookSecret.url_path) | derived: crm_channels2.WebhookEndpoint.EndpointKey |
| tiktok | Verify token | lastWebhookSecret.verify_token_once | one_time_output: crm_channels2.SecretVersion.Ciphertext |
| tiktok | OAuth TikTok | tiktokDiagnostics.oauth_callback_url // API_BASE/saas/v1/integrations/tiktok/oauth/callback | derived: crm_channels2.Application.RedirectUri |
| tiktok | (salida o etiqueta dinámica) | tiktokOAuth.callbackUrl | derived: crm_channels2.OAuthSession.RedirectUri |
| tiktok | Preparación: | tiktokReadiness.level / tiktokReadiness.app_review_status | derived: crm_channels2.TikTokPolicy.ReviewStatus, crm_channels2.TikTokPolicy.ApprovedProducts, crm_channels2.TikTokPolicy.ApprovedScopes, crm_channels2.VerificationEvidence.Result |
| tiktok | (salida o etiqueta dinámica) | tiktokDiagnostics.status / tiktokDiagnostics.config.scopes // tiktokDiagnostics.recommended_scopes | derived: crm_channels2.Integration.RequestedStatus, crm_channels2.TikTokPolicy.ConfiguredScopes, crm_channels2.ProviderAsset.ObservedScopes |
| tiktok | Webhook: | tiktokDiagnostics.endpoint.callback_url / tiktokDiagnostics.endpoint.last_seen_at | derived: crm_channels2.WebhookEndpoint.EndpointKey, crm_channels2.WebhookEndpoint.LastSeenAt |
| tiktok | Último evento crudo: | tiktokDiagnostics.last_event.event_type // status / received_at | derived: crm_channels2.WebhookEvent.Kind, crm_channels2.WebhookEvent.Status, crm_channels2.WebhookReceipt.ReceivedAt |
| tiktok | (salida o etiqueta dinámica) | tiktokReadiness.checks[].code / label / ok / warning | derived: crm_channels2.TikTokPolicy.ReviewStatus, crm_channels2.TikTokPolicy.ApprovedProducts, crm_channels2.TikTokPolicy.ApprovedScopes, crm_channels2.VerificationEvidence.Result |
| tiktok | Envíos operativos | tiktokRuntimePolicy.outbound_mode / rollout_percent / daily_outbound_quota / daily_ai_quota | derived: crm_channels2.TikTokPolicy.OutboundMode, crm_channels2.TikTokPolicy.RolloutPercent, crm_channels2.TikTokPolicy.DailyOutboundQuota, crm_channels2.TikTokPolicy.DailyAiQuota, crm_channels2.QuotaBucket.Reserved, crm_channels2.QuotaBucket.Committed |
| tiktok | (salida o etiqueta dinámica) | tiktokRuntimePreflight.capabilities[].allowed / reason / mode | derived: crm_channels2.TikTokPolicy.OutboundMode, crm_channels2.TikTokPolicy.BusinessMessagingEnabled, crm_channels2.TikTokPolicy.CommentReplyEnabled, crm_channels2.VerificationEvidence.Result, crm_channels2.QuotaBucket.Reserved, crm_channels2.QuotaBucket.Committed |
| tiktok | (salida o etiqueta dinámica) | tiktokRuntimePreflight.features / feature_sources | derived: crm_channels2.TikTokPolicy.AiEnabled, crm_channels2.TikTokPolicy.AgentsEnabled, crm_channels2.TikTokPolicy.TriggersEnabled, crm_channels2.TikTokPolicy.RemarketingEnabled |
| tiktok | Inbox TikTok | tiktokNormalization.inbox_conversations | derived: crm_channels2.ExternalIdentity.ConversationId |
| tiktok | Comentarios | tiktokNormalization.social_comments | derived: crm_channels2.SocialComment.CommentId |
| tiktok | Prospectos | tiktokNormalization.ad_leads | derived: transitorio |
| tiktok | Eventos reales | tiktokPayloadDiagnostics.recent_count | derived: crm_channels2.WebhookReceipt.ReceiptId |
| tiktok | Envíos bloqueados | tiktokRuntimePreflight.usage.queue.blocked | derived: crm_channels2.SendJob.State |
| tiktok | Errores abiertos | tiktokRuntimePreflight.usage.open_dead_letters | derived: transitorio |
| tiktok | Recursos configurados | tiktokAssets.configured | derived: crm_channels2.Integration.ExternalAccountId, crm_channels2.Integration.BusinessAccountId, crm_channels2.Integration.AdvertiserId |
| tiktok | Recursos inferidos | tiktokAssets.inferred_from_payloads | derived: crm_channels2.ProviderAsset.Kind, crm_channels2.ProviderAsset.ExternalId, crm_channels2.ProviderAsset.Metadata, crm_channels2.WebhookEvent.Payload |
| tiktok | (salida o etiqueta dinámica) | tiktokReadiness.products[].approved / name / code / missing_scopes | derived: crm_channels2.TikTokPolicy.ApprovedProducts, crm_channels2.TikTokPolicy.ApprovedScopes |
| tiktok | (salida o etiqueta dinámica) | tiktokDiagnostics.notes[] | derived: crm_channels2.ProviderOperation.ResultMetadata |
| tiktok | Access Token TikTok | integrationSecretModal.has_access_token / token_hint | derived: crm_channels2.SecretVersion.Hint, crm_channels2.SecretVersion.State |
| tiktok | Client Secret TikTok | integrationSecretModal.has_app_secret / app_secret_hint | derived: crm_channels2.SecretVersion.Hint, crm_channels2.SecretVersion.State |
| tiktok | Webhook Secret TikTok | integrationSecretModal.has_webhook_secret / webhook_secret_hint | derived: crm_channels2.SecretVersion.Hint, crm_channels2.SecretVersion.State |
| webhooks | (salida o etiqueta dinámica) | provider | sql: crm_channels2.WebhookEndpoint.ChannelSelector, crm_channels2.WebhookEndpoint.Provider |
| webhooks | Requerir firma HMAC | signature_required | sql: crm_channels2.WebhookEndpoint.SignatureRequired |
| webhooks | (salida o etiqueta dinámica) | endpoint_key | derived: crm_channels2.WebhookEndpoint.EndpointKey |
| webhooks | Callback URL para Meta | callback_url | derived: crm_channels2.WebhookEndpoint.EndpointKey |
| webhooks | Verify token para Meta | verify_token_once | one_time_output: crm_channels2.SecretVersion.Ciphertext |
| webhooks | Firma HMAC opcional | signature_secret_once | one_time_output: crm_channels2.SecretVersion.Ciphertext |
| webhooks | (salida o etiqueta dinámica) | endpoint.provider | derived: crm_channels2.WebhookEndpoint.ChannelSelector |
| webhooks | (salida o etiqueta dinámica) | endpoint.is_active | derived: crm_channels2.WebhookEndpoint.IsActive |
| webhooks | (salida o etiqueta dinámica) | endpoint.signature_required | derived: crm_channels2.WebhookEndpoint.SignatureRequired |
| webhooks | (salida o etiqueta dinámica) | endpoint.last_seen_at | derived: crm_channels2.WebhookEndpoint.LastSeenAt |
| webhooks | (salida o etiqueta dinámica) | webhook_check.ok | derived: crm_channels2.ProviderOperation.ResultMetadata, crm_channels2.VerificationEvidence.Summary, crm_channels2.WebhookEvent.Status |
| webhooks | (salida o etiqueta dinámica) | webhook_check.error | derived: crm_channels2.ProviderOperation.ResultMetadata, crm_channels2.VerificationEvidence.Summary, crm_channels2.WebhookEvent.Status |
| webhooks | (salida o etiqueta dinámica) | webhook_check.callback_url | derived: crm_channels2.ProviderOperation.ResultMetadata, crm_channels2.VerificationEvidence.Summary, crm_channels2.WebhookEvent.Status |
| webhooks | (salida o etiqueta dinámica) | webhook_check.checks | derived: crm_channels2.ProviderOperation.ResultMetadata, crm_channels2.VerificationEvidence.Summary, crm_channels2.WebhookEvent.Status |
| webhooks | Integracion vinculada | webhook_check.integration | derived: crm_channels2.ProviderOperation.ResultMetadata, crm_channels2.VerificationEvidence.Summary, crm_channels2.WebhookEvent.Status |
| webhooks | (salida o etiqueta dinámica) | webhook_check.recent_events | derived: crm_channels2.ProviderOperation.ResultMetadata, crm_channels2.VerificationEvidence.Summary, crm_channels2.WebhookEvent.Status |
| webhooks | (salida o etiqueta dinámica) | webhook_check.next_steps | derived: crm_channels2.ProviderOperation.ResultMetadata, crm_channels2.VerificationEvidence.Summary, crm_channels2.WebhookEvent.Status |

## Acciones de la fuente

| Etiqueta/handler | Uso definido |
|---|---|
| Refrescar / loadIntegrations | GET integrations · IntegrationListOut |
| Cargar datos para editar / editIntegration | local · local |
| Actualizar token / openIntegrationSecretModal | local · local |
| Eliminar / deleteIntegration | DELETE integrations/{integrationId} · MutationIn |
| Actualizar secretos / openIntegrationSecretModal | local · local |
| Guardar integracion / saveIntegration | POST/PATCH integrations/{integrationId?} · IntegrationWriteIn |
| Editar / editIntegration | local · local |
| Actualizar token / openIntegrationSecretModal | local · local |
| Eliminar / deleteIntegration | DELETE integrations/{integrationId} · MutationIn |
| Sincronizar números / syncWhatsappPhones | POST integrations/{integrationId}/phones/sync · DiscoveryIn |
| Registrar/verificar / registerWhatsappPhone | POST integrations/{integrationId}/phones/register · PhoneRegisterIn |
| Diagnóstico IG / loadInstagramDiagnostics | POST integrations/{integrationId}/diagnostics · ProviderDiagnosticIn |
| Cargar datos / editInstagramIntegration | local · local |
| Actualizar secretos / openIntegrationSecretModal | local · local |
| Salud token / loadMetaTokenHealth | GET integrations/{integrationId}/token-health · StatusOut |
| Renovar / refreshMetaToken | POST integrations/{integrationId}/oauth/refresh · TokenRefreshIn |
| Eliminar / deleteIntegration | DELETE integrations/{integrationId} · MutationIn |
| Conectar Instagram / startInstagramOAuth | POST oauth/{applicationId}/start · OAuthStartIn |
| Cargar cuenta / loadInstagramAssets | POST oauth/{sessionId}/discover · DiscoveryIn |
| Actualizar secretos / openIntegrationSecretModal | local · local |
| Guardar conexión manual / saveInstagramManual | POST/PATCH integrations/{integrationId?} · IntegrationWriteIn |
| Crear endpoint Instagram / createInstagramWebhookEndpoint | POST endpoints · EndpointWriteIn |
| Editar / editInstagramIntegration | local · local |
| Actualizar secretos / openIntegrationSecretModal | local · local |
| Salud / loadMetaTokenHealth | GET integrations/{integrationId}/token-health · StatusOut |
| Renovar / refreshMetaToken | POST integrations/{integrationId}/oauth/refresh · TokenRefreshIn |
| Eliminar / deleteIntegration | DELETE integrations/{integrationId} · MutationIn |
| Copiar URL / copyText | local · local |
| Copiar token / copyText | local · local |
| Copiar OAuth callback / copyText | local · local |
| Usar Instagram / connectInstagramAsset | POST oauth/{sessionId}/connect · ConnectAssetIn |
| Usar Facebook / connectFacebookAsset | POST oauth/{sessionId}/connect · ConnectAssetIn |
| Diagnóstico FB / loadFacebookDiagnostics | POST integrations/{integrationId}/diagnostics · ProviderDiagnosticIn |
| Cargar datos / editFacebookIntegration | local · local |
| Actualizar secretos / openIntegrationSecretModal | local · local |
| Salud token / loadMetaTokenHealth | GET integrations/{integrationId}/token-health · StatusOut |
| Renovar / refreshMetaToken | POST integrations/{integrationId}/oauth/refresh · TokenRefreshIn |
| Eliminar / deleteIntegration | DELETE integrations/{integrationId} · MutationIn |
| Conectar Facebook / startFacebookOAuth | POST oauth/{applicationId}/start · OAuthStartIn |
| Cargar páginas / loadFacebookAssets | POST oauth/{sessionId}/discover · DiscoveryIn |
| Actualizar secretos / openIntegrationSecretModal | local · local |
| Copiar OAuth callback / copyText | local · local |
| Usar Facebook / connectFacebookAsset | POST oauth/{sessionId}/connect · ConnectAssetIn |
| Editar / editFacebookIntegration | local · local |
| Actualizar secretos / openIntegrationSecretModal | local · local |
| Salud / loadMetaTokenHealth | GET integrations/{integrationId}/token-health · StatusOut |
| Renovar / refreshMetaToken | POST integrations/{integrationId}/oauth/refresh · TokenRefreshIn |
| Eliminar / deleteIntegration | DELETE integrations/{integrationId} · MutationIn |
| Guardar conexión manual / saveFacebookManual | POST/PATCH integrations/{integrationId?} · IntegrationWriteIn |
| Crear endpoint Facebook / createFacebookWebhookEndpoint | POST endpoints · EndpointWriteIn |
| Copiar URL / copyText | local · local |
| Copiar token / copyText | local · local |
| Guardar cifrado / saveIntegrationSecrets | POST integrations/{integrationId}/secrets · SecretChangesIn |
| Cancelar / setIntegrationSecretModal(null) | local · local |
| Diagnóstico TikTok / loadTikTokStatus | POST integrations/{integrationId}/diagnostics · ProviderDiagnosticIn |
| Descubrir recursos / discoverTikTokAssets | POST integrations/{integrationId}/resources/discover · DiscoveryIn |
| Procesar eventos / processTikTokPayloads | POST events/process · ProcessEventsIn |
| Cargar datos para editar / editTikTokIntegration(selectedTikTokIntegration) | local · local |
| Actualizar secretos / openIntegrationSecretModal(selectedTikTokIntegration) | local · local |
| Renovar token / refreshTikTokToken | POST integrations/{integrationId}/oauth/refresh · TokenRefreshIn |
| Eliminar / deleteIntegration(selectedTikTokIntegration) | DELETE integrations/{integrationId} · MutationIn |
| Actualizar secretos / openIntegrationSecretModal(selectedTikTokIntegration) | local · local |
| Guardar TikTok / saveTikTokManual | POST/PATCH integrations/{integrationId?} · IntegrationWriteIn |
| Crear endpoint TikTok / createTikTokWebhookEndpoint | POST endpoints · EndpointWriteIn |
| Copiar URL / copyText(fullWebhookUrl(lastWebhookSecret.url_path), Callback TikTok) | local · local |
| Copiar token / copyText(lastWebhookSecret.verify_token_once, Verify token TikTok) | local · local |
| Conectar TikTok / startTikTokOAuth | POST oauth/{applicationId}/start · OAuthStartIn |
| Actualizar estado / loadTikTokStatus | GET integrations/{integrationId}/status · StatusOut |
| Copiar OAuth callback / copyText(tiktokOAuth.callbackUrl, Callback OAuth TikTok) | local · local |
| Cerrar / setIntegrationSecretModal(null) | local · local |
| Guardar cifrado / saveIntegrationSecrets | POST integrations/{integrationId}/secrets · SecretChangesIn |
| Cancelar / setIntegrationSecretModal(null) | local · local |
| Refrescar / loadWebhooks | GET endpoints · EndpointListOut |
| Crear / actualizar endpoint / createWebhook | POST endpoints · EndpointWriteIn |
| Copiar URL / copyText | local · local |
| Copiar token / copyText | local · local |
| Copiar firma / copyText | local · local |
| Verificar / verifyWebhookEndpoint | POST endpoints/{endpointId}/verify · MutationIn |
| Permitir token, Exigir firma / updateWebhookEndpoint | PATCH endpoints/{endpointId} · EndpointWriteIn |
| Rotar token / rotateWebhookToken | POST endpoints/{endpointId}/rotate-token · MutationIn |
| Rotar firma / rotateWebhookSignature | POST endpoints/{endpointId}/rotate-signature · MutationIn |
| Eliminar / deleteWebhookEndpoint | DELETE endpoints/{endpointId} · MutationIn |
| Procesar eventos pendientes / processWebhookEvents | POST events/process · ProcessEventsIn |

La especificación JSON conserva tipos, valores/etiquetas de opciones, required/maxLength observados, condiciones de visibilidad, handlers y anclas. PIN y contraseña son efímeros; tokens/secretos se cifran; Verify token generado se expone una vez. No confundirlo con el token permanente de WhatsApp.

[Contrato JSON](channels-ui-parity-contract.json) · [Modelo SQL](channels-parity-contract.json) · [Contrato principal](SQL_C10_CONTRACT.md)
