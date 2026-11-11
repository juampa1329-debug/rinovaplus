"""LOCAL proposals and source-shaped DTOs; not connected-domain approvals.

All ungrounded bounds/references are synthetic transport proposals. Control
fields validate structure only: no idempotency, authorization or concurrency.
"""

import json
from typing import Annotated, Literal, get_args

from pydantic import Field, model_validator

from app.schemas import Channel, DemoReference, LocalModel

Label = Annotated[str, Field(min_length=1, max_length=120)]
Name = Annotated[str, Field(min_length=1, max_length=80)]
Note = Annotated[str, Field(min_length=1, max_length=1000)]
Reason = Annotated[str, Field(min_length=1, max_length=300)]
ReviewReason = Annotated[str, Field(min_length=5, max_length=600)]
Revision = Annotated[int, Field(ge=0)]
Refs = Annotated[list[DemoReference], Field(min_length=1, max_length=20)]
ChannelName = Literal["facebook", "messenger", "instagram", "whatsapp", "tiktok"]
CommentPlatform = Literal["Facebook", "Instagram", "TikTok"]
ReviewState = Literal["pending", "in_review", "reviewed", "observed", "rejected"]
OpaqueReference = Annotated[
    str, Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
]


class ProposalModel(LocalModel):
    @model_validator(mode="before")
    @classmethod
    def strict_boolean_literals(cls, values):
        # Literal[True] otherwise accepts integer 1, even in strict mode.
        if isinstance(values, dict):
            for name, field in cls.model_fields.items():
                args = get_args(field.annotation)
                if (
                    args
                    and all(type(value) is bool for value in args)
                    and name in values
                    and type(values[name]) is not bool
                ):
                    raise ValueError("Invalid local boolean")
        return values

    @model_validator(mode="after")
    def meaningful_values(self):
        for name in type(self).model_fields:
            value = getattr(self, name)
            if isinstance(value, str) and value and not value.strip():
                raise ValueError("Invalid local value")
            if isinstance(value, list):
                if any(isinstance(item, str) and not item.strip() for item in value):
                    raise ValueError("Invalid local collection value")
                encoded = [
                    json.dumps(
                        item.model_dump(mode="json")
                        if isinstance(item, LocalModel)
                        else item,
                        sort_keys=True,
                    )
                    for item in value
                ]
                if len(encoded) != len(set(encoded)):
                    raise ValueError("Invalid local collection")
        return self


class Control(ProposalModel):
    idempotencyReference: DemoReference
    expectedRevision: Revision


class IdentityIntent(Control):
    identityReference: DemoReference
    policyReference: DemoReference
    purpose: Literal["sign_in", "reauthenticate", "challenge", "recover_identity"]


class LoginIntent(IdentityIntent):
    purpose: Literal["sign_in"]


class ReauthenticationIntent(IdentityIntent):
    purpose: Literal["reauthenticate"]


class ChallengeIntent(IdentityIntent):
    purpose: Literal["challenge"]


class IdentityRecoveryIntent(IdentityIntent):
    purpose: Literal["recover_identity"]


class SessionEnd(Control):
    sessionReference: DemoReference
    revocationPolicyReference: DemoReference


class DeactivationIntent(Control):
    reason: Reason
    reviewReference: DemoReference
    policyReference: DemoReference


class ConversationControl(Control):
    target: Literal["human", "ai"]
    reason: Reason
    humanPolicyReference: DemoReference


class ReadIntent(Control):
    lastMessageReference: DemoReference


class SuggestionIntent(Control):
    contextReference: DemoReference
    configurationReference: DemoReference
    evidenceReferences: Refs
    templateReference: DemoReference


class AnalysisIntent(Control):
    contextReference: DemoReference
    configurationReference: DemoReference
    evidenceReferences: Refs
    analysisPolicyReference: DemoReference


class ReactionIntent(Control):
    policyReference: DemoReference
    reactionReference: DemoReference
    intent: Literal["add", "remove"]


class LinkIntent(Control):
    clientReference: DemoReference
    programReference: DemoReference
    scheduleReference: DemoReference
    formPolicyReference: DemoReference


class ReviewStart(Control):
    reviewerReference: DemoReference


class ReviewReopen(Control):
    reviewerReference: DemoReference
    reason: ReviewReason


class CoreRegistrationIntent(Control):
    applicationRevision: Revision
    contractReference: DemoReference
    authorizationEvidenceReference: DemoReference
    reviewReference: DemoReference
    confirmed: Literal[True]

    @model_validator(mode="after")
    def coherent_revision(self):
        if self.applicationRevision != self.expectedRevision:
            raise ValueError("Invalid local revision binding")
        return self


class AssistantReview(Control):
    configurationRevision: Revision
    reviewerReference: DemoReference
    reviewReference: DemoReference


