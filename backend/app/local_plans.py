"""Typed planned mutation results; never runtime execution receipts."""

from typing import Literal

from app import local_models as m
from app import schemas


class ActivationIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.ActivationIntent
    humanReview: Literal["required"]


class AliasIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.AliasIntent
    humanReview: Literal["required"]


class AnalysisIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.AnalysisIntent
    humanReview: Literal["required"]


class ApplicationDraftPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: schemas.ApplicationDraft
    humanReview: Literal["required"]


class AssistantDraftPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: schemas.AssistantDraft
    humanReview: Literal["required"]


class AssistantPublicationPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.AssistantPublication
    humanReview: Literal["required"]


class AssistantReviewPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.AssistantReview
    humanReview: Literal["required"]


class AssistantTestPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.AssistantTest
    humanReview: Literal["required"]


class CampaignDraftPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.CampaignDraft
    humanReview: Literal["required"]


class ChallengeIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.ChallengeIntent
    humanReview: Literal["required"]


class ChannelDiscoveryPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.ChannelDiscovery
    humanReview: Literal["required"]


class ChannelDraftPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: schemas.ChannelDraft
    humanReview: Literal["required"]


class ChannelTestPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.ChannelTest
    humanReview: Literal["required"]


class ClientDraftPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: schemas.ClientDraft
    humanReview: Literal["required"]


class ContactPlanPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.ContactPlan
    humanReview: Literal["required"]


class ConversationControlPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.ConversationControl
    humanReview: Literal["required"]


class CoreRegistrationIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.CoreRegistrationIntent
    humanReview: Literal["required"]


class CreatorDraftPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.CreatorDraft
    humanReview: Literal["required"]


class CrmDraftPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: schemas.CrmDraft
    humanReview: Literal["required"]


class DeactivationIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.DeactivationIntent
    humanReview: Literal["required"]


class DeletionIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.DeletionIntent
    humanReview: Literal["required"]


class DeliverableDraftPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.DeliverableDraft
    humanReview: Literal["required"]


class DeliverableUpdatePlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.DeliverableUpdate
    humanReview: Literal["required"]


class EmailChangePlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.EmailChange
    humanReview: Literal["required"]


class EmailVerificationPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.EmailVerification
    humanReview: Literal["required"]


class EvaluationIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.EvaluationIntent
    humanReview: Literal["required"]


class ExportIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.ExportIntent
    humanReview: Literal["required"]


class FactorActivationPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.FactorActivation
    humanReview: Literal["required"]


class FactorEnrollmentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.FactorEnrollment
    humanReview: Literal["required"]


class FactorRecoveryPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.FactorRecovery
    humanReview: Literal["required"]


class FactorVerificationPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.FactorVerification
    humanReview: Literal["required"]


class FallbackIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.FallbackIntent
    humanReview: Literal["required"]


class FollowupCancellationPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.FollowupCancellation
    humanReview: Literal["required"]


class FollowupIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.FollowupIntent
    humanReview: Literal["required"]


class IdentityRecoveryIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.IdentityRecoveryIntent
    humanReview: Literal["required"]


class IndexIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.IndexIntent
    humanReview: Literal["required"]


class KnowledgePublicationPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.KnowledgePublication
    humanReview: Literal["required"]


class LinkIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.LinkIntent
    humanReview: Literal["required"]


class LoginIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.LoginIntent
    humanReview: Literal["required"]


class MediaMetadataPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.MediaMetadata
    humanReview: Literal["required"]


class MessageDraftPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: schemas.MessageDraft
    humanReview: Literal["required"]


class NumberRegistrationPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.NumberRegistration
    humanReview: Literal["required"]


class NumberVerificationPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.NumberVerification
    humanReview: Literal["required"]


class OAuthIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.OAuthIntent
    humanReview: Literal["required"]


class OperationPausePlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.OperationPause
    humanReview: Literal["required"]


class OperationResumePlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.OperationResume
    humanReview: Literal["required"]


class PasswordChangePlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.PasswordChange
    humanReview: Literal["required"]


class PauseIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.PauseIntent
    humanReview: Literal["required"]


class PerformanceAnalysisPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.PerformanceAnalysis
    humanReview: Literal["required"]


class ProcessIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.ProcessIntent
    humanReview: Literal["required"]


class ProfileDraftPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: schemas.ProfileDraft
    humanReview: Literal["required"]


class ProviderAuthenticationTestPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.ProviderAuthenticationTest
    humanReview: Literal["required"]


class ProviderDraftPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.ProviderDraft
    humanReview: Literal["required"]


class ProviderModelIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.ProviderModelIntent
    humanReview: Literal["required"]


class ProviderTestPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.ProviderTest
    humanReview: Literal["required"]


class ReactionIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.ReactionIntent
    humanReview: Literal["required"]


class ReadIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.ReadIntent
    humanReview: Literal["required"]


class ReauthenticationIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.ReauthenticationIntent
    humanReview: Literal["required"]


class RecoveryReviewPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.RecoveryReview
    humanReview: Literal["required"]


class ResourceDraftPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.ResourceDraft
    humanReview: Literal["required"]


class RetrievalIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.RetrievalIntent
    humanReview: Literal["required"]


class ReviewDraftPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: schemas.ReviewDraft
    humanReview: Literal["required"]


class ReviewReopenPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.ReviewReopen
    humanReview: Literal["required"]


class ReviewStartPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.ReviewStart
    humanReview: Literal["required"]


class RevocationIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.RevocationIntent
    humanReview: Literal["required"]


class RightsReviewPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.RightsReview
    humanReview: Literal["required"]


class RightsRevocationPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.RightsRevocation
    humanReview: Literal["required"]


class RotationIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.RotationIntent
    humanReview: Literal["required"]


class SessionEndPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.SessionEnd
    humanReview: Literal["required"]


class SimulationIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.SimulationIntent
    humanReview: Literal["required"]


class SourceMetadataPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.SourceMetadata
    humanReview: Literal["required"]


class SourceRemovalPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.SourceRemoval
    humanReview: Literal["required"]


class SourceUpdatePlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.SourceUpdate
    humanReview: Literal["required"]


class SparkPreflightPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.SparkPreflight
    humanReview: Literal["required"]


class SuggestionIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.SuggestionIntent
    humanReview: Literal["required"]


class SynthesisIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.SynthesisIntent
    humanReview: Literal["required"]


class SyntheticWebhookPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.SyntheticWebhook
    humanReview: Literal["required"]


class TaskDraftPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: schemas.TaskDraft
    humanReview: Literal["required"]


class TranscriptionIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.TranscriptionIntent
    humanReview: Literal["required"]


class UserInvitationPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.UserInvitation
    humanReview: Literal["required"]


class UserPresentationPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.UserPresentation
    humanReview: Literal["required"]


class UserRoleIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.UserRoleIntent
    humanReview: Literal["required"]


class UserStatusIntentPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: m.UserStatusIntent
    humanReview: Literal["required"]


class WorkflowDraftPlan(m.PlannedResult):
    proposalReference: schemas.DemoReference
    intent: schemas.WorkflowDraft
    humanReview: Literal["required"]


class SessionRevocationPlan(m.PlannedResult):
    sessionReference: schemas.DemoReference
    revocationIntentReference: schemas.DemoReference
    expectedRevision: m.Revision
    humanReview: Literal["required"]
