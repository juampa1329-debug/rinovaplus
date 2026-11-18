-- Apply once as the PostgreSQL operator. Never run from application startup.
-- Separate native schema preserves the frozen 155-table CRM mapping.
BEGIN;
SELECT pg_advisory_xact_lock(hashtextextended('rinova-notify-p15-v1',0));
CREATE SCHEMA IF NOT EXISTS rinova_notify;
REVOKE ALL ON SCHEMA rinova_notify FROM PUBLIC;
CREATE TABLE IF NOT EXISTS rinova_notify.version (
  version integer PRIMARY KEY CHECK(version=1), applied_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO rinova_notify.version(version) VALUES(1) ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS rinova_notify.document (
 institution uuid NOT NULL, kind text NOT NULL CHECK(kind IN('transport','template','rule','group','schedule','preference')),
 id text NOT NULL, revision integer NOT NULL, body jsonb NOT NULL, actor uuid NOT NULL,
 updated_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(institution,kind,id)
);
CREATE TABLE IF NOT EXISTS rinova_notify.history (
 institution uuid NOT NULL, kind text NOT NULL, id text NOT NULL, revision integer NOT NULL,
 body jsonb NOT NULL, actor uuid NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(institution,kind,id,revision)
);
CREATE TABLE IF NOT EXISTS rinova_notify.outbox (
 institution uuid NOT NULL, id uuid PRIMARY KEY, dedup text NOT NULL, event text NOT NULL,
 recipient text NOT NULL, user_id uuid, required_action text NOT NULL,
 nonce bytea NOT NULL, ciphertext bytea NOT NULL,
 state text NOT NULL CHECK(state IN('queued','sending','accepted','retry','failed','uncertain','suppressed','relayed','bounced','cancelled')),
 attempts integer NOT NULL DEFAULT 0, next_at timestamptz NOT NULL DEFAULT now(),
 expires_at timestamptz NOT NULL DEFAULT now()+interval '24 hours', lease_until timestamptz,
 error text, message_id text NOT NULL UNIQUE, created_at timestamptz NOT NULL DEFAULT now(),
 updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(institution,dedup,recipient)
);
CREATE INDEX IF NOT EXISTS p15_outbox_due ON rinova_notify.outbox(institution,next_at) WHERE state IN('queued','retry');
CREATE TABLE IF NOT EXISTS rinova_notify.receipt (
 institution uuid NOT NULL, id text NOT NULL, mail_id uuid NOT NULL REFERENCES rinova_notify.outbox(id),
 action text NOT NULL, observed_at timestamptz NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(institution,id)
);
CREATE TABLE IF NOT EXISTS rinova_notify.asset (
 institution uuid NOT NULL, id uuid PRIMARY KEY, name text NOT NULL, mime text NOT NULL,
 content bytea NOT NULL, sha256 text NOT NULL, actor uuid NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS rinova_notify.cursor (
 institution uuid NOT NULL, key text NOT NULL, value jsonb NOT NULL, PRIMARY KEY(institution,key)
);
GRANT USAGE ON SCHEMA rinova_notify TO rinovaplus_app;
GRANT SELECT ON rinova_notify.version TO rinovaplus_app;
GRANT SELECT,INSERT,UPDATE ON rinova_notify.document,rinova_notify.outbox,rinova_notify.cursor TO rinovaplus_app;
GRANT SELECT,INSERT ON rinova_notify.history,rinova_notify.receipt,rinova_notify.asset TO rinovaplus_app;
COMMIT;