class AssistantTest(Control):
    configurationRevision: Revision
    testReference: DemoReference
    evaluationPolicyReference: DemoReference


class AssistantPublication(Control):
    configurationRevision: Revision
    testReference: DemoReference
    reviewReference: DemoReference
    evaluationReference: DemoReference


class OAuthIntent(Control):
    callbackPolicyReference: DemoReference
    identityPolicyReference: DemoReference


class ChannelDiscovery(Control):
    draftRevision: Revision
    testReference: DemoReference
    capabilityPolicyReference: DemoReference


class ChannelTest(Control):
    draftRevision: Revision
    testReference: DemoReference
    connectionPolicyReference: DemoReference


class ActivationIntent(Control):
    testedRevision: Revision
    evidenceReference: DemoReference
    activationPolicyReference: DemoReference

    @model_validator(mode="after")
    def coherent_revision(self):
        if self.testedRevision != self.expectedRevision:
            raise ValueError("Invalid local revision binding")
        return self


class PauseIntent(Control):
    reason: Reason
    policyReference: DemoReference


class NumberRegistration(Control):
    phoneReference: DemoReference
    wabaReference: DemoReference
    registrationPolicyReference: DemoReference
    evidenceReference: DemoReference


class NumberVerification(Control):
    phoneReference: DemoReference
    wabaReference: DemoReference
    verificationPolicyReference: DemoReference
    verificationEvidenceReference: DemoReference


class MessageEvent(ProposalModel):
    kind: Literal["message"]
    messageReference: DemoReference
    senderReference: DemoReference
    text: Annotated[str, Field(min_length=1, max_length=1500)]
    direction: Literal["incoming", "outgoing"]


class DeliveryEvent(ProposalModel):
    kind: Literal["delivery"]
    messageReference: DemoReference
    deliveryReference: DemoReference
    status: Literal["pending", "uncertain"]


class ReferenceEvent(ProposalModel):
    kind: Literal["reference"]
    objectReference: DemoReference
    evidenceReference: DemoReference


class SyntheticWebhook(ProposalModel):
    eventReference: DemoReference
    channel: ChannelName
    payload: Annotated[
        MessageEvent | DeliveryEvent | ReferenceEvent, Field(discriminator="kind")
    ]


class ProviderDraft(Control):
    displayName: Name
    capability: Literal["text", "stt", "tts"]
    credentialPolicyReference: DemoReference
    versionReference: DemoReference


class ProviderModelIntent(Control):
    modelReference: DemoReference
    capability: Literal["text", "stt", "tts"]


class ProviderAuthenticationTest(Control):
    draftRevision: Revision
    testReference: DemoReference
    credentialPolicyReference: DemoReference


class ProviderTest(Control):
    draftRevision: Revision
    modelRevision: Revision
    testReference: DemoReference
    evaluationPolicyReference: DemoReference


class RotationIntent(Control):
    rotationPolicyReference: DemoReference
    evidenceReference: DemoReference
    reason: Reason


class RevocationIntent(Control):
    revocationPolicyReference: DemoReference
    evidenceReference: DemoReference
    reason: Reason


class ProcessIntent(Control):
    scope: Literal["synthetic_events", "synthetic_queue"]
    eventReferences: Refs
    reconciliationPolicyReference: DemoReference


Scenario = Literal["stable", "provider", "queue", "uncertain"]


class SimulationIntent(Control):
    scenario: Scenario
    fixtureReference: DemoReference


class OperationPause(Control):
    scenario: Scenario
    reason: Reason


class RecoveryChecks(ProposalModel):
    isolation: Literal[True]
    human: Literal[True]
    reconciliation: Literal[True]


class RecoveryReview(Control):
    scenario: Scenario
    reason: Reason
    checks: RecoveryChecks
    evidenceReference: DemoReference


class OperationResume(RecoveryReview):
    recoveryReviewReference: DemoReference


class UserInvitation(Control):
    identityReference: DemoReference
    displayName: Name
    invitationPolicyReference: DemoReference
    roleReferences: Refs


class PresentationPatch(ProposalModel):
    displayName: Name | None = None
    position: Name | None = None
    timezone: Literal["America/Bogota", "UTC"] | None = None

    @model_validator(mode="after")
    def nonempty_patch(self):
        if not self.model_fields_set or any(
            getattr(self, name) is None for name in self.model_fields_set
        ):
            raise ValueError("Invalid local patch")
        return self


class UserPresentation(Control):
    presentation: PresentationPatch


class UserStatusIntent(Control):
    reason: Reason
    identityPolicyReference: DemoReference
    authorizationReviewReference: DemoReference


class UserRoleIntent(Control):
    roleReference: DemoReference
    authorizationReviewReference: DemoReference


