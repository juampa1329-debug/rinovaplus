"""One explicit schema binding for every finite business operation.

Models and synthetic examples are validated on import; no business execution.
"""

import json
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

from app import local_models as m
from app import local_plans as p
from app import schemas
from app.local_samples import SAMPLES


@dataclass(frozen=True)
class LocalContract:
    body_model: type[BaseModel] | None
    query_model: type[BaseModel]
    path_model: type[BaseModel]
    result_model: type[BaseModel]
    evidence: Literal["local_source", "local_proposal"]
    body_example: BaseModel | None
    query_example: BaseModel
    path_example: BaseModel
    result_example: BaseModel

    @property
    def models(self):
        return tuple(
            model
            for model in (
                self.body_model,
                self.query_model,
                self.path_model,
                self.result_model,
            )
            if model is not None
        )


def bind(body, query, path, result, evidence):
    def example(model):
        return model.model_validate_json(json.dumps(SAMPLES[model.__name__]))

    return LocalContract(
        body,
        query,
        path,
        result,
        evidence,
        example(body) if body else None,
        example(query),
        example(path),
        example(result),
    )


# This is the sole authored schema-operation mapping. GROUPS owns only inventory.
LOCAL_CONTRACTS = {
    ("POST", "/application-links"): bind(
        m.LinkIntent, m.EmptyQuery, m.EmptyPath, p.LinkIntentPlan, "local_source"
    ),
    ("GET", "/applications"): bind(
        None, m.ApplicationQuery, m.EmptyPath, m.ApplicationsResult, "local_source"
    ),
    ("GET", "/assistant/configuration"): bind(
        None, m.EmptyQuery, m.EmptyPath, m.AssistantConfigurationResult, "local_source"
    ),
    ("PUT", "/assistant/configuration"): bind(
        schemas.AssistantDraft,
        m.EmptyQuery,
        m.EmptyPath,
        p.AssistantDraftPlan,
        "local_source",
    ),
    ("PUT", "/assistant/fallback-references"): bind(
        m.FallbackIntent,
        m.EmptyQuery,
        m.EmptyPath,
        p.FallbackIntentPlan,
        "local_proposal",
    ),
    ("POST", "/assistant/publications"): bind(
        m.AssistantPublication,
        m.EmptyQuery,
        m.EmptyPath,
        p.AssistantPublicationPlan,
        "local_source",
    ),
    ("POST", "/assistant/reviews"): bind(
        m.AssistantReview,
        m.EmptyQuery,
        m.EmptyPath,
        p.AssistantReviewPlan,
        "local_source",
    ),
    ("POST", "/assistant/tests"): bind(
        m.AssistantTest, m.EmptyQuery, m.EmptyPath, p.AssistantTestPlan, "local_source"
    ),
    ("POST", "/auth/challenges"): bind(
        m.ChallengeIntent,
        m.EmptyQuery,
        m.EmptyPath,
        p.ChallengeIntentPlan,
        "local_proposal",
    ),
    ("POST", "/auth/login"): bind(
        m.LoginIntent, m.EmptyQuery, m.EmptyPath, p.LoginIntentPlan, "local_proposal"
    ),
    ("POST", "/auth/logout"): bind(
        m.SessionEnd, m.EmptyQuery, m.EmptyPath, p.SessionEndPlan, "local_proposal"
    ),
    ("GET", "/auth/me"): bind(
        None, m.EmptyQuery, m.EmptyPath, m.MeResult, "local_proposal"
    ),
    ("POST", "/auth/reauthenticate"): bind(
        m.ReauthenticationIntent,
        m.EmptyQuery,
        m.EmptyPath,
        p.ReauthenticationIntentPlan,
        "local_proposal",
    ),
    ("POST", "/auth/recovery"): bind(
        m.IdentityRecoveryIntent,
        m.EmptyQuery,
        m.EmptyPath,
        p.IdentityRecoveryIntentPlan,
        "local_proposal",
    ),
    ("GET", "/auth/sessions"): bind(
        None, m.PageQuery, m.EmptyPath, m.SessionsResult, "local_proposal"
    ),
    ("GET", "/catalog/attention-hours"): bind(
        None, m.EmptyQuery, m.EmptyPath, m.AttentionHoursResult, "local_proposal"
    ),
    ("GET", "/catalog/programs"): bind(
        None, m.PageQuery, m.EmptyPath, m.ProgramsResult, "local_proposal"
    ),
    ("GET", "/catalog/schedules"): bind(
        None, m.PageQuery, m.EmptyPath, m.SchedulesResult, "local_proposal"
    ),
    ("GET", "/channels"): bind(
        None, m.PageQuery, m.EmptyPath, m.ChannelsResult, "local_source"
    ),
    ("POST", "/channels/whatsapp/number-registration"): bind(
        m.NumberRegistration,
        m.EmptyQuery,
        m.EmptyPath,
        p.NumberRegistrationPlan,
        "local_source",
    ),
    ("POST", "/channels/whatsapp/number-verification"): bind(
        m.NumberVerification,
        m.EmptyQuery,
        m.EmptyPath,
        p.NumberVerificationPlan,
        "local_source",
    ),
    ("GET", "/channels/whatsapp/numbers"): bind(
        None, m.PageQuery, m.EmptyPath, m.NumbersResult, "local_source"
    ),
    ("GET", "/clients"): bind(
        None, m.ClientQuery, m.EmptyPath, m.ClientsResult, "local_source"
    ),
    ("POST", "/clients"): bind(
        schemas.ClientDraft,
        m.EmptyQuery,
        m.EmptyPath,
        p.ClientDraftPlan,
        "local_source",
    ),
    ("GET", "/comments"): bind(
        None, m.CommentQuery, m.EmptyPath, m.CommentsResult, "local_source"
    ),
    ("GET", "/conversations"): bind(
        None, m.ConversationQuery, m.EmptyPath, m.ConversationsResult, "local_source"
    ),
    ("GET", "/corporate-relations"): bind(
        None, m.PageQuery, m.EmptyPath, m.CorporatesResult, "local_proposal"
    ),
    ("GET", "/creator-audit-events"): bind(
        None, m.PageQuery, m.EmptyPath, m.CreatorAuditResult, "local_proposal"
    ),
    ("GET", "/creator-campaigns"): bind(
        None, m.PageQuery, m.EmptyPath, m.CampaignsResult, "local_proposal"
    ),
    ("POST", "/creator-campaigns"): bind(
        m.CampaignDraft,
        m.EmptyQuery,
        m.EmptyPath,
        p.CampaignDraftPlan,
        "local_proposal",
    ),
    ("GET", "/creator-resources"): bind(
        None, m.PageQuery, m.EmptyPath, m.ResourcesResult, "local_proposal"
    ),
    ("POST", "/creator-resources"): bind(
        m.ResourceDraft,
        m.EmptyQuery,
        m.EmptyPath,
        p.ResourceDraftPlan,
        "local_proposal",
    ),
    ("GET", "/creators"): bind(
        None, m.CreatorQuery, m.EmptyPath, m.CreatorsResult, "local_proposal"
    ),
    ("POST", "/creators"): bind(
        m.CreatorDraft, m.EmptyQuery, m.EmptyPath, p.CreatorDraftPlan, "local_proposal"
    ),
    ("GET", "/crm/configuration"): bind(
        None, m.EmptyQuery, m.EmptyPath, m.CrmResult, "local_source"
    ),
    ("PUT", "/crm/configuration"): bind(
        schemas.CrmDraft, m.EmptyQuery, m.EmptyPath, p.CrmDraftPlan, "local_source"
    ),
    ("GET", "/diagnostics"): bind(
        None, m.EmptyQuery, m.EmptyPath, m.DiagnosticsResult, "local_source"
    ),
    ("GET", "/diagnostics/endpoints"): bind(
        None, m.PageQuery, m.EmptyPath, m.DiagnosticEndpointsResult, "local_source"
    ),
    ("GET", "/diagnostics/events"): bind(
        None, m.PageQuery, m.EmptyPath, m.DiagnosticEventsResult, "local_source"
    ),
    ("GET", "/diagnostics/incidents"): bind(
        None, m.PageQuery, m.EmptyPath, m.DiagnosticIncidentsResult, "local_source"
    ),
    ("POST", "/diagnostics/pause"): bind(
        m.OperationPause,
        m.EmptyQuery,
        m.EmptyPath,
        p.OperationPausePlan,
        "local_source",
    ),
    ("POST", "/diagnostics/process"): bind(
        m.ProcessIntent, m.EmptyQuery, m.EmptyPath, p.ProcessIntentPlan, "local_source"
    ),
    ("GET", "/diagnostics/queues"): bind(
        None, m.PageQuery, m.EmptyPath, m.DiagnosticQueuesResult, "local_source"
    ),
    ("POST", "/diagnostics/recovery-reviews"): bind(
        m.RecoveryReview,
        m.EmptyQuery,
        m.EmptyPath,
        p.RecoveryReviewPlan,
        "local_source",
    ),
    ("POST", "/diagnostics/resume"): bind(
        m.OperationResume,
        m.EmptyQuery,
        m.EmptyPath,
        p.OperationResumePlan,
        "local_source",
    ),
    ("POST", "/diagnostics/simulations"): bind(
        m.SimulationIntent,
        m.EmptyQuery,
        m.EmptyPath,
        p.SimulationIntentPlan,
        "local_source",
    ),
    ("GET", "/follow-ups"): bind(
        None, m.FollowupQuery, m.EmptyPath, m.FollowupsResult, "local_proposal"
    ),
    ("POST", "/follow-ups"): bind(
        m.FollowupIntent,
        m.EmptyQuery,
        m.EmptyPath,
        p.FollowupIntentPlan,
        "local_proposal",
    ),
    ("GET", "/knowledge/aliases"): bind(
        None, m.PageQuery, m.EmptyPath, m.AliasesResult, "local_proposal"
    ),
    ("PUT", "/knowledge/aliases"): bind(
        m.AliasIntent, m.EmptyQuery, m.EmptyPath, p.AliasIntentPlan, "local_proposal"
    ),
    ("POST", "/knowledge/evaluations"): bind(
        m.EvaluationIntent,
        m.EmptyQuery,
        m.EmptyPath,
        m.EvaluationResult,
        "local_proposal",
    ),
    ("POST", "/knowledge/indexing"): bind(
        m.IndexIntent, m.EmptyQuery, m.EmptyPath, p.IndexIntentPlan, "local_proposal"
    ),
    ("POST", "/knowledge/publications"): bind(
        m.KnowledgePublication,
        m.EmptyQuery,
        m.EmptyPath,
        p.KnowledgePublicationPlan,
        "local_proposal",
    ),
    ("POST", "/knowledge/retrieval-tests"): bind(
        m.RetrievalIntent,
        m.EmptyQuery,
        m.EmptyPath,
        m.RetrievalResult,
        "local_proposal",
    ),
    ("GET", "/knowledge/sources"): bind(
        None, m.SourceQuery, m.EmptyPath, m.SourcesResult, "local_proposal"
    ),
    ("POST", "/knowledge/sources"): bind(
        m.SourceMetadata,
        m.EmptyQuery,
        m.EmptyPath,
        p.SourceMetadataPlan,
        "local_proposal",
    ),
    ("POST", "/media"): bind(
        m.MediaMetadata,
        m.EmptyQuery,
        m.EmptyPath,
        p.MediaMetadataPlan,
        "local_proposal",
    ),
    ("GET", "/overview"): bind(
        None, m.EmptyQuery, m.EmptyPath, m.OverviewResult, "local_proposal"
    ),
    ("GET", "/profile"): bind(
        None, m.EmptyQuery, m.EmptyPath, m.ProfileResult, "local_source"
    ),
    ("PUT", "/profile"): bind(
        schemas.ProfileDraft,
        m.EmptyQuery,
        m.EmptyPath,
        p.ProfileDraftPlan,
        "local_source",
    ),
    ("POST", "/profile/email-change"): bind(
        m.EmailChange, m.EmptyQuery, m.EmptyPath, p.EmailChangePlan, "local_source"
    ),
    ("POST", "/profile/email-verification"): bind(
        m.EmailVerification,
        m.EmptyQuery,
        m.EmptyPath,
        p.EmailVerificationPlan,
        "local_source",
    ),
    ("GET", "/providers"): bind(
        None, m.ProviderQuery, m.EmptyPath, m.ProvidersResult, "local_proposal"
    ),
    ("GET", "/retention"): bind(
        None, m.PageQuery, m.EmptyPath, m.RetentionListResult, "local_proposal"
    ),
    ("GET", "/roles"): bind(
        None, m.PageQuery, m.EmptyPath, m.RolesResult, "local_proposal"
    ),
    ("GET", "/sales-memory"): bind(
        None, m.PageQuery, m.EmptyPath, m.SalesMemoriesResult, "local_proposal"
    ),
    ("GET", "/security"): bind(
        None, m.EmptyQuery, m.EmptyPath, m.SecurityResult, "local_proposal"
    ),
    ("GET", "/security/audit-events"): bind(
        None, m.PageQuery, m.EmptyPath, m.AuditResult, "local_proposal"
    ),
    ("POST", "/security/deletion-requests"): bind(
        m.DeletionIntent,
        m.EmptyQuery,
        m.EmptyPath,
        p.DeletionIntentPlan,
        "local_proposal",
    ),
    ("POST", "/security/exports"): bind(
        m.ExportIntent, m.EmptyQuery, m.EmptyPath, p.ExportIntentPlan, "local_proposal"
    ),
    ("POST", "/security/password-change"): bind(
        m.PasswordChange,
        m.EmptyQuery,
        m.EmptyPath,
        p.PasswordChangePlan,
        "local_proposal",
    ),
    ("POST", "/security/two-factor/activation"): bind(
        m.FactorActivation,
        m.EmptyQuery,
        m.EmptyPath,
        p.FactorActivationPlan,
        "local_proposal",
    ),
    ("POST", "/security/two-factor/enrollment"): bind(
        m.FactorEnrollment,
        m.EmptyQuery,
        m.EmptyPath,
        p.FactorEnrollmentPlan,
        "local_proposal",
    ),
    ("POST", "/security/two-factor/recovery"): bind(
        m.FactorRecovery,
        m.EmptyQuery,
        m.EmptyPath,
        p.FactorRecoveryPlan,
        "local_proposal",
    ),
    ("POST", "/security/two-factor/verification"): bind(
        m.FactorVerification,
        m.EmptyQuery,
        m.EmptyPath,
        p.FactorVerificationPlan,
        "local_proposal",
    ),
    ("POST", "/speech/synthesis"): bind(
        m.SynthesisIntent,
        m.EmptyQuery,
        m.EmptyPath,
        m.SynthesisResult,
        "local_proposal",
    ),
    ("POST", "/speech/transcriptions"): bind(
        m.TranscriptionIntent,
        m.EmptyQuery,
        m.EmptyPath,
        m.TranscriptionResult,
        "local_proposal",
    ),
    ("GET", "/users"): bind(
        None, m.PageQuery, m.EmptyPath, m.UsersResult, "local_proposal"
    ),
    ("POST", "/users/invitations"): bind(
        m.UserInvitation,
        m.EmptyQuery,
        m.EmptyPath,
        p.UserInvitationPlan,
        "local_proposal",
    ),
    ("GET", "/application-links/{link_reference}"): bind(
        None,
        m.EmptyQuery,
        m.ApplicationLinkPath,
        m.ApplicationLinkResult,
        "local_source",
    ),
    ("POST", "/application-links/{link_reference}/submissions"): bind(
        schemas.ApplicationDraft,
        m.EmptyQuery,
        m.ApplicationLinkPath,
        p.ApplicationDraftPlan,
        "local_source",
    ),
    ("GET", "/applications/{application_id}"): bind(
        None, m.EmptyQuery, m.ApplicationPath, m.ApplicationResult, "local_source"
    ),
    ("POST", "/applications/{application_id}/core-registration"): bind(
        m.CoreRegistrationIntent,
        m.EmptyQuery,
        m.ApplicationPath,
        p.CoreRegistrationIntentPlan,
        "local_source",
    ),
    ("POST", "/applications/{application_id}/reopen"): bind(
        m.ReviewReopen,
        m.EmptyQuery,
        m.ApplicationPath,
        p.ReviewReopenPlan,
        "local_source",
    ),
    ("POST", "/applications/{application_id}/review-decisions"): bind(
        schemas.ReviewDraft,
        m.EmptyQuery,
        m.ApplicationPath,
        p.ReviewDraftPlan,
        "local_source",
    ),
    ("POST", "/applications/{application_id}/review-start"): bind(
        m.ReviewStart,
        m.EmptyQuery,
        m.ApplicationPath,
        p.ReviewStartPlan,
        "local_source",
    ),
    ("DELETE", "/auth/sessions/{session_id}"): bind(
        None,
        m.SessionRevocationQuery,
        m.SessionPath,
        p.SessionRevocationPlan,
        "local_proposal",
    ),
    ("GET", "/catalog/programs/{program_id}"): bind(
        None, m.EmptyQuery, m.ProgramPath, m.ProgramResult, "local_proposal"
    ),
    ("GET", "/channels/{channel}"): bind(
        None, m.EmptyQuery, m.ChannelPath, m.ChannelResult, "local_source"
    ),
    ("POST", "/channels/{channel}/activation"): bind(
        m.ActivationIntent,
        m.EmptyQuery,
        m.ChannelPath,
        p.ActivationIntentPlan,
        "local_source",
    ),
    ("GET", "/channels/{channel}/capabilities"): bind(
        None, m.EmptyQuery, m.ChannelPath, m.ChannelCapabilitiesResult, "local_source"
    ),
    ("POST", "/channels/{channel}/connection-tests"): bind(
        m.ChannelTest, m.EmptyQuery, m.ChannelPath, p.ChannelTestPlan, "local_source"
    ),
    ("POST", "/channels/{channel}/discovery"): bind(
        m.ChannelDiscovery,
        m.EmptyQuery,
        m.ChannelPath,
        p.ChannelDiscoveryPlan,
        "local_source",
    ),
    ("PUT", "/channels/{channel}/draft"): bind(
        schemas.ChannelDraft,
        m.EmptyQuery,
        m.ChannelPath,
        p.ChannelDraftPlan,
        "local_source",
    ),
    ("POST", "/channels/{channel}/oauth"): bind(
        m.OAuthIntent, m.EmptyQuery, m.ChannelPath, p.OAuthIntentPlan, "local_source"
    ),
    ("GET", "/channels/{channel}/oauth/callback"): bind(
        None, m.CallbackQuery, m.ChannelPath, m.CallbackResult, "local_source"
    ),
    ("POST", "/channels/{channel}/pause"): bind(
        m.PauseIntent, m.EmptyQuery, m.ChannelPath, p.PauseIntentPlan, "local_source"
    ),
    ("GET", "/channels/{channel}/webhook-reference"): bind(
        None, m.EmptyQuery, m.ChannelPath, m.WebhookReferenceResult, "local_source"
    ),
    ("GET", "/clients/{client_id}"): bind(
        None, m.EmptyQuery, m.ClientPath, m.ClientResult, "local_source"
    ),
    ("PATCH", "/clients/{client_id}"): bind(
        schemas.ClientDraft,
        m.EmptyQuery,
        m.ClientPath,
        p.ClientDraftPlan,
        "local_source",
    ),
    ("POST", "/clients/{client_id}/deactivation-requests"): bind(
        m.DeactivationIntent,
        m.EmptyQuery,
        m.ClientPath,
        p.DeactivationIntentPlan,
        "local_source",
    ),
    ("GET", "/clients/{client_id}/timeline"): bind(
        None, m.PageQuery, m.ClientPath, m.ClientTimelineResult, "local_source"
    ),
    ("GET", "/comments/{comment_id}"): bind(
        None, m.EmptyQuery, m.CommentPath, m.CommentResult, "local_source"
    ),
    ("POST", "/comments/{comment_id}/reactions"): bind(
        m.ReactionIntent,
        m.EmptyQuery,
        m.CommentPath,
        p.ReactionIntentPlan,
        "local_source",
    ),
    ("POST", "/comments/{comment_id}/replies"): bind(
        schemas.MessageDraft,
        m.EmptyQuery,
        m.CommentPath,
        p.MessageDraftPlan,
        "local_source",
    ),
    ("GET", "/conversations/{conversation_id}"): bind(
        None, m.EmptyQuery, m.ConversationPath, m.ConversationResult, "local_source"
    ),
    ("POST", "/conversations/{conversation_id}/analysis"): bind(
        m.AnalysisIntent,
        m.EmptyQuery,
        m.ConversationPath,
        m.AnalysisResult,
        "local_source",
    ),
    ("POST", "/conversations/{conversation_id}/control"): bind(
        m.ConversationControl,
        m.EmptyQuery,
        m.ConversationPath,
        p.ConversationControlPlan,
        "local_source",
    ),
    ("GET", "/conversations/{conversation_id}/delivery-statuses"): bind(
        None, m.PageQuery, m.ConversationPath, m.DeliveriesResult, "local_source"
    ),
    ("GET", "/conversations/{conversation_id}/events"): bind(
        None, m.PageQuery, m.ConversationPath, m.EventsResult, "local_source"
    ),
    ("GET", "/conversations/{conversation_id}/messages"): bind(
        None, m.PageQuery, m.ConversationPath, m.MessagesResult, "local_source"
    ),
    ("POST", "/conversations/{conversation_id}/messages"): bind(
        schemas.MessageDraft,
        m.EmptyQuery,
        m.ConversationPath,
        p.MessageDraftPlan,
        "local_source",
    ),
    ("POST", "/conversations/{conversation_id}/read"): bind(
        m.ReadIntent, m.EmptyQuery, m.ConversationPath, p.ReadIntentPlan, "local_source"
    ),
    ("POST", "/conversations/{conversation_id}/suggestions"): bind(
        m.SuggestionIntent,
        m.EmptyQuery,
        m.ConversationPath,
        m.SuggestionResult,
        "local_source",
    ),
    ("GET", "/conversations/{conversation_id}/tasks"): bind(
        None, m.PageQuery, m.ConversationPath, m.TasksResult, "local_source"
    ),
    ("POST", "/conversations/{conversation_id}/tasks"): bind(
        schemas.TaskDraft,
        m.EmptyQuery,
        m.ConversationPath,
        p.TaskDraftPlan,
        "local_source",
    ),
    ("PATCH", "/conversations/{conversation_id}/workflow"): bind(
        schemas.WorkflowDraft,
        m.EmptyQuery,
        m.ConversationPath,
        p.WorkflowDraftPlan,
        "local_source",
    ),
    ("GET", "/corporate-relations/{reference_id}"): bind(
        None, m.EmptyQuery, m.ReferencePath, m.CorporateResult, "local_proposal"
    ),
    ("POST", "/creator-campaigns/{campaign_id}/deliverables"): bind(
        m.DeliverableDraft,
        m.EmptyQuery,
        m.CampaignPath,
        p.DeliverableDraftPlan,
        "local_proposal",
    ),
    ("PATCH", "/creator-deliverables/{deliverable_id}"): bind(
        m.DeliverableUpdate,
        m.EmptyQuery,
        m.DeliverablePath,
        p.DeliverableUpdatePlan,
        "local_proposal",
    ),
    ("POST", "/creator-resources/{resource_id}/performance-analysis"): bind(
        m.PerformanceAnalysis,
        m.EmptyQuery,
        m.ResourcePath,
        p.PerformanceAnalysisPlan,
        "local_proposal",
    ),
    ("POST", "/creator-resources/{resource_id}/rights-reviews"): bind(
        m.RightsReview,
        m.EmptyQuery,
        m.ResourcePath,
        p.RightsReviewPlan,
        "local_proposal",
    ),
    ("POST", "/creator-resources/{resource_id}/rights-revocation"): bind(
        m.RightsRevocation,
        m.EmptyQuery,
        m.ResourcePath,
        p.RightsRevocationPlan,
        "local_proposal",
    ),
    ("POST", "/creator-resources/{resource_id}/spark-preflight"): bind(
        m.SparkPreflight,
        m.EmptyQuery,
        m.ResourcePath,
        p.SparkPreflightPlan,
        "local_proposal",
    ),
    ("POST", "/creators/{creator_id}/contact-plans"): bind(
        m.ContactPlan, m.EmptyQuery, m.CreatorPath, p.ContactPlanPlan, "local_proposal"
    ),
    ("POST", "/follow-ups/{follow_up_id}/cancellation"): bind(
        m.FollowupCancellation,
        m.EmptyQuery,
        m.FollowupPath,
        p.FollowupCancellationPlan,
        "local_proposal",
    ),
    ("PATCH", "/knowledge/sources/{source_id}"): bind(
        m.SourceUpdate, m.EmptyQuery, m.SourcePath, p.SourceUpdatePlan, "local_proposal"
    ),
    ("POST", "/knowledge/sources/{source_id}/removal-requests"): bind(
        m.SourceRemoval,
        m.EmptyQuery,
        m.SourcePath,
        p.SourceRemovalPlan,
        "local_proposal",
    ),
    ("GET", "/media/{media_reference}"): bind(
        None, m.EmptyQuery, m.MediaPath, m.MediaResult, "local_proposal"
    ),
    ("GET", "/providers/{provider_reference}"): bind(
        None, m.EmptyQuery, m.ProviderPath, m.ProviderResult, "local_proposal"
    ),
    ("POST", "/providers/{provider_reference}/activation"): bind(
        m.ActivationIntent,
        m.EmptyQuery,
        m.ProviderPath,
        p.ActivationIntentPlan,
        "local_proposal",
    ),
    ("POST", "/providers/{provider_reference}/authentication-tests"): bind(
        m.ProviderAuthenticationTest,
        m.EmptyQuery,
        m.ProviderPath,
        p.ProviderAuthenticationTestPlan,
        "local_proposal",
    ),
    ("PUT", "/providers/{provider_reference}/draft"): bind(
        m.ProviderDraft,
        m.EmptyQuery,
        m.ProviderPath,
        p.ProviderDraftPlan,
        "local_proposal",
    ),
    ("PUT", "/providers/{provider_reference}/model-reference"): bind(
        m.ProviderModelIntent,
        m.EmptyQuery,
        m.ProviderPath,
        p.ProviderModelIntentPlan,
        "local_proposal",
    ),
    ("GET", "/providers/{provider_reference}/models"): bind(
        None, m.PageQuery, m.ProviderPath, m.ModelsResult, "local_proposal"
    ),
    ("POST", "/providers/{provider_reference}/pause"): bind(
        m.PauseIntent, m.EmptyQuery, m.ProviderPath, p.PauseIntentPlan, "local_proposal"
    ),
    ("POST", "/providers/{provider_reference}/revocation"): bind(
        m.RevocationIntent,
        m.EmptyQuery,
        m.ProviderPath,
        p.RevocationIntentPlan,
        "local_proposal",
    ),
    ("POST", "/providers/{provider_reference}/rotation"): bind(
        m.RotationIntent,
        m.EmptyQuery,
        m.ProviderPath,
        p.RotationIntentPlan,
        "local_proposal",
    ),
    ("POST", "/providers/{provider_reference}/tests"): bind(
        m.ProviderTest,
        m.EmptyQuery,
        m.ProviderPath,
        p.ProviderTestPlan,
        "local_proposal",
    ),
    ("GET", "/retention/{reference_id}"): bind(
        None, m.EmptyQuery, m.ReferencePath, m.RetentionResult, "local_proposal"
    ),
    ("GET", "/sales-memory/{case_id}"): bind(
        None, m.EmptyQuery, m.MemoryPath, m.SalesMemoryResult, "local_proposal"
    ),
    ("PATCH", "/users/{user_id}"): bind(
        m.UserPresentation,
        m.EmptyQuery,
        m.UserPath,
        p.UserPresentationPlan,
        "local_proposal",
    ),
    ("POST", "/users/{user_id}/deactivation"): bind(
        m.UserStatusIntent,
        m.EmptyQuery,
        m.UserPath,
        p.UserStatusIntentPlan,
        "local_proposal",
    ),
    ("POST", "/users/{user_id}/reactivation"): bind(
        m.UserStatusIntent,
        m.EmptyQuery,
        m.UserPath,
        p.UserStatusIntentPlan,
        "local_proposal",
    ),
    ("PUT", "/users/{user_id}/role"): bind(
        m.UserRoleIntent,
        m.EmptyQuery,
        m.UserPath,
        p.UserRoleIntentPlan,
        "local_proposal",
    ),
    ("GET", "/webhooks/{channel}"): bind(
        None,
        m.WebhookVerificationQuery,
        m.ChannelPath,
        m.WebhookVerificationResult,
        "local_proposal",
    ),
    ("POST", "/webhooks/{channel}"): bind(
        m.SyntheticWebhook,
        m.EmptyQuery,
        m.ChannelPath,
        m.WebhookIngressResult,
        "local_proposal",
    ),
    ("PATCH", "/conversations/{conversation_id}/tasks/{task_id}"): bind(
        schemas.TaskDraft,
        m.EmptyQuery,
        m.ConversationTaskPath,
        p.TaskDraftPlan,
        "local_source",
    ),
}
