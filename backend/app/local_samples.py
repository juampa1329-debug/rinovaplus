"""Canonical synthetic examples. Not user data or runtime business state."""

SAMPLES = {
    "LinkIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "clientReference": "DEMO-clientReference",
        "programReference": "DEMO-programReference",
        "scheduleReference": "DEMO-scheduleReference",
        "formPolicyReference": "DEMO-formPolicyReference",
    },
    "EmptyQuery": {},
    "EmptyPath": {},
    "LinkIntentPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "clientReference": "DEMO-clientReference",
            "programReference": "DEMO-programReference",
            "scheduleReference": "DEMO-scheduleReference",
            "formPolicyReference": "DEMO-formPolicyReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "ApplicationQuery": {},
    "ApplicationsResult": {
        "applications": [
            {
                "id": "DEMO-001",
                "name": "Synthetic demo",
                "email": "demo@example.invalid",
                "program": "Synthetic demo",
                "schedule": "Synthetic demo",
                "syntheticConfirmed": True,
                "status": "pending",
                "history": [
                    {
                        "status": "pending",
                        "reason": "Synthetic demo",
                        "at": "2026-10-14T00:00:00Z",
                        "actor": "Synthetic demo",
                    }
                ],
            }
        ],
        "execution": "planned_not_executed",
    },
    "AssistantConfigurationResult": {
        "assistantName": "Synthetic demo",
        "style": "Claro y profesional",
        "instructions": "Synthetic demo",
        "configurationRevision": 1,
        "reviewReference": "DEMO-reviewReference",
        "execution": "planned_not_executed",
    },
    "AssistantDraft": {},
    "AssistantDraftPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {},
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "FallbackIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "textModelReference": "DEMO-textModelReference",
        "sttModelReference": "DEMO-sttModelReference",
        "ttsModelReference": "DEMO-ttsModelReference",
        "fallbackPolicyReference": "DEMO-fallbackPolicyReference",
    },
    "FallbackIntentPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "textModelReference": "DEMO-textModelReference",
            "sttModelReference": "DEMO-sttModelReference",
            "ttsModelReference": "DEMO-ttsModelReference",
            "fallbackPolicyReference": "DEMO-fallbackPolicyReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "AssistantPublication": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "configurationRevision": 1,
        "testReference": "DEMO-testReference",
        "reviewReference": "DEMO-reviewReference",
        "evaluationReference": "DEMO-evaluationReference",
    },
    "AssistantPublicationPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "configurationRevision": 1,
            "testReference": "DEMO-testReference",
            "reviewReference": "DEMO-reviewReference",
            "evaluationReference": "DEMO-evaluationReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "AssistantReview": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "configurationRevision": 1,
        "reviewerReference": "DEMO-reviewerReference",
        "reviewReference": "DEMO-reviewReference",
    },
    "AssistantReviewPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "configurationRevision": 1,
            "reviewerReference": "DEMO-reviewerReference",
            "reviewReference": "DEMO-reviewReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "AssistantTest": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "configurationRevision": 1,
        "testReference": "DEMO-testReference",
        "evaluationPolicyReference": "DEMO-evaluationPolicyReference",
    },
    "AssistantTestPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "configurationRevision": 1,
            "testReference": "DEMO-testReference",
            "evaluationPolicyReference": "DEMO-evaluationPolicyReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "ChallengeIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "identityReference": "DEMO-identityReference",
        "policyReference": "DEMO-policyReference",
        "purpose": "challenge",
    },
    "ChallengeIntentPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "identityReference": "DEMO-identityReference",
            "policyReference": "DEMO-policyReference",
            "purpose": "challenge",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "LoginIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "identityReference": "DEMO-identityReference",
        "policyReference": "DEMO-policyReference",
        "purpose": "sign_in",
    },
    "LoginIntentPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "identityReference": "DEMO-identityReference",
            "policyReference": "DEMO-policyReference",
            "purpose": "sign_in",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "SessionEnd": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "sessionReference": "DEMO-sessionReference",
        "revocationPolicyReference": "DEMO-revocationPolicyReference",
    },
    "SessionEndPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "sessionReference": "DEMO-sessionReference",
            "revocationPolicyReference": "DEMO-revocationPolicyReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "MeResult": {
        "identity": {
            "identityReference": "DEMO-identityReference",
            "displayName": "Synthetic demo",
            "policyReference": "DEMO-policyReference",
        },
        "execution": "planned_not_executed",
    },
    "ReauthenticationIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "identityReference": "DEMO-identityReference",
        "policyReference": "DEMO-policyReference",
        "purpose": "reauthenticate",
    },
    "ReauthenticationIntentPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "identityReference": "DEMO-identityReference",
            "policyReference": "DEMO-policyReference",
            "purpose": "reauthenticate",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "IdentityRecoveryIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "identityReference": "DEMO-identityReference",
        "policyReference": "DEMO-policyReference",
        "purpose": "recover_identity",
    },
    "IdentityRecoveryIntentPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "identityReference": "DEMO-identityReference",
            "policyReference": "DEMO-policyReference",
            "purpose": "recover_identity",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "PageQuery": {},
    "SessionsResult": {
        "sessions": [
            {
                "sessionReference": "DEMO-sessionReference",
                "identityReference": "DEMO-identityReference",
                "sessionPolicyReference": "DEMO-sessionPolicyReference",
            }
        ],
        "execution": "planned_not_executed",
    },
    "AttentionHoursResult": {
        "attentionPolicyReference": "DEMO-attentionPolicyReference",
        "sourceAvailability": "unconfigured",
        "displayNote": "Synthetic demo",
        "execution": "planned_not_executed",
    },
    "ProgramsResult": {
        "programs": [
            {
                "reference": "DEMO-reference",
                "displayName": "Synthetic demo",
                "sourceAvailability": "unconfigured",
            }
        ],
        "execution": "planned_not_executed",
    },
    "SchedulesResult": {
        "schedules": [
            {
                "reference": "DEMO-reference",
                "displayName": "Synthetic demo",
                "sourceAvailability": "unconfigured",
            }
        ],
        "execution": "planned_not_executed",
    },
    "ChannelsResult": {
        "channels": [
            {
                "channel": "facebook",
                "connectedStatus": "approval_pending",
                "appReference": "DEMO-appReference",
                "assetReference": "DEMO-assetReference",
                "portfolioReference": "DEMO-portfolioReference",
                "pageReference": "DEMO-pageReference",
                "wabaReference": "DEMO-wabaReference",
                "phoneReference": "DEMO-phoneReference",
                "accountReference": "DEMO-accountReference",
                "usernameReference": "DEMO-usernameReference",
                "clientKeyReference": "DEMO-clientKeyReference",
                "openIdReference": "DEMO-openIdReference",
                "tokenReference": "DEMO-tokenReference",
                "secretReference": "DEMO-secretReference",
                "verifyReference": "DEMO-verifyReference",
                "callbackReference": "DEMO-callbackReference",
                "webhookReference": "DEMO-webhookReference",
                "versionReference": "DEMO-versionReference",
                "requestedScopesReference": "DEMO-requestedScopesReference",
                "grantedScopesReference": "DEMO-grantedScopesReference",
                "accessEvidenceReference": "DEMO-accessEvidenceReference",
            }
        ],
        "execution": "planned_not_executed",
    },
    "NumberRegistration": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "phoneReference": "DEMO-phoneReference",
        "wabaReference": "DEMO-wabaReference",
        "registrationPolicyReference": "DEMO-registrationPolicyReference",
        "evidenceReference": "DEMO-evidenceReference",
    },
    "NumberRegistrationPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "phoneReference": "DEMO-phoneReference",
            "wabaReference": "DEMO-wabaReference",
            "registrationPolicyReference": "DEMO-registrationPolicyReference",
            "evidenceReference": "DEMO-evidenceReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "NumberVerification": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "phoneReference": "DEMO-phoneReference",
        "wabaReference": "DEMO-wabaReference",
        "verificationPolicyReference": "DEMO-verificationPolicyReference",
        "verificationEvidenceReference": "DEMO-verificationEvidenceReference",
    },
    "NumberVerificationPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "phoneReference": "DEMO-phoneReference",
            "wabaReference": "DEMO-wabaReference",
            "verificationPolicyReference": "DEMO-verificationPolicyReference",
            "verificationEvidenceReference": "DEMO-verificationEvidenceReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "NumbersResult": {
        "numbers": [
            {
                "phoneReference": "DEMO-phoneReference",
                "wabaReference": "DEMO-wabaReference",
                "verificationEvidenceReference": "DEMO-verificationEvidenceReference",
                "status": "unverified",
            }
        ],
        "execution": "planned_not_executed",
    },
    "ClientQuery": {},
    "ClientsResult": {
        "clients": [
            {
                "id": "DEMO-001",
                "name": "Synthetic demo",
                "phone": "Synthetic demo",
                "city": "Synthetic demo",
                "program": "Synthetic demo",
                "schedule": "Synthetic demo",
                "stage": "Synthetic demo",
                "tags": "Synthetic demo",
                "notes": "Synthetic demo",
                "type": "Synthetic demo",
                "interests": "Synthetic demo",
                "customValues": {},
            }
        ],
        "execution": "planned_not_executed",
    },
    "ClientDraft": {},
    "ClientDraftPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {},
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "CommentQuery": {},
    "CommentsResult": {
        "comments": [
            {
                "id": "DEMO-001",
                "platform": "Facebook",
                "author": "Synthetic demo",
                "post": "Synthetic demo",
                "body": "Synthetic demo",
                "status": "Pendiente",
                "replies": [{"id": "DEMO-001", "body": "Synthetic demo"}],
            }
        ],
        "execution": "planned_not_executed",
    },
    "ConversationQuery": {},
    "ConversationsResult": {
        "conversations": [
            {
                "clientId": "DEMO-001",
                "unread": True,
                "mode": "human",
                "channel": "WhatsApp",
                "messages": [
                    {
                        "id": "DEMO-001",
                        "body": "Synthetic demo",
                        "direction": "incoming",
                    }
                ],
                "workflow": {
                    "state": "Abierta",
                    "priority": "Baja",
                    "assignee": "Synthetic demo",
                    "revision": 1,
                    "tasks": [
                        {
                            "id": "DEMO-001",
                            "title": "Synthetic demo",
                            "due": "",
                            "status": "Pendiente",
                        }
                    ],
                    "events": [
                        {
                            "id": "DEMO-001",
                            "at": "2026-10-14T00:00:00Z",
                            "description": "Synthetic demo",
                        }
                    ],
                },
            }
        ],
        "execution": "planned_not_executed",
    },
    "CorporatesResult": {
        "organizations": [
            {
                "organizationReference": "DEMO-organizationReference",
                "displayName": "Synthetic demo",
                "contactReference": "DEMO-contactReference",
                "interactionReferences": ["DEMO-interactionReferences"],
                "scope": "conditional_pending",
            }
        ],
        "execution": "planned_not_executed",
    },
    "CreatorAuditResult": {
        "creatorAuditEvents": [
            {
                "eventReference": "DEMO-eventReference",
                "actorReference": "DEMO-actorReference",
                "intentReference": "DEMO-intentReference",
                "evidenceReference": "DEMO-evidenceReference",
            }
        ],
        "execution": "planned_not_executed",
    },
    "CampaignsResult": {
        "campaigns": [
            {
                "campaignReference": "DEMO-campaignReference",
                "name": "Synthetic demo",
                "objective": "Synthetic demo",
                "providerReference": "DEMO-providerReference",
                "budgetReference": "DEMO-budgetReference",
            }
        ],
        "execution": "planned_not_executed",
    },
    "CampaignDraft": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "name": "Synthetic demo",
        "objective": "Synthetic demo",
        "providerReference": "DEMO-providerReference",
        "budgetReference": "DEMO-budgetReference",
    },
    "CampaignDraftPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "name": "Synthetic demo",
            "objective": "Synthetic demo",
            "providerReference": "DEMO-providerReference",
            "budgetReference": "DEMO-budgetReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "ResourcesResult": {
        "resources": [
            {
                "resourceReference": "DEMO-resourceReference",
                "title": "Synthetic demo",
                "creatorReference": "DEMO-creatorReference",
                "campaignReference": "DEMO-campaignReference",
                "contentReference": "DEMO-contentReference",
                "rightsReviewReference": "DEMO-rightsReviewReference",
            }
        ],
        "execution": "planned_not_executed",
    },
    "ResourceDraft": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "title": "Synthetic demo",
        "creatorReference": "DEMO-creatorReference",
        "campaignReference": "DEMO-campaignReference",
        "contentReference": "DEMO-contentReference",
    },
    "ResourceDraftPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "title": "Synthetic demo",
            "creatorReference": "DEMO-creatorReference",
            "campaignReference": "DEMO-campaignReference",
            "contentReference": "DEMO-contentReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "CreatorQuery": {},
    "CreatorsResult": {
        "creators": [
            {
                "creatorReference": "DEMO-creatorReference",
                "displayName": "Synthetic demo",
                "platform": "instagram",
                "profileReference": "DEMO-profileReference",
                "contactReference": "DEMO-contactReference",
            }
        ],
        "execution": "planned_not_executed",
    },
    "CreatorDraft": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "displayName": "Synthetic demo",
        "platform": "instagram",
    },
    "CreatorDraftPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "displayName": "Synthetic demo",
            "platform": "instagram",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "CrmResult": {
        "stages": [{"key": "demo_key", "label": "Synthetic demo", "probability": 1.0}],
        "tags": ["Synthetic demo"],
        "fields": [
            {
                "key": "Synthetic demo",
                "label": "Synthetic demo",
                "type": "Text",
                "options": ["Synthetic demo"],
                "active": True,
            }
        ],
        "execution": "planned_not_executed",
    },
    "CrmDraft": {},
    "CrmDraftPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {},
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "OperationRecord": {
        "id": "ops-demo-stable",
        "name": "Synthetic demo",
        "description": "Synthetic demo",
        "status": "stable",
        "incident": "none",
        "revision": 1,
        "checks": [
            {"id": "isolation", "label": "Synthetic checklist", "checked": False},
            {"id": "human", "label": "Synthetic checklist", "checked": False},
            {"id": "reconciliation", "label": "Synthetic checklist", "checked": False},
        ],
        "history": [
            {
                "at": "2026-10-14T00:00:00Z",
                "label": "Synthetic demo",
                "reason": "Synthetic demo",
            }
        ],
    },
    "DiagnosticsResult": {
        "availability": "unconfigured",
        "scenarios": [
            {
                "id": "ops-demo-stable",
                "name": "Synthetic demo",
                "description": "Synthetic demo",
                "status": "stable",
                "incident": "none",
                "revision": 1,
                "checks": [
                    {
                        "id": "isolation",
                        "label": "Synthetic checklist",
                        "checked": False,
                    },
                    {"id": "human", "label": "Synthetic checklist", "checked": False},
                    {
                        "id": "reconciliation",
                        "label": "Synthetic checklist",
                        "checked": False,
                    },
                ],
                "history": [
                    {
                        "at": "2026-10-14T00:00:00Z",
                        "label": "Synthetic demo",
                        "reason": "Synthetic demo",
                    }
                ],
            }
        ],
        "execution": "planned_not_executed",
    },
    "DiagnosticEndpointsResult": {
        "endpoints": [
            {
                "operationReference": "DEMO-operationReference",
                "evidenceReference": "DEMO-evidenceReference",
                "availability": "unconfigured",
            }
        ],
        "execution": "planned_not_executed",
    },
    "DiagnosticEventsResult": {
        "events": [
            {
                "eventReference": "DEMO-eventReference",
                "description": "Synthetic demo",
                "evidenceReference": "DEMO-evidenceReference",
            }
        ],
        "execution": "planned_not_executed",
    },
    "DiagnosticIncidentsResult": {
        "incidents": [
            {
                "id": "ops-demo-stable",
                "name": "Synthetic demo",
                "description": "Synthetic demo",
                "status": "stable",
                "incident": "none",
                "revision": 1,
                "checks": [
                    {
                        "id": "isolation",
                        "label": "Synthetic checklist",
                        "checked": False,
                    },
                    {"id": "human", "label": "Synthetic checklist", "checked": False},
                    {
                        "id": "reconciliation",
                        "label": "Synthetic checklist",
                        "checked": False,
                    },
                ],
                "history": [
                    {
                        "at": "2026-10-14T00:00:00Z",
                        "label": "Synthetic demo",
                        "reason": "Synthetic demo",
                    }
                ],
            }
        ],
        "execution": "planned_not_executed",
    },
    "OperationPause": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "scenario": "stable",
        "reason": "Synthetic demo",
    },
    "OperationPausePlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "scenario": "stable",
            "reason": "Synthetic demo",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "ProcessIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "scope": "synthetic_events",
        "eventReferences": ["DEMO-eventReferences"],
        "reconciliationPolicyReference": "DEMO-reconciliationPolicyReference",
    },
    "ProcessIntentPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "scope": "synthetic_events",
            "eventReferences": ["DEMO-eventReferences"],
            "reconciliationPolicyReference": "DEMO-reconciliationPolicyReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "DiagnosticQueuesResult": {
        "queues": [
            {
                "queueReference": "DEMO-queueReference",
                "reconciliationReference": "DEMO-reconciliationReference",
                "availability": "unconfigured",
                "pendingCount": 1,
            }
        ],
        "execution": "planned_not_executed",
    },
    "RecoveryReview": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "scenario": "stable",
        "reason": "Synthetic demo",
        "checks": {"isolation": True, "human": True, "reconciliation": True},
        "evidenceReference": "DEMO-evidenceReference",
    },
    "RecoveryReviewPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "scenario": "stable",
            "reason": "Synthetic demo",
            "checks": {"isolation": True, "human": True, "reconciliation": True},
            "evidenceReference": "DEMO-evidenceReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "OperationResume": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "scenario": "stable",
        "reason": "Synthetic demo",
        "checks": {"isolation": True, "human": True, "reconciliation": True},
        "evidenceReference": "DEMO-evidenceReference",
        "recoveryReviewReference": "DEMO-recoveryReviewReference",
    },
    "OperationResumePlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "scenario": "stable",
            "reason": "Synthetic demo",
            "checks": {"isolation": True, "human": True, "reconciliation": True},
            "evidenceReference": "DEMO-evidenceReference",
            "recoveryReviewReference": "DEMO-recoveryReviewReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "SimulationIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "scenario": "stable",
        "fixtureReference": "DEMO-fixtureReference",
    },
    "SimulationIntentPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "scenario": "stable",
            "fixtureReference": "DEMO-fixtureReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "FollowupQuery": {},
    "FollowupsResult": {
        "followups": [
            {
                "followupReference": "DEMO-followupReference",
                "clientReference": "DEMO-clientReference",
                "conversationReference": "DEMO-conversationReference",
                "scheduleIntentReference": "DEMO-scheduleIntentReference",
                "status": "planned",
            }
        ],
        "execution": "planned_not_executed",
    },
    "FollowupIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "clientReference": "DEMO-clientReference",
        "conversationReference": "DEMO-conversationReference",
        "templateReference": "DEMO-templateReference",
        "consentPolicyReference": "DEMO-consentPolicyReference",
        "scheduleIntentReference": "DEMO-scheduleIntentReference",
    },
    "FollowupIntentPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "clientReference": "DEMO-clientReference",
            "conversationReference": "DEMO-conversationReference",
            "templateReference": "DEMO-templateReference",
            "consentPolicyReference": "DEMO-consentPolicyReference",
            "scheduleIntentReference": "DEMO-scheduleIntentReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "AliasesResult": {
        "aliases": [
            {"alias": "Synthetic demo", "sourceReference": "DEMO-sourceReference"}
        ],
        "execution": "planned_not_executed",
    },
    "AliasIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "aliases": [
            {"alias": "Synthetic demo", "sourceReference": "DEMO-sourceReference"}
        ],
    },
    "AliasIntentPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "aliases": [
                {"alias": "Synthetic demo", "sourceReference": "DEMO-sourceReference"}
            ],
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "EvaluationIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "question": "Synthetic demo",
        "expectedSourceReferences": ["DEMO-expectedSourceReferences"],
        "criteriaReferences": ["DEMO-criteriaReferences"],
    },
    "EvaluationResult": {
        "evaluationReference": "DEMO-evaluationReference",
        "criteriaReferences": ["DEMO-criteriaReferences"],
        "evidenceReferences": ["DEMO-evidenceReferences"],
        "outcome": "not_evaluated",
        "execution": "planned_not_executed",
    },
    "IndexIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "sourceReferences": ["DEMO-sourceReferences"],
        "sourceRevision": 1,
        "indexingPolicyReference": "DEMO-indexingPolicyReference",
    },
    "IndexIntentPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "sourceReferences": ["DEMO-sourceReferences"],
            "sourceRevision": 1,
            "indexingPolicyReference": "DEMO-indexingPolicyReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "KnowledgePublication": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "indexReference": "DEMO-indexReference",
        "evaluationReference": "DEMO-evaluationReference",
        "reviewReference": "DEMO-reviewReference",
    },
    "KnowledgePublicationPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "indexReference": "DEMO-indexReference",
            "evaluationReference": "DEMO-evaluationReference",
            "reviewReference": "DEMO-reviewReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "RetrievalIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "question": "Synthetic demo",
        "contextReference": "DEMO-contextReference",
        "sourceReferences": ["DEMO-sourceReferences"],
    },
    "RetrievalResult": {
        "snippets": [
            {
                "proposedText": "Synthetic demo",
                "citations": [
                    {
                        "sourceReference": "DEMO-sourceReference",
                        "excerptReference": "DEMO-excerptReference",
                    }
                ],
            }
        ],
        "evaluationReference": "DEMO-evaluationReference",
        "execution": "planned_not_executed",
    },
    "SourceQuery": {},
    "SourcesResult": {
        "sources": [
            {
                "sourceReference": "DEMO-sourceReference",
                "title": "Synthetic demo",
                "sourceType": "approved_document",
                "contentReference": "DEMO-contentReference",
                "tags": ["Synthetic demo"],
                "notes": "Synthetic demo",
                "revision": 1,
            }
        ],
        "execution": "planned_not_executed",
    },
    "SourceMetadata": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "title": "Synthetic demo",
        "sourceType": "approved_document",
        "contentReference": "DEMO-contentReference",
        "tags": ["Synthetic demo"],
        "notes": "Synthetic demo",
    },
    "SourceMetadataPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "title": "Synthetic demo",
            "sourceType": "approved_document",
            "contentReference": "DEMO-contentReference",
            "tags": ["Synthetic demo"],
            "notes": "Synthetic demo",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "MediaMetadata": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "assetReference": "DEMO-assetReference",
        "contentType": "audio/ogg",
        "byteLength": 1,
        "privacyPolicyReference": "DEMO-privacyPolicyReference",
    },
    "MediaMetadataPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "assetReference": "DEMO-assetReference",
            "contentType": "audio/ogg",
            "byteLength": 1,
            "privacyPolicyReference": "DEMO-privacyPolicyReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "OverviewResult": {
        "availability": "unconfigured",
        "clientCount": 1,
        "conversationCount": 1,
        "humanPendingReferences": ["DEMO-humanPendingReferences"],
        "execution": "planned_not_executed",
    },
    "ProfileResult": {
        "profileName": "Synthetic demo",
        "position": "Synthetic demo",
        "timezone": "America/Bogota",
        "emailReference": "DEMO-emailReference",
        "photoReference": "DEMO-photoReference",
        "identityReference": "DEMO-identityReference",
        "verificationReference": "DEMO-verificationReference",
        "execution": "planned_not_executed",
    },
    "ProfileDraft": {},
    "ProfileDraftPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {},
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "EmailChange": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "contactReference": "DEMO-contactReference",
        "identityReference": "DEMO-identityReference",
        "emailPolicyReference": "DEMO-emailPolicyReference",
    },
    "EmailChangePlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "contactReference": "DEMO-contactReference",
            "identityReference": "DEMO-identityReference",
            "emailPolicyReference": "DEMO-emailPolicyReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "EmailVerification": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "verificationIntentReference": "DEMO-verificationIntentReference",
        "evidenceReference": "DEMO-evidenceReference",
    },
    "EmailVerificationPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "verificationIntentReference": "DEMO-verificationIntentReference",
            "evidenceReference": "DEMO-evidenceReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "ProviderQuery": {},
    "ProvidersResult": {
        "providers": [
            {
                "providerReference": "DEMO-providerReference",
                "displayName": "Synthetic demo",
                "capability": "text",
                "credentialPolicyReference": "DEMO-credentialPolicyReference",
                "connectedStatus": "approval_pending",
            }
        ],
        "execution": "planned_not_executed",
    },
    "RetentionListResult": {
        "contacts": [
            {
                "contactReference": "DEMO-contactReference",
                "relationshipReference": "DEMO-relationshipReference",
                "displayName": "Synthetic demo",
                "nextReviewReference": "DEMO-nextReviewReference",
                "scope": "conditional_pending",
            }
        ],
        "execution": "planned_not_executed",
    },
    "RolesResult": {
        "roles": [
            {
                "roleReference": "DEMO-roleReference",
                "displayName": "Synthetic demo",
                "authorizationPolicyReference": "DEMO-authorizationPolicyReference",
            }
        ],
        "execution": "planned_not_executed",
    },
    "SalesMemoriesResult": {
        "memories": [
            {
                "caseReference": "DEMO-caseReference",
                "contextReference": "DEMO-contextReference",
                "sourceReferences": ["DEMO-sourceReferences"],
                "retentionPolicyReference": "DEMO-retentionPolicyReference",
            }
        ],
        "execution": "planned_not_executed",
    },
    "SecurityResult": {
        "posture": "not_configured",
        "identityPolicyReference": "DEMO-identityPolicyReference",
        "factorPolicyReference": "DEMO-factorPolicyReference",
        "auditPolicyReference": "DEMO-auditPolicyReference",
        "execution": "planned_not_executed",
    },
    "AuditResult": {
        "auditEvents": [
            {
                "eventReference": "DEMO-eventReference",
                "actorReference": "DEMO-actorReference",
                "intentReference": "DEMO-intentReference",
                "evidenceReference": "DEMO-evidenceReference",
            }
        ],
        "execution": "planned_not_executed",
    },
    "DeletionIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "targetReferences": ["DEMO-targetReferences"],
        "purpose": "subject_review",
        "reviewReference": "DEMO-reviewReference",
        "reauthenticationReference": "DEMO-reauthenticationReference",
        "reason": "Synthetic demo",
        "retentionPolicyReference": "DEMO-retentionPolicyReference",
    },
    "DeletionIntentPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "targetReferences": ["DEMO-targetReferences"],
            "purpose": "subject_review",
            "reviewReference": "DEMO-reviewReference",
            "reauthenticationReference": "DEMO-reauthenticationReference",
            "reason": "Synthetic demo",
            "retentionPolicyReference": "DEMO-retentionPolicyReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "ExportIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "targetReferences": ["DEMO-targetReferences"],
        "purpose": "subject_review",
        "reviewReference": "DEMO-reviewReference",
        "reauthenticationReference": "DEMO-reauthenticationReference",
    },
    "ExportIntentPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "targetReferences": ["DEMO-targetReferences"],
            "purpose": "subject_review",
            "reviewReference": "DEMO-reviewReference",
            "reauthenticationReference": "DEMO-reauthenticationReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "PasswordChange": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "credentialPolicyReference": "DEMO-credentialPolicyReference",
        "changeIntentReference": "DEMO-changeIntentReference",
        "reauthenticationReference": "DEMO-reauthenticationReference",
    },
    "PasswordChangePlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "credentialPolicyReference": "DEMO-credentialPolicyReference",
            "changeIntentReference": "DEMO-changeIntentReference",
            "reauthenticationReference": "DEMO-reauthenticationReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "FactorActivation": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "enrollmentIntentReference": "DEMO-enrollmentIntentReference",
        "verificationReviewReference": "DEMO-verificationReviewReference",
        "activationPolicyReference": "DEMO-activationPolicyReference",
    },
    "FactorActivationPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "enrollmentIntentReference": "DEMO-enrollmentIntentReference",
            "verificationReviewReference": "DEMO-verificationReviewReference",
            "activationPolicyReference": "DEMO-activationPolicyReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "FactorEnrollment": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "enrollmentIntentReference": "DEMO-enrollmentIntentReference",
        "factorPolicyReference": "DEMO-factorPolicyReference",
        "identityReference": "DEMO-identityReference",
    },
    "FactorEnrollmentPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "enrollmentIntentReference": "DEMO-enrollmentIntentReference",
            "factorPolicyReference": "DEMO-factorPolicyReference",
            "identityReference": "DEMO-identityReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "FactorRecovery": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "identityReference": "DEMO-identityReference",
        "recoveryPolicyReference": "DEMO-recoveryPolicyReference",
        "recoveryEvidenceReference": "DEMO-recoveryEvidenceReference",
    },
    "FactorRecoveryPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "identityReference": "DEMO-identityReference",
            "recoveryPolicyReference": "DEMO-recoveryPolicyReference",
            "recoveryEvidenceReference": "DEMO-recoveryEvidenceReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "FactorVerification": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "enrollmentIntentReference": "DEMO-enrollmentIntentReference",
        "verificationEvidenceReference": "DEMO-verificationEvidenceReference",
    },
    "FactorVerificationPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "enrollmentIntentReference": "DEMO-enrollmentIntentReference",
            "verificationEvidenceReference": "DEMO-verificationEvidenceReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "SynthesisIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "text": "Synthetic demo",
        "voiceReference": "DEMO-voiceReference",
        "modelReference": "DEMO-modelReference",
        "processingPolicyReference": "DEMO-processingPolicyReference",
    },
    "SynthesisResult": {
        "proposedMediaReference": "DEMO-proposedMediaReference",
        "voiceReference": "DEMO-voiceReference",
        "evaluationReference": "DEMO-evaluationReference",
        "execution": "planned_not_executed",
    },
    "TranscriptionIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "mediaReference": "DEMO-mediaReference",
        "modelReference": "DEMO-modelReference",
        "processingPolicyReference": "DEMO-processingPolicyReference",
    },
    "TranscriptionResult": {
        "mediaReference": "DEMO-mediaReference",
        "proposedTranscript": "Synthetic demo",
        "evaluationReference": "DEMO-evaluationReference",
        "execution": "planned_not_executed",
    },
    "UsersResult": {
        "users": [
            {
                "userReference": "DEMO-userReference",
                "identityReference": "DEMO-identityReference",
                "displayName": "Synthetic demo",
                "roleReferences": ["DEMO-roleReferences"],
                "identityPolicyReference": "DEMO-identityPolicyReference",
            }
        ],
        "execution": "planned_not_executed",
    },
    "UserInvitation": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "identityReference": "DEMO-identityReference",
        "displayName": "Synthetic demo",
        "invitationPolicyReference": "DEMO-invitationPolicyReference",
        "roleReferences": ["DEMO-roleReferences"],
    },
    "UserInvitationPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "identityReference": "DEMO-identityReference",
            "displayName": "Synthetic demo",
            "invitationPolicyReference": "DEMO-invitationPolicyReference",
            "roleReferences": ["DEMO-roleReferences"],
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "ApplicationLinkPath": {"link_reference": "DEMO-001"},
    "ApplicationLinkResult": {
        "linkReference": "DEMO-linkReference",
        "status": "valid",
        "schemaReference": "DEMO-schemaReference",
        "execution": "planned_not_executed",
    },
    "ApplicationDraft": {},
    "ApplicationDraftPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {},
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "ApplicationPath": {"application_id": "DEMO-001"},
    "ApplicationResult": {
        "application": {
            "id": "DEMO-001",
            "name": "Synthetic demo",
            "email": "demo@example.invalid",
            "program": "Synthetic demo",
            "schedule": "Synthetic demo",
            "syntheticConfirmed": True,
            "status": "pending",
            "history": [
                {
                    "status": "pending",
                    "reason": "Synthetic demo",
                    "at": "2026-10-14T00:00:00Z",
                    "actor": "Synthetic demo",
                }
            ],
        },
        "execution": "planned_not_executed",
    },
    "CoreRegistrationIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "applicationRevision": 1,
        "contractReference": "DEMO-contractReference",
        "authorizationEvidenceReference": "DEMO-authorizationEvidenceReference",
        "reviewReference": "DEMO-reviewReference",
        "confirmed": True,
    },
    "CoreRegistrationIntentPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "applicationRevision": 1,
            "contractReference": "DEMO-contractReference",
            "authorizationEvidenceReference": "DEMO-authorizationEvidenceReference",
            "reviewReference": "DEMO-reviewReference",
            "confirmed": True,
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "ReviewReopen": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "reviewerReference": "DEMO-reviewerReference",
        "reason": "Synthetic demo",
    },
    "ReviewReopenPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "reviewerReference": "DEMO-reviewerReference",
            "reason": "Synthetic demo",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "ReviewDraft": {},
    "ReviewDraftPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {},
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "ReviewStart": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "reviewerReference": "DEMO-reviewerReference",
    },
    "ReviewStartPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "reviewerReference": "DEMO-reviewerReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "SessionRevocationQuery": {
        "revocationIntentReference": "DEMO-revocationIntentReference",
        "expectedRevision": 1,
    },
    "SessionPath": {"session_id": "DEMO-001"},
    "SessionRevocationPlan": {
        "sessionReference": "DEMO-sessionReference",
        "revocationIntentReference": "DEMO-revocationIntentReference",
        "expectedRevision": 1,
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "ProgramPath": {"program_id": "DEMO-001"},
    "ProgramResult": {
        "program": {
            "reference": "DEMO-reference",
            "displayName": "Synthetic demo",
            "sourceAvailability": "unconfigured",
        },
        "execution": "planned_not_executed",
    },
    "ChannelPath": {"channel": "whatsapp"},
    "ChannelResult": {
        "channel": {
            "channel": "facebook",
            "connectedStatus": "approval_pending",
            "appReference": "DEMO-appReference",
            "assetReference": "DEMO-assetReference",
            "portfolioReference": "DEMO-portfolioReference",
            "pageReference": "DEMO-pageReference",
            "wabaReference": "DEMO-wabaReference",
            "phoneReference": "DEMO-phoneReference",
            "accountReference": "DEMO-accountReference",
            "usernameReference": "DEMO-usernameReference",
            "clientKeyReference": "DEMO-clientKeyReference",
            "openIdReference": "DEMO-openIdReference",
            "tokenReference": "DEMO-tokenReference",
            "secretReference": "DEMO-secretReference",
            "verifyReference": "DEMO-verifyReference",
            "callbackReference": "DEMO-callbackReference",
            "webhookReference": "DEMO-webhookReference",
            "versionReference": "DEMO-versionReference",
            "requestedScopesReference": "DEMO-requestedScopesReference",
            "grantedScopesReference": "DEMO-grantedScopesReference",
            "accessEvidenceReference": "DEMO-accessEvidenceReference",
        },
        "execution": "planned_not_executed",
    },
    "ActivationIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "testedRevision": 1,
        "evidenceReference": "DEMO-evidenceReference",
        "activationPolicyReference": "DEMO-activationPolicyReference",
    },
    "ActivationIntentPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "testedRevision": 1,
            "evidenceReference": "DEMO-evidenceReference",
            "activationPolicyReference": "DEMO-activationPolicyReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "ChannelCapabilitiesResult": {
        "capabilities": [
            {
                "capabilityReference": "DEMO-capabilityReference",
                "evidenceReference": "DEMO-evidenceReference",
                "status": "unverified",
            }
        ],
        "execution": "planned_not_executed",
    },
    "ChannelTest": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "draftRevision": 1,
        "testReference": "DEMO-testReference",
        "connectionPolicyReference": "DEMO-connectionPolicyReference",
    },
    "ChannelTestPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "draftRevision": 1,
            "testReference": "DEMO-testReference",
            "connectionPolicyReference": "DEMO-connectionPolicyReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "ChannelDiscovery": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "draftRevision": 1,
        "testReference": "DEMO-testReference",
        "capabilityPolicyReference": "DEMO-capabilityPolicyReference",
    },
    "ChannelDiscoveryPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "draftRevision": 1,
            "testReference": "DEMO-testReference",
            "capabilityPolicyReference": "DEMO-capabilityPolicyReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "ChannelDraft": {},
    "ChannelDraftPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {},
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "OAuthIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "callbackPolicyReference": "DEMO-callbackPolicyReference",
        "identityPolicyReference": "DEMO-identityPolicyReference",
    },
    "OAuthIntentPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "callbackPolicyReference": "DEMO-callbackPolicyReference",
            "identityPolicyReference": "DEMO-identityPolicyReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "CallbackQuery": {
        "authorizationEventReference": "DEMO-authorizationEventReference"
    },
    "CallbackResult": {
        "authorizationEventReference": "DEMO-authorizationEventReference",
        "reviewReference": "DEMO-reviewReference",
        "execution": "planned_not_executed",
    },
    "PauseIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "reason": "Synthetic demo",
        "policyReference": "DEMO-policyReference",
    },
    "PauseIntentPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "reason": "Synthetic demo",
            "policyReference": "DEMO-policyReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "WebhookReferenceResult": {
        "webhookReference": "DEMO-webhookReference",
        "callbackPolicyReference": "DEMO-callbackPolicyReference",
        "verificationPolicyReference": "DEMO-verificationPolicyReference",
        "execution": "planned_not_executed",
    },
    "ClientPath": {"client_id": "DEMO-001"},
    "ClientResult": {
        "client": {
            "id": "DEMO-001",
            "name": "Synthetic demo",
            "phone": "Synthetic demo",
            "city": "Synthetic demo",
            "program": "Synthetic demo",
            "schedule": "Synthetic demo",
            "stage": "Synthetic demo",
            "tags": "Synthetic demo",
            "notes": "Synthetic demo",
            "type": "Synthetic demo",
            "interests": "Synthetic demo",
            "customValues": {},
        },
        "execution": "planned_not_executed",
    },
    "DeactivationIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "reason": "Synthetic demo",
        "reviewReference": "DEMO-reviewReference",
        "policyReference": "DEMO-policyReference",
    },
    "DeactivationIntentPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "reason": "Synthetic demo",
            "reviewReference": "DEMO-reviewReference",
            "policyReference": "DEMO-policyReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "ClientTimelineResult": {
        "clientReference": "DEMO-clientReference",
        "timeline": [
            {
                "eventReference": "DEMO-eventReference",
                "description": "Synthetic demo",
                "evidenceReference": "DEMO-evidenceReference",
            }
        ],
        "execution": "planned_not_executed",
    },
    "CommentPath": {"comment_id": "DEMO-001"},
    "CommentResult": {
        "comment": {
            "id": "DEMO-001",
            "platform": "Facebook",
            "author": "Synthetic demo",
            "post": "Synthetic demo",
            "body": "Synthetic demo",
            "status": "Pendiente",
            "replies": [{"id": "DEMO-001", "body": "Synthetic demo"}],
        },
        "execution": "planned_not_executed",
    },
    "ReactionIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "policyReference": "DEMO-policyReference",
        "reactionReference": "DEMO-reactionReference",
        "intent": "add",
    },
    "ReactionIntentPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "policyReference": "DEMO-policyReference",
            "reactionReference": "DEMO-reactionReference",
            "intent": "add",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "MessageDraft": {},
    "MessageDraftPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {},
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "ConversationPath": {"conversation_id": "DEMO-001"},
    "ConversationResult": {
        "conversation": {
            "clientId": "DEMO-001",
            "unread": True,
            "mode": "human",
            "channel": "WhatsApp",
            "messages": [
                {"id": "DEMO-001", "body": "Synthetic demo", "direction": "incoming"}
            ],
            "workflow": {
                "state": "Abierta",
                "priority": "Baja",
                "assignee": "Synthetic demo",
                "revision": 1,
                "tasks": [
                    {
                        "id": "DEMO-001",
                        "title": "Synthetic demo",
                        "due": "",
                        "status": "Pendiente",
                    }
                ],
                "events": [
                    {
                        "id": "DEMO-001",
                        "at": "2026-10-14T00:00:00Z",
                        "description": "Synthetic demo",
                    }
                ],
            },
        },
        "execution": "planned_not_executed",
    },
    "AnalysisIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "contextReference": "DEMO-contextReference",
        "configurationReference": "DEMO-configurationReference",
        "evidenceReferences": ["DEMO-evidenceReferences"],
        "analysisPolicyReference": "DEMO-analysisPolicyReference",
    },
    "AnalysisResult": {
        "contextReference": "DEMO-contextReference",
        "signalReferences": ["DEMO-signalReferences"],
        "derivation": "deterministic_local_proposal",
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "ConversationControl": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "target": "human",
        "reason": "Synthetic demo",
        "humanPolicyReference": "DEMO-humanPolicyReference",
    },
    "ConversationControlPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "target": "human",
            "reason": "Synthetic demo",
            "humanPolicyReference": "DEMO-humanPolicyReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "DeliveriesResult": {
        "deliveries": [
            {
                "messageReference": "DEMO-messageReference",
                "status": "pending",
                "evidenceReference": "DEMO-evidenceReference",
            }
        ],
        "execution": "planned_not_executed",
    },
    "EventsResult": {
        "events": [
            {
                "id": "DEMO-001",
                "at": "2026-10-14T00:00:00Z",
                "description": "Synthetic demo",
            }
        ],
        "execution": "planned_not_executed",
    },
    "MessagesResult": {
        "messages": [
            {"id": "DEMO-001", "body": "Synthetic demo", "direction": "incoming"}
        ],
        "execution": "planned_not_executed",
    },
    "ReadIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "lastMessageReference": "DEMO-lastMessageReference",
    },
    "ReadIntentPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "lastMessageReference": "DEMO-lastMessageReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "SuggestionIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "contextReference": "DEMO-contextReference",
        "configurationReference": "DEMO-configurationReference",
        "evidenceReferences": ["DEMO-evidenceReferences"],
        "templateReference": "DEMO-templateReference",
    },
    "SuggestionResult": {
        "templateReference": "DEMO-templateReference",
        "proposedText": "Synthetic demo",
        "evidenceReferences": ["DEMO-evidenceReferences"],
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "TasksResult": {
        "tasks": [
            {
                "id": "DEMO-001",
                "title": "Synthetic demo",
                "due": "",
                "status": "Pendiente",
            }
        ],
        "execution": "planned_not_executed",
    },
    "TaskDraft": {},
    "TaskDraftPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {},
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "WorkflowDraft": {},
    "WorkflowDraftPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {},
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "ReferencePath": {"reference_id": "DEMO-001"},
    "CorporateResult": {
        "organization": {
            "organizationReference": "DEMO-organizationReference",
            "displayName": "Synthetic demo",
            "contactReference": "DEMO-contactReference",
            "interactionReferences": ["DEMO-interactionReferences"],
            "scope": "conditional_pending",
        },
        "execution": "planned_not_executed",
    },
    "DeliverableDraft": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "creatorReference": "DEMO-creatorReference",
        "title": "Synthetic demo",
        "dueReference": "DEMO-dueReference",
        "requirements": ["Synthetic demo"],
    },
    "CampaignPath": {"campaign_id": "DEMO-001"},
    "DeliverableDraftPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "creatorReference": "DEMO-creatorReference",
            "title": "Synthetic demo",
            "dueReference": "DEMO-dueReference",
            "requirements": ["Synthetic demo"],
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "DeliverableUpdate": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "deliverable": {"title": "Synthetic demo"},
    },
    "DeliverablePath": {"deliverable_id": "DEMO-001"},
    "DeliverableUpdatePlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "deliverable": {"title": "Synthetic demo"},
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "PerformanceAnalysis": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "analysisPolicyReference": "DEMO-analysisPolicyReference",
        "evidenceReferences": ["DEMO-evidenceReferences"],
    },
    "ResourcePath": {"resource_id": "DEMO-001"},
    "PerformanceAnalysisPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "analysisPolicyReference": "DEMO-analysisPolicyReference",
            "evidenceReferences": ["DEMO-evidenceReferences"],
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "RightsReview": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "contractReference": "DEMO-contractReference",
        "reviewerReference": "DEMO-reviewerReference",
        "scopeEvidenceReference": "DEMO-scopeEvidenceReference",
        "periodEvidenceReference": "DEMO-periodEvidenceReference",
    },
    "RightsReviewPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "contractReference": "DEMO-contractReference",
            "reviewerReference": "DEMO-reviewerReference",
            "scopeEvidenceReference": "DEMO-scopeEvidenceReference",
            "periodEvidenceReference": "DEMO-periodEvidenceReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "RightsRevocation": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "contractReference": "DEMO-contractReference",
        "reviewerReference": "DEMO-reviewerReference",
        "scopeEvidenceReference": "DEMO-scopeEvidenceReference",
        "periodEvidenceReference": "DEMO-periodEvidenceReference",
        "reason": "Synthetic demo",
    },
    "RightsRevocationPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "contractReference": "DEMO-contractReference",
            "reviewerReference": "DEMO-reviewerReference",
            "scopeEvidenceReference": "DEMO-scopeEvidenceReference",
            "periodEvidenceReference": "DEMO-periodEvidenceReference",
            "reason": "Synthetic demo",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "SparkPreflight": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "rightsReviewReference": "DEMO-rightsReviewReference",
        "capabilityEvaluationReference": "DEMO-capabilityEvaluationReference",
        "authorizationPolicyReference": "DEMO-authorizationPolicyReference",
    },
    "SparkPreflightPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "rightsReviewReference": "DEMO-rightsReviewReference",
            "capabilityEvaluationReference": "DEMO-capabilityEvaluationReference",
            "authorizationPolicyReference": "DEMO-authorizationPolicyReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "ContactPlan": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "templateReference": "DEMO-templateReference",
        "messageReference": "DEMO-messageReference",
        "followupReference": "DEMO-followupReference",
    },
    "CreatorPath": {"creator_id": "DEMO-001"},
    "ContactPlanPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "templateReference": "DEMO-templateReference",
            "messageReference": "DEMO-messageReference",
            "followupReference": "DEMO-followupReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "FollowupCancellation": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "reason": "Synthetic demo",
        "cancellationPolicyReference": "DEMO-cancellationPolicyReference",
    },
    "FollowupPath": {"follow_up_id": "DEMO-001"},
    "FollowupCancellationPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "reason": "Synthetic demo",
            "cancellationPolicyReference": "DEMO-cancellationPolicyReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "SourceUpdate": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "metadata": {"title": "Synthetic demo"},
    },
    "SourcePath": {"source_id": "DEMO-001"},
    "SourceUpdatePlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "metadata": {"title": "Synthetic demo"},
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "SourceRemoval": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "reason": "Synthetic demo",
        "reviewReference": "DEMO-reviewReference",
    },
    "SourceRemovalPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "reason": "Synthetic demo",
            "reviewReference": "DEMO-reviewReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "MediaPath": {"media_reference": "DEMO-001"},
    "MediaResult": {
        "mediaReference": "DEMO-mediaReference",
        "assetReference": "DEMO-assetReference",
        "contentType": "audio/ogg",
        "privacyPolicyReference": "DEMO-privacyPolicyReference",
        "execution": "planned_not_executed",
    },
    "ProviderPath": {"provider_reference": "DEMO-001"},
    "ProviderResult": {
        "provider": {
            "providerReference": "DEMO-providerReference",
            "displayName": "Synthetic demo",
            "capability": "text",
            "credentialPolicyReference": "DEMO-credentialPolicyReference",
            "connectedStatus": "approval_pending",
        },
        "execution": "planned_not_executed",
    },
    "ProviderAuthenticationTest": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "draftRevision": 1,
        "testReference": "DEMO-testReference",
        "credentialPolicyReference": "DEMO-credentialPolicyReference",
    },
    "ProviderAuthenticationTestPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "draftRevision": 1,
            "testReference": "DEMO-testReference",
            "credentialPolicyReference": "DEMO-credentialPolicyReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "ProviderDraft": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "displayName": "Synthetic demo",
        "capability": "text",
        "credentialPolicyReference": "DEMO-credentialPolicyReference",
        "versionReference": "DEMO-versionReference",
    },
    "ProviderDraftPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "displayName": "Synthetic demo",
            "capability": "text",
            "credentialPolicyReference": "DEMO-credentialPolicyReference",
            "versionReference": "DEMO-versionReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "ProviderModelIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "modelReference": "DEMO-modelReference",
        "capability": "text",
    },
    "ProviderModelIntentPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "modelReference": "DEMO-modelReference",
            "capability": "text",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "ModelsResult": {
        "models": [
            {
                "modelReference": "DEMO-modelReference",
                "displayName": "Synthetic demo",
                "capability": "text",
                "evaluationReference": "DEMO-evaluationReference",
            }
        ],
        "execution": "planned_not_executed",
    },
    "RevocationIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "revocationPolicyReference": "DEMO-revocationPolicyReference",
        "evidenceReference": "DEMO-evidenceReference",
        "reason": "Synthetic demo",
    },
    "RevocationIntentPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "revocationPolicyReference": "DEMO-revocationPolicyReference",
            "evidenceReference": "DEMO-evidenceReference",
            "reason": "Synthetic demo",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "RotationIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "rotationPolicyReference": "DEMO-rotationPolicyReference",
        "evidenceReference": "DEMO-evidenceReference",
        "reason": "Synthetic demo",
    },
    "RotationIntentPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "rotationPolicyReference": "DEMO-rotationPolicyReference",
            "evidenceReference": "DEMO-evidenceReference",
            "reason": "Synthetic demo",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "ProviderTest": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "draftRevision": 1,
        "modelRevision": 1,
        "testReference": "DEMO-testReference",
        "evaluationPolicyReference": "DEMO-evaluationPolicyReference",
    },
    "ProviderTestPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "draftRevision": 1,
            "modelRevision": 1,
            "testReference": "DEMO-testReference",
            "evaluationPolicyReference": "DEMO-evaluationPolicyReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "RetentionResult": {
        "contact": {
            "contactReference": "DEMO-contactReference",
            "relationshipReference": "DEMO-relationshipReference",
            "displayName": "Synthetic demo",
            "nextReviewReference": "DEMO-nextReviewReference",
            "scope": "conditional_pending",
        },
        "execution": "planned_not_executed",
    },
    "MemoryPath": {"case_id": "DEMO-001"},
    "SalesMemoryResult": {
        "memory": {
            "caseReference": "DEMO-caseReference",
            "contextReference": "DEMO-contextReference",
            "sourceReferences": ["DEMO-sourceReferences"],
            "retentionPolicyReference": "DEMO-retentionPolicyReference",
        },
        "execution": "planned_not_executed",
    },
    "UserPresentation": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "presentation": {"displayName": "Synthetic demo"},
    },
    "UserPath": {"user_id": "DEMO-001"},
    "UserPresentationPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "presentation": {"displayName": "Synthetic demo"},
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "UserStatusIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "reason": "Synthetic demo",
        "identityPolicyReference": "DEMO-identityPolicyReference",
        "authorizationReviewReference": "DEMO-authorizationReviewReference",
    },
    "UserStatusIntentPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "reason": "Synthetic demo",
            "identityPolicyReference": "DEMO-identityPolicyReference",
            "authorizationReviewReference": "DEMO-authorizationReviewReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "UserRoleIntent": {
        "idempotencyReference": "DEMO-idempotencyReference",
        "expectedRevision": 1,
        "roleReference": "DEMO-roleReference",
        "authorizationReviewReference": "DEMO-authorizationReviewReference",
    },
    "UserRoleIntentPlan": {
        "proposalReference": "DEMO-proposalReference",
        "intent": {
            "idempotencyReference": "DEMO-idempotencyReference",
            "expectedRevision": 1,
            "roleReference": "DEMO-roleReference",
            "authorizationReviewReference": "DEMO-authorizationReviewReference",
        },
        "humanReview": "required",
        "execution": "planned_not_executed",
    },
    "WebhookVerificationQuery": {"verificationReference": "DEMO-verificationReference"},
    "WebhookVerificationResult": {
        "verificationReference": "DEMO-verificationReference",
        "contractReference": "DEMO-contractReference",
        "execution": "planned_not_executed",
    },
    "SyntheticWebhook": {
        "eventReference": "DEMO-eventReference",
        "channel": "whatsapp",
        "payload": {
            "kind": "message",
            "messageReference": "DEMO-messageReference",
            "senderReference": "DEMO-senderReference",
            "text": "Synthetic demo",
            "direction": "incoming",
        },
    },
    "WebhookIngressResult": {
        "eventReference": "DEMO-eventReference",
        "ingressContractReference": "DEMO-ingressContractReference",
        "disposition": "not_acknowledged",
        "execution": "planned_not_executed",
    },
    "ConversationTaskPath": {"conversation_id": "DEMO-001", "task_id": "DEMO-001"},
}