class EmailChange(Control):
    contactReference: DemoReference
    identityReference: DemoReference
    emailPolicyReference: DemoReference


class EmailVerification(Control):
    verificationIntentReference: DemoReference
    evidenceReference: DemoReference


class PasswordChange(Control):
    credentialPolicyReference: DemoReference
    changeIntentReference: DemoReference
    reauthenticationReference: DemoReference


class FactorEnrollment(Control):
    enrollmentIntentReference: DemoReference
    factorPolicyReference: DemoReference
    identityReference: DemoReference


class FactorVerification(Control):
    enrollmentIntentReference: DemoReference
    verificationEvidenceReference: DemoReference


class FactorActivation(Control):
    enrollmentIntentReference: DemoReference
    verificationReviewReference: DemoReference
    activationPolicyReference: DemoReference


class FactorRecovery(Control):
    identityReference: DemoReference
    recoveryPolicyReference: DemoReference
    recoveryEvidenceReference: DemoReference


class ExportIntent(Control):
    targetReferences: Refs
    purpose: Literal["subject_review", "authorized_audit"]
    reviewReference: DemoReference
    reauthenticationReference: DemoReference


class DeletionIntent(ExportIntent):
    reason: Reason
    retentionPolicyReference: DemoReference


class MediaMetadata(Control):
    assetReference: DemoReference
    contentType: Literal["audio/ogg", "audio/wav", "image/png", "image/jpeg"]
    byteLength: Annotated[int, Field(ge=1, le=10000000)]
    privacyPolicyReference: DemoReference


class TranscriptionIntent(Control):
    mediaReference: DemoReference
    modelReference: DemoReference
    processingPolicyReference: DemoReference


class SynthesisIntent(Control):
    text: Annotated[str, Field(min_length=1, max_length=1500)]
    voiceReference: DemoReference
    modelReference: DemoReference
    processingPolicyReference: DemoReference


class FallbackIntent(Control):
    textModelReference: DemoReference
    sttModelReference: DemoReference
    ttsModelReference: DemoReference
    fallbackPolicyReference: DemoReference


class FollowupIntent(Control):
    clientReference: DemoReference
    conversationReference: DemoReference
    templateReference: DemoReference
    consentPolicyReference: DemoReference
    scheduleIntentReference: DemoReference


class FollowupCancellation(Control):
    reason: Reason
    cancellationPolicyReference: DemoReference


class SourceMetadata(Control):
    title: Label
    sourceType: Literal["approved_document", "synthetic_note", "catalog_reference"]
    contentReference: DemoReference
    tags: Annotated[list[Name], Field(max_length=20)]
    notes: Annotated[str, Field(max_length=1000)]


class SourcePatch(ProposalModel):
    title: Label | None = None
    tags: Annotated[list[Name], Field(max_length=20)] | None = None
    notes: Annotated[str, Field(max_length=1000)] | None = None

    @model_validator(mode="after")
    def nonempty_patch(self):
        if not self.model_fields_set or any(
            getattr(self, name) is None for name in self.model_fields_set
        ):
            raise ValueError("Invalid local patch")
        return self


class SourceUpdate(Control):
    metadata: SourcePatch


class SourceRemoval(Control):
    reason: Reason
    reviewReference: DemoReference


class IndexIntent(Control):
    sourceReferences: Refs
    sourceRevision: Revision
    indexingPolicyReference: DemoReference


class AliasRow(ProposalModel):
    alias: Name
    sourceReference: DemoReference


class AliasIntent(Control):
    aliases: Annotated[list[AliasRow], Field(min_length=1, max_length=20)]

    @model_validator(mode="after")
    def unique_aliases(self):
        if len({row.alias.strip().casefold() for row in self.aliases}) != len(
            self.aliases
        ):
            raise ValueError("Invalid local alias collection")
        return self


class RetrievalIntent(Control):
    question: Note
    contextReference: DemoReference
    sourceReferences: Refs


class EvaluationIntent(Control):
    question: Note
    expectedSourceReferences: Refs
    criteriaReferences: Refs


class KnowledgePublication(Control):
    indexReference: DemoReference
    evaluationReference: DemoReference
    reviewReference: DemoReference


class CreatorDraft(Control):
    displayName: Name
    platform: Literal["instagram", "tiktok", "youtube", "facebook"]
    handleReference: DemoReference | None = None
    nicheReference: DemoReference | None = None
    countryReference: DemoReference | None = None
    audienceReference: DemoReference | None = None
    engagementReference: DemoReference | None = None
    stageReference: DemoReference | None = None
    contactReference: DemoReference | None = None
    profileReference: DemoReference | None = None


class CampaignDraft(Control):
    name: Name
    objective: Note
    providerReference: DemoReference
    budgetReference: DemoReference


class ContactPlan(Control):
    templateReference: DemoReference
    messageReference: DemoReference
    followupReference: DemoReference


class DeliverableDraft(Control):
    creatorReference: DemoReference
    title: Label
    dueReference: DemoReference
    requirements: Annotated[list[Label], Field(min_length=1, max_length=20)]


class DeliverablePatch(ProposalModel):
    title: Label | None = None
    dueReference: DemoReference | None = None
    requirements: Annotated[list[Label], Field(min_length=1, max_length=20)] | None = (
        None
    )
    reviewReference: DemoReference | None = None

    @model_validator(mode="after")
    def nonempty_patch(self):
        if not self.model_fields_set or any(
            getattr(self, name) is None for name in self.model_fields_set
        ):
            raise ValueError("Invalid local patch")
        return self


class DeliverableUpdate(Control):
    deliverable: DeliverablePatch


class ResourceDraft(Control):
    title: Label
    creatorReference: DemoReference
    campaignReference: DemoReference
    contentReference: DemoReference
    hook: Note | None = None
    copyText: Note | None = None
    brollReference: DemoReference | None = None
    callToAction: Note | None = None


class RightsReview(Control):
    contractReference: DemoReference
    reviewerReference: DemoReference
    scopeEvidenceReference: DemoReference
    periodEvidenceReference: DemoReference


class RightsRevocation(RightsReview):
    reason: Reason


class PerformanceAnalysis(Control):
    analysisPolicyReference: DemoReference
    evidenceReferences: Refs


class SparkPreflight(Control):
    rightsReviewReference: DemoReference
    capabilityEvaluationReference: DemoReference
    authorizationPolicyReference: DemoReference


# Named query shapes; transport limits are not business defaults.
class EmptyQuery(ProposalModel):
    """No semantic query fields for singleton/detail operations."""


class PageQuery(ProposalModel):
    limit: Annotated[int, Field(ge=1, le=100)] = 50
    offset: Annotated[int, Field(ge=0, le=10000)] = 0


class ClientQuery(PageQuery):
    search: Annotated[str, Field(min_length=1, max_length=120)] | None = None
    stage: Name | None = None


class ConversationQuery(PageQuery):
    channel: Literal["WhatsApp", "Facebook", "Instagram", "TikTok"] | None = None
    mode: Literal["human", "ai"] | None = None


class CommentQuery(PageQuery):
    platform: CommentPlatform | None = None


class ApplicationQuery(PageQuery):
    search: Annotated[str, Field(min_length=1, max_length=120)] | None = None
    status: ReviewState | None = None
    program: Name | None = None


class SourceQuery(PageQuery):
    sourceType: (
        Literal["approved_document", "synthetic_note", "catalog_reference"] | None
    ) = None


class TimelineQuery(PageQuery):
    eventReference: DemoReference | None = None


class CreatorQuery(PageQuery):
    platform: Literal["instagram", "tiktok", "youtube", "facebook"] | None = None


class ProviderQuery(PageQuery):
    capability: Literal["text", "stt", "tts"] | None = None


class FollowupQuery(PageQuery):
    clientReference: DemoReference | None = None
    status: Literal["planned", "cancellation_proposed"] | None = None


class EmptyPath(ProposalModel):
    """No path values."""


class ClientPath(ProposalModel):
    client_id: OpaqueReference


class ConversationPath(ProposalModel):
    conversation_id: OpaqueReference


class ConversationTaskPath(ConversationPath):
    task_id: OpaqueReference


class CommentPath(ProposalModel):
    comment_id: OpaqueReference


class ProgramPath(ProposalModel):
    program_id: OpaqueReference


class ApplicationLinkPath(ProposalModel):
    link_reference: OpaqueReference


class ApplicationPath(ProposalModel):
    application_id: OpaqueReference


class SessionPath(ProposalModel):
    session_id: OpaqueReference


class ChannelPath(ProposalModel):
    channel: Channel


class ProviderPath(ProposalModel):
    provider_reference: OpaqueReference


class UserPath(ProposalModel):
    user_id: OpaqueReference


class MediaPath(ProposalModel):
    media_reference: OpaqueReference


class FollowupPath(ProposalModel):
    follow_up_id: OpaqueReference


class SourcePath(ProposalModel):
    source_id: OpaqueReference


class MemoryPath(ProposalModel):
    case_id: OpaqueReference


class ReferencePath(ProposalModel):
    reference_id: OpaqueReference


class CreatorPath(ProposalModel):
    creator_id: OpaqueReference


class CampaignPath(ProposalModel):
    campaign_id: OpaqueReference


class DeliverablePath(ProposalModel):
    deliverable_id: OpaqueReference


class ResourcePath(ProposalModel):
    resource_id: OpaqueReference


class CallbackQuery(ProposalModel):
    authorizationEventReference: DemoReference


class WebhookVerificationQuery(ProposalModel):
    verificationReference: DemoReference


class SessionRevocationQuery(ProposalModel):
    revocationIntentReference: DemoReference
    expectedRevision: Revision


# Planned read results: never returned by the business stubs.
class PlannedResult(ProposalModel):
    execution: Literal["planned_not_executed"] = "planned_not_executed"


class IdentityDescriptor(ProposalModel):
    identityReference: DemoReference
    displayName: Name
    policyReference: DemoReference


class MeResult(PlannedResult):
    identity: IdentityDescriptor


class SessionDescriptor(ProposalModel):
    sessionReference: DemoReference
    identityReference: DemoReference
    sessionPolicyReference: DemoReference


class SessionsResult(PlannedResult):
    sessions: Annotated[list[SessionDescriptor], Field(max_length=100)]


class OverviewResult(PlannedResult):
    availability: Literal["unconfigured", "synthetic_only"]
    clientCount: Annotated[int, Field(ge=0)] | None
    conversationCount: Annotated[int, Field(ge=0)] | None
    humanPendingReferences: Annotated[list[DemoReference], Field(max_length=100)]


class ClientRecord(ProposalModel):
    id: OpaqueReference
    name: Annotated[str, Field(max_length=1000)]
    phone: Annotated[str, Field(max_length=1000)]
    city: Annotated[str, Field(max_length=1000)]
    program: Annotated[str, Field(max_length=1000)]
    schedule: Annotated[str, Field(max_length=1000)]
    stage: Annotated[str, Field(max_length=1000)]
    tags: Annotated[str, Field(max_length=1000)]
    notes: Annotated[str, Field(max_length=1000)]
    type: Annotated[str, Field(max_length=1000)]
    interests: Annotated[str, Field(max_length=1000)]
    customValues: Annotated[
        dict[Name, Annotated[str, Field(max_length=1000)]], Field(max_length=100)
    ]


class ClientsResult(PlannedResult):
    clients: Annotated[list[ClientRecord], Field(max_length=100)]


class ClientResult(PlannedResult):
    client: ClientRecord


class TimelineEntry(ProposalModel):
    eventReference: DemoReference
    description: Note
    evidenceReference: DemoReference


class ClientTimelineResult(PlannedResult):
    clientReference: DemoReference
    timeline: Annotated[list[TimelineEntry], Field(max_length=100)]


class StageRecord(ProposalModel):
    key: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")]
    label: Annotated[str, Field(min_length=1, max_length=60)]
    probability: Annotated[float, Field(ge=0, le=100)]


class FieldRecord(ProposalModel):
    key: Name
    label: Label
    type: Literal["Text", "Number", "List", "Date", "Boolean", "Email", "Phone", "URL"]
    options: Annotated[list[Name], Field(max_length=100)]
    active: bool


class CrmResult(PlannedResult):
    stages: Annotated[list[StageRecord], Field(min_length=1, max_length=100)]
    tags: Annotated[list[Name], Field(max_length=100)]
    fields: Annotated[list[FieldRecord], Field(max_length=100)]


class MessageRecord(ProposalModel):
    id: OpaqueReference
    body: Annotated[str, Field(min_length=1, max_length=1500)]
    direction: Literal["incoming", "outgoing"]


class TaskRecord(ProposalModel):
    id: OpaqueReference
    title: Label
    due: Annotated[str, Field(max_length=100)]
    status: Literal["Pendiente", "Completada", "Cancelada"]


class WorkflowEvent(ProposalModel):
    id: OpaqueReference
    at: Annotated[str, Field(max_length=100)]
    description: Note


class WorkflowRecord(ProposalModel):
    state: Literal["Abierta", "En espera", "Cerrada"]
    priority: Literal["Baja", "Normal", "Alta", "Urgente"]
    assignee: Name
    revision: Revision
    tasks: Annotated[list[TaskRecord], Field(max_length=100)]
    events: Annotated[list[WorkflowEvent], Field(max_length=100)]


class ThreadRecord(ProposalModel):
    clientId: OpaqueReference
    unread: bool
    mode: Literal["human", "ai"]
    channel: Literal["WhatsApp", "Facebook", "Instagram", "TikTok"]
    messages: Annotated[list[MessageRecord], Field(max_length=100)]
    workflow: WorkflowRecord


class ConversationsResult(PlannedResult):
    conversations: Annotated[list[ThreadRecord], Field(max_length=100)]


class ConversationResult(PlannedResult):
    conversation: ThreadRecord


class MessagesResult(PlannedResult):
    messages: Annotated[list[MessageRecord], Field(max_length=100)]


class TasksResult(PlannedResult):
    tasks: Annotated[list[TaskRecord], Field(max_length=100)]


class EventsResult(PlannedResult):
    events: Annotated[list[WorkflowEvent], Field(max_length=100)]


class DeliveryRecord(ProposalModel):
    messageReference: DemoReference
    status: Literal["pending", "uncertain"]
    evidenceReference: DemoReference


class DeliveriesResult(PlannedResult):
    deliveries: Annotated[list[DeliveryRecord], Field(max_length=100)]


class CommentReplyRecord(ProposalModel):
    id: OpaqueReference
    body: Note


class CommentRecord(ProposalModel):
    id: OpaqueReference
    platform: Literal["Facebook", "Instagram", "TikTok"]
    author: Name
    post: Note
    body: Note
    status: Literal["Pendiente", "Respondido"]
    replies: Annotated[list[CommentReplyRecord], Field(max_length=100)]


class CommentsResult(PlannedResult):
    comments: Annotated[list[CommentRecord], Field(max_length=100)]


class CommentResult(PlannedResult):
    comment: CommentRecord


class CatalogRecord(ProposalModel):
    reference: DemoReference
    displayName: Label
    sourceAvailability: Literal["unconfigured", "synthetic_only"]


class ProgramsResult(PlannedResult):
    programs: Annotated[list[CatalogRecord], Field(max_length=100)]


class ProgramResult(PlannedResult):
    program: CatalogRecord


class SchedulesResult(PlannedResult):
    schedules: Annotated[list[CatalogRecord], Field(max_length=100)]


class AttentionHoursResult(PlannedResult):
    attentionPolicyReference: DemoReference
    sourceAvailability: Literal["unconfigured", "synthetic_only"]
    displayNote: Note


class ApplicationLinkResult(PlannedResult):
    linkReference: DemoReference
    status: Literal["valid", "expired", "used", "invalid"]
    schemaReference: DemoReference


class ReviewHistory(ProposalModel):
    status: ReviewState
    reason: Annotated[str, Field(max_length=600)]
    at: Annotated[str, Field(max_length=100)]
    actor: Name


class ReviewRecord(ProposalModel):
    id: OpaqueReference
    name: Annotated[str, Field(max_length=100)]
    email: Annotated[str, Field(max_length=160)]
    program: Label
    schedule: Label
    syntheticConfirmed: bool
    status: ReviewState
    history: Annotated[list[ReviewHistory], Field(max_length=100)]


class ApplicationsResult(PlannedResult):
    applications: Annotated[list[ReviewRecord], Field(max_length=100)]


class ApplicationResult(PlannedResult):
    application: ReviewRecord


class AssistantConfigurationResult(PlannedResult):
    assistantName: Name
    style: Literal["Claro y profesional", "Cercano y respetuoso", "Breve y directo"]
    instructions: Annotated[str, Field(max_length=1000)]
    configurationRevision: Revision
    reviewReference: DemoReference | None


class CapabilityEvidence(ProposalModel):
    capabilityReference: DemoReference
    evidenceReference: DemoReference
    status: Literal["unverified", "local_proposal"]


class ChannelProfile(ProposalModel):
    channel: ChannelName
    connectedStatus: Literal["approval_pending"]
    appReference: DemoReference | None
    assetReference: DemoReference | None
    portfolioReference: DemoReference | None
    pageReference: DemoReference | None
    wabaReference: DemoReference | None
    phoneReference: DemoReference | None
    accountReference: DemoReference | None
    usernameReference: DemoReference | None
    clientKeyReference: DemoReference | None
    openIdReference: DemoReference | None
    tokenReference: DemoReference | None
    secretReference: DemoReference | None
    verifyReference: DemoReference | None
    callbackReference: DemoReference | None
    webhookReference: DemoReference | None
    versionReference: DemoReference | None
    requestedScopesReference: DemoReference | None
    grantedScopesReference: DemoReference | None
    accessEvidenceReference: DemoReference | None


class ChannelsResult(PlannedResult):
    channels: Annotated[list[ChannelProfile], Field(max_length=5)]


class ChannelResult(PlannedResult):
    channel: ChannelProfile


class ChannelCapabilitiesResult(PlannedResult):
    capabilities: Annotated[list[CapabilityEvidence], Field(max_length=20)]


class WebhookReferenceResult(PlannedResult):
    webhookReference: DemoReference
    callbackPolicyReference: DemoReference
    verificationPolicyReference: DemoReference


class CallbackResult(PlannedResult):
    authorizationEventReference: DemoReference
    reviewReference: DemoReference


class NumberDescriptor(ProposalModel):
    phoneReference: DemoReference
    wabaReference: DemoReference
    verificationEvidenceReference: DemoReference | None
    status: Literal["unverified", "approval_pending"]


class NumbersResult(PlannedResult):
    numbers: Annotated[list[NumberDescriptor], Field(max_length=100)]


class WebhookVerificationResult(PlannedResult):
    verificationReference: DemoReference
    contractReference: DemoReference


class WebhookIngressResult(PlannedResult):
    eventReference: DemoReference
    ingressContractReference: DemoReference
    disposition: Literal["not_acknowledged"]


class ProviderDescriptor(ProposalModel):
    providerReference: DemoReference
    displayName: Name
    capability: Literal["text", "stt", "tts"]
    credentialPolicyReference: DemoReference
    connectedStatus: Literal["approval_pending"]


class ProvidersResult(PlannedResult):
    providers: Annotated[list[ProviderDescriptor], Field(max_length=100)]


class ProviderResult(PlannedResult):
    provider: ProviderDescriptor


class ModelDescriptor(ProposalModel):
    modelReference: DemoReference
    displayName: Name
    capability: Literal["text", "stt", "tts"]
    evaluationReference: DemoReference | None


class ModelsResult(PlannedResult):
    models: Annotated[list[ModelDescriptor], Field(max_length=100)]


class DiagnosticCheck(ProposalModel):
    id: Literal["isolation", "human", "reconciliation"]
    label: Note
    checked: bool


class DiagnosticHistory(ProposalModel):
    at: Annotated[str, Field(max_length=100)]
    label: Label
    reason: Reason


class OperationRecord(ProposalModel):
    id: Literal[
        "ops-demo-stable", "ops-demo-provider", "ops-demo-queue", "ops-demo-uncertain"
    ]
    name: Label
    description: Note
    status: Literal["stable", "degraded", "paused", "recovering"]
    incident: Literal["none", "open", "in_review", "closed"]
    revision: Revision
    checks: Annotated[list[DiagnosticCheck], Field(min_length=3, max_length=3)]
    history: Annotated[list[DiagnosticHistory], Field(max_length=100)]

    @model_validator(mode="after")
    def complete_checks(self):
        if {check.id for check in self.checks} != {
            "isolation",
            "human",
            "reconciliation",
        }:
            raise ValueError("Invalid local checklist")
        return self


class DiagnosticsResult(PlannedResult):
    availability: Literal["unconfigured", "synthetic_only"]
    scenarios: Annotated[list[OperationRecord], Field(max_length=4)]


class EndpointDiagnostic(ProposalModel):
    operationReference: DemoReference
    evidenceReference: DemoReference
    availability: Literal["unconfigured", "synthetic_only"]


class DiagnosticEndpointsResult(PlannedResult):
    endpoints: Annotated[list[EndpointDiagnostic], Field(max_length=100)]


class DiagnosticEventsResult(PlannedResult):
    events: Annotated[list[TimelineEntry], Field(max_length=100)]


class QueueDescriptor(ProposalModel):
    queueReference: DemoReference
    reconciliationReference: DemoReference
    availability: Literal["unconfigured"]
    pendingCount: Annotated[int, Field(ge=0)] | None


class DiagnosticQueuesResult(PlannedResult):
    queues: Annotated[list[QueueDescriptor], Field(max_length=100)]


class DiagnosticIncidentsResult(PlannedResult):
    incidents: Annotated[list[OperationRecord], Field(max_length=4)]


class UserDescriptor(ProposalModel):
    userReference: DemoReference
    identityReference: DemoReference
    displayName: Name
    roleReferences: Annotated[list[DemoReference], Field(max_length=20)]
    identityPolicyReference: DemoReference


class UsersResult(PlannedResult):
    users: Annotated[list[UserDescriptor], Field(max_length=100)]


class RoleDescriptor(ProposalModel):
    roleReference: DemoReference
    displayName: Name
    authorizationPolicyReference: DemoReference


class RolesResult(PlannedResult):
    roles: Annotated[list[RoleDescriptor], Field(max_length=100)]


class ProfileResult(PlannedResult):
    profileName: Name
    position: Name
    timezone: Literal["America/Bogota", "UTC"]
    emailReference: DemoReference
    photoReference: DemoReference
    identityReference: DemoReference
    verificationReference: DemoReference | None


class SecurityResult(PlannedResult):
    posture: Literal["not_configured"]
    identityPolicyReference: DemoReference
    factorPolicyReference: DemoReference
    auditPolicyReference: DemoReference


class AuditEntry(ProposalModel):
    eventReference: DemoReference
    actorReference: DemoReference
    intentReference: DemoReference
    evidenceReference: DemoReference


class AuditResult(PlannedResult):
    auditEvents: Annotated[list[AuditEntry], Field(max_length=100)]


class MediaResult(PlannedResult):
    mediaReference: DemoReference
    assetReference: DemoReference
    contentType: Literal["audio/ogg", "audio/wav", "image/png", "image/jpeg"]
    privacyPolicyReference: DemoReference


class FollowupRecord(ProposalModel):
    followupReference: DemoReference
    clientReference: DemoReference
    conversationReference: DemoReference
    scheduleIntentReference: DemoReference
    status: Literal["planned", "cancellation_proposed"]


class FollowupsResult(PlannedResult):
    followups: Annotated[list[FollowupRecord], Field(max_length=100)]


class SourceRecord(ProposalModel):
    sourceReference: DemoReference
    title: Label
    sourceType: Literal["approved_document", "synthetic_note", "catalog_reference"]
    contentReference: DemoReference
    tags: Annotated[list[Name], Field(max_length=20)]
    notes: Annotated[str, Field(max_length=1000)]
    revision: Revision


class SourcesResult(PlannedResult):
    sources: Annotated[list[SourceRecord], Field(max_length=100)]


class AliasesResult(PlannedResult):
    aliases: Annotated[list[AliasRow], Field(max_length=100)]


class MemoryRecord(ProposalModel):
    caseReference: DemoReference
    contextReference: DemoReference
    sourceReferences: Refs
    retentionPolicyReference: DemoReference


class SalesMemoriesResult(PlannedResult):
    memories: Annotated[list[MemoryRecord], Field(max_length=100)]


class SalesMemoryResult(PlannedResult):
    memory: MemoryRecord


class RetentionRecord(ProposalModel):
    contactReference: DemoReference
    relationshipReference: DemoReference
    displayName: Name
    nextReviewReference: DemoReference
    scope: Literal["conditional_pending"]


class RetentionListResult(PlannedResult):
    contacts: Annotated[list[RetentionRecord], Field(max_length=100)]


class RetentionResult(PlannedResult):
    contact: RetentionRecord


class CorporateRecord(ProposalModel):
    organizationReference: DemoReference
    displayName: Name
    contactReference: DemoReference
    interactionReferences: Annotated[list[DemoReference], Field(max_length=100)]
    scope: Literal["conditional_pending"]


class CorporatesResult(PlannedResult):
    organizations: Annotated[list[CorporateRecord], Field(max_length=100)]


class CorporateResult(PlannedResult):
    organization: CorporateRecord


class CreatorRecord(ProposalModel):
    creatorReference: DemoReference
    displayName: Name
    platform: Literal["instagram", "tiktok", "youtube", "facebook"]
    profileReference: DemoReference | None
    contactReference: DemoReference | None


class CreatorsResult(PlannedResult):
    creators: Annotated[list[CreatorRecord], Field(max_length=100)]


class CampaignRecord(ProposalModel):
    campaignReference: DemoReference
    name: Name
    objective: Note
    providerReference: DemoReference
    budgetReference: DemoReference


class CampaignsResult(PlannedResult):
    campaigns: Annotated[list[CampaignRecord], Field(max_length=100)]


class ResourceRecord(ProposalModel):
    resourceReference: DemoReference
    title: Label
    creatorReference: DemoReference
    campaignReference: DemoReference
    contentReference: DemoReference
    rightsReviewReference: DemoReference | None


class ResourcesResult(PlannedResult):
    resources: Annotated[list[ResourceRecord], Field(max_length=100)]


class CreatorAuditResult(PlannedResult):
    creatorAuditEvents: Annotated[list[AuditEntry], Field(max_length=100)]


class SuggestionResult(PlannedResult):
    templateReference: DemoReference
    proposedText: Annotated[str, Field(min_length=1, max_length=1500)]
    evidenceReferences: Refs
    humanReview: Literal["required"]


class AnalysisResult(PlannedResult):
    contextReference: DemoReference
    signalReferences: Refs
    derivation: Literal["deterministic_local_proposal"]
    humanReview: Literal["required"]


class TranscriptionResult(PlannedResult):
    mediaReference: DemoReference
    proposedTranscript: Annotated[str, Field(min_length=1, max_length=1500)]
    evaluationReference: DemoReference


class SynthesisResult(PlannedResult):
    proposedMediaReference: DemoReference
    voiceReference: DemoReference
    evaluationReference: DemoReference


class Citation(ProposalModel):
    sourceReference: DemoReference
    excerptReference: DemoReference


class Snippet(ProposalModel):
    proposedText: Note
    citations: Annotated[list[Citation], Field(min_length=1, max_length=20)]


class RetrievalResult(PlannedResult):
    snippets: Annotated[list[Snippet], Field(max_length=20)]
    evaluationReference: DemoReference


class EvaluationResult(PlannedResult):
    evaluationReference: DemoReference
    criteriaReferences: Refs
    evidenceReferences: Refs
    outcome: Literal["not_evaluated"]
