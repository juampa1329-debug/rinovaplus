"SQL-backed human identity; every protected transaction rechecks revocation."

import hmac
import json
from uuid import uuid4

from fastapi import HTTPException

from app.institutional.crypto import (
    matching_step,
    password_hash,
    password_matches,
    token,
    token_hash,
)
from app.institutional.db import (
    audit,
    bound_hash,
    csrf_token,
    institution,
    one,
    public_user,
    read_factor_secret,
    uid,
)
from app.institutional.store import transaction

COOKIE = "cbn_institution_session"


def cookie_name(settings):
    if getattr(settings, "ticket", {}).get("version") == "cbn-institutional-operations-p11-v1":
        return COOKIE + "_operations"
    if getattr(settings, 'ticket', {}).get('version') in {'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        return COOKIE + '_learning' 
    if getattr(settings, "ticket", {}).get("version") in {'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        return COOKIE + "_ads"

    if getattr(settings, "ticket", {}).get("version") in {
        "cbn-institutional-ads-p9-v1",
        "cbn-institutional-campaign-p8-v1",
    'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        return COOKIE + "_campaigns"
    if getattr(settings, "ticket", {}).get("version") in {
        "cbn-institutional-broadcast-p7-v1",
        "cbn-institutional-campaign-p8-v1",
        "cbn-institutional-ads-p9-v1",
    'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
        return COOKIE + "_broadcast"
    if (
        getattr(settings, "ticket", {}).get("version")
        == "cbn-institutional-knowledge-p6-v1"
    ):
        return COOKIE + "_knowledge"
    if (
        getattr(settings, "ticket", {}).get("version")
        == "cbn-institutional-agents-p5-v1"
    ):
        return COOKIE + "_agents"
    if (
        getattr(settings, "ticket", {}).get("version")
        == "cbn-institutional-channels-p4-v1"
    ):
        return COOKIE + "_channels"
    return (
        COOKIE + "_workspace"
        if getattr(settings, "ticket", {}).get("version")
        == "cbn-institutional-spanish-p3-v1"
        else COOKIE
    )


DUMMY = "pbkdf2-sha256$1000000$" + "00" * 16 + "$" + "00" * 32


def authorize(cursor, settings, authority, permission="self", *, recent=False):
    raw = authority.get("token", "")
    if not isinstance(raw, str) or not 40 <= len(raw) <= 100:
        raise HTTPException(401, "session_required")
    value = one(
        cursor,
        (
            "SELECT u.*,r.Actions,s.SessionId,s.CSR"
            "FHash,s.RecentAt,s.MFAAt,CASE WHEN s.R"
            "ecentAt>=DATEADD(minute,-5,SYSUTCDATET"
            "IME()) THEN 1 ELSE 0 END AS Recent,CAS"
            "E WHEN s.MFAAt>=DATEADD(minute,-5,SYSU"
            "TCDATETIME()) THEN 1 ELSE 0 END AS Rec"
            "entMFA,ISNULL(f.State,'disabled') AS M"
            "FAState FROM crm_access.Session s JOIN"
            " crm_access.AccessUser u ON u.Institut"
            "ionId=s.InstitutionId AND u.UserId=s.U"
            "serId JOIN crm_access.Role r ON r.Inst"
            "itutionId=u.InstitutionId AND r.RoleKe"
            "y=u.RoleKey LEFT JOIN crm_access.Facto"
            "r f ON f.InstitutionId=u.InstitutionId"
            " AND f.UserId=u.UserId WHERE s.Institu"
            "tionId=? AND s.TokenHash=? AND s.Revok"
            "edAt IS NULL AND s.ExpiresAt>SYSUTCDAT"
            "ETIME() AND u.Active=1 AND r.Active=1 "
            "AND s.AuthVersion=u.AuthVersion"
        ),
        institution(settings),
        bound_hash(settings, raw, "session"),
    )
    if not value:
        raise HTTPException(401, "session_required")
    if permission != "self" and permission not in json.loads(value["Actions"]):
        raise HTTPException(403, "permission_denied")
    module = authority.get("module")
    if module:
        document = cursor.execute(
            (
                "SELECT Document FROM crm_access.Settin"
                "g WHERE InstitutionId=? AND Section='m"
                "odules'"
            ),
            institution(settings),
        ).fetchval()
        if not json.loads(document)["enabled"].get(module, False):
            raise HTTPException(403, "module_disabled")
    if authority.get("method", "GET") not in {"GET", "HEAD", "OPTIONS"}:
        csrf = authority.get("csrf", "")
        if not isinstance(csrf, str) or not hmac.compare_digest(
            bytes(value["CSRFHash"]), token_hash(csrf)
        ):
            raise HTTPException(403, "csrf_required")
    if recent and (
        not value["Recent"] or value["MFAState"] == "enabled" and not value["RecentMFA"]
    ):
        raise HTTPException(428, "password_confirmation_required")
    value["UserId"] = uid(str(value["UserId"]))
    value["SessionId"] = uid(str(value["SessionId"]))
    return value


def user(cursor, settings, identity):
    return one(
        cursor,
        (
            "SELECT u.*,r.Actions FROM crm_access.A"
            "ccessUser u JOIN crm_access.Role r ON "
            "r.InstitutionId=u.InstitutionId AND r."
            "RoleKey=u.RoleKey WHERE u.InstitutionI"
            "d=? AND u.UserId=? AND u.Active=1 AND "
            "r.Active=1"
        ),
        institution(settings),
        identity,
    )


def rate(cursor, settings, reference, limit, window):
    cursor.execute(
        (
            "DELETE TOP(100) FROM crm_access.RateBu"
            "cket WHERE InstitutionId=? AND WindowA"
            "t<DATEADD(day,-1,SYSUTCDATETIME())"
        ),
        institution(settings),
    )
    bucket = bound_hash(settings, reference, "rate")
    current = one(
        cursor,
        (
            "SELECT Attempts,CASE WHEN DATEDIFF(sec"
            "ond,WindowAt,SYSUTCDATETIME())>=? THEN"
            " 1 ELSE 0 END AS Expired FROM crm_acce"
            "ss.RateBucket WITH(UPDLOCK,HOLDLOCK) W"
            "HERE InstitutionId=? AND BucketHash=?"
        ),
        window,
        institution(settings),
        bucket,
    )
    if not current:
        cursor.execute(
            (
                "INSERT crm_access.RateBucket(Instituti"
                "onId,BucketHash,WindowAt,Attempts) VAL"
                "UES(?,?,SYSUTCDATETIME(),1)"
            ),
            institution(settings),
            bucket,
        )
        return True
    if current["Expired"]:
        cursor.execute(
            (
                "UPDATE crm_access.RateBucket SET Attem"
                "pts=1,WindowAt=SYSUTCDATETIME(),Locked"
                "Until=NULL WHERE InstitutionId=? AND B"
                "ucketHash=?"
            ),
            institution(settings),
            bucket,
        )
        return True
    if current["Attempts"] >= limit:
        return False
    cursor.execute(
        (
            "UPDATE crm_access.RateBucket SET Attem"
            "pts=Attempts+1 WHERE InstitutionId=? A"
            "ND BucketHash=?"
        ),
        institution(settings),
        bucket,
    )
    return True


def start_session(cursor, settings, value, *, mfa=False):
    raw, identity = token(), str(uuid4())
    csrf = csrf_token(settings, raw)
    cursor.execute(
        (
            "INSERT crm_access.Session(InstitutionI"
            "d,SessionId,UserId,TokenHash,CSRFHash,"
            "AuthVersion,IssuedAt,ExpiresAt,RecentA"
            "t,MFAAt) VALUES(?,?,?,?,?,?,SYSUTCDATE"
            "TIME(),DATEADD(hour,8,SYSUTCDATETIME()"
            "),SYSUTCDATETIME(),CASE WHEN ?=1 THEN "
            "SYSUTCDATETIME() ELSE NULL END)"
        ),
        institution(settings),
        identity,
        uid(str(value["UserId"])),
        bound_hash(settings, raw, "session"),
        token_hash(csrf),
        value["AuthVersion"],
        int(mfa),
    )
    audit(cursor, settings, uid(str(value["UserId"])), "auth.login", identity)
    return {
        "user": public_user(value),
        "session_id": identity,
        "actions": json.loads(value["Actions"]),
        "csrf_token": csrf,
        "mfa_required": False,
        "mfa_enabled": bool(mfa),
        "_token": raw,
    }


def factor_code(cursor, settings, identity, code):
    value = one(
        cursor,
        (
            "SELECT * FROM crm_access.Factor WITH(U"
            "PDLOCK,HOLDLOCK) WHERE InstitutionId=?"
            " AND UserId=? AND State='enabled'"
        ),
        institution(settings),
        identity,
    )
    if not value:
        return False
    secret = read_factor_secret(cursor, settings, value["SecretId"], identity)
    now = cursor.execute(
        ("SELECT DATEDIFF_BIG(second,CONVERT(datetime2,'19700101'),SYSUTCDATETIME())")
    ).fetchval()
    step = matching_step(
        secret,
        code,
        last=max(value["LastStep"], settings.ticket.get("mfa_floor", -1)),
        now=now,
    )
    if step is not None:
        cursor.execute(
            (
                "UPDATE crm_access.Factor SET LastStep="
                "? WHERE InstitutionId=? AND UserId=? A"
                "ND LastStep=?"
            ),
            step,
            institution(settings),
            identity,
            value["LastStep"],
        )
        return cursor.rowcount == 1
    if (
        isinstance(code, str)
        and len(code) == 32
        and all(c in "0123456789abcdefABCDEF" for c in code)
    ):
        cursor.execute(
            (
                "UPDATE crm_access.RecoveryCode SET Con"
                "sumedAt=SYSUTCDATETIME() WHERE Institu"
                "tionId=? AND UserId=? AND CodeHash=? A"
                "ND ConsumedAt IS NULL"
            ),
            institution(settings),
            identity,
            token_hash(code.lower()),
        )
        return cursor.rowcount == 1
    return False


class Identity:
    def __init__(self, settings):
        self.settings = settings

    def status(self):
        with transaction(self.settings, anonymous=True) as c:
            initialized = c.execute(
                (
                    "SELECT CASE WHEN InitializedAt IS NULL"
                    " THEN 0 ELSE 1 END FROM crm_access.Ins"
                    "titution WHERE InstitutionId=?"
                ),
                institution(self.settings),
            ).fetchval()
        return {"initialized": bool(initialized), "email_otp_available": False}

    def bootstrap(self, body):
        with transaction(self.settings, True, anonymous=True) as c:
            allowed = rate(c, self.settings, "bootstrap-global", 20, 900)
            current = one(
                c,
                (
                    "SELECT BootstrapHash,InitializedAt FRO"
                    "M crm_access.Institution WITH(UPDLOCK,"
                    "HOLDLOCK) WHERE InstitutionId=?"
                ),
                institution(self.settings),
            )
            if (
                not allowed
                or not current
                or current["InitializedAt"] is not None
                or not hmac.compare_digest(
                    bytes(current["BootstrapHash"] or b""),
                    token_hash(body.bootstrap_token.get_secret_value()),
                )
            ):
                audit(c, self.settings, None, "auth.bootstrap_denied", outcome="denied")
                result = None
            else:
                encoded = password_hash(body.password.get_secret_value())
                identity = str(uuid4())
                c.execute(
                    (
                        "INSERT crm_access.AccessUser(Instituti"
                        "onId,UserId,Login,NormalizedLogin,Disp"
                        "layName,Profile,PasswordHash,RoleKey,A"
                        "ctive,AuthVersion,Revision) VALUES(?,?"
                        ",?,?,?,?,?,'owner',1,1,1)"
                    ),
                    institution(self.settings),
                    identity,
                    body.email,
                    body.email,
                    body.full_name,
                    json.dumps(
                        {
                            "full_name": body.full_name,
                            "phone": "",
                            "role_label": "",
                            "avatar_url": "",
                            "timezone": "America/Bogota",
                        }
                    ),
                    encoded,
                )
                c.execute(
                    (
                        "UPDATE crm_access.Institution SET Boot"
                        "strapHash=NULL,InitializedAt=SYSUTCDAT"
                        "ETIME() WHERE InstitutionId=?"
                    ),
                    institution(self.settings),
                )
                audit(c, self.settings, identity, "auth.bootstrap", identity)
                result = start_session(
                    c, self.settings, user(c, self.settings, identity)
                )
        if result is None:
            raise HTTPException(403, "setup_unavailable")
        return result

    def login(self, body):
        with transaction(self.settings, True, anonymous=True) as c:
            allowed = rate(c, self.settings, "login-global", 120, 60) and rate(
                c, self.settings, "login:" + body.email, 10, 900
            )
            value = (
                one(
                    c,
                    (
                        "SELECT u.*,r.Actions,r.Active AS RoleA"
                        "ctive FROM crm_access.AccessUser u JOI"
                        "N crm_access.Role r ON r.InstitutionId"
                        "=u.InstitutionId AND r.RoleKey=u.RoleK"
                        "ey WHERE u.InstitutionId=? AND u.Norma"
                        "lizedLogin=?"
                    ),
                    institution(self.settings),
                    body.email,
                )
                if allowed
                else None
            )
            matches = allowed and password_matches(
                body.password.get_secret_value(),
                value["PasswordHash"] if value and value["PasswordHash"] else DUMMY,
            )
            result = None
            if (
                not allowed
                or not matches
                or not value
                or not value["Active"]
                or not value["RoleActive"]
            ):
                audit(
                    c,
                    self.settings,
                    None,
                    "auth.login_failed",
                    outcome="denied",
                    reason="rate" if not allowed else "credentials",
                )
            else:
                identity = uid(str(value["UserId"]))
                active = c.execute(
                    (
                        "SELECT COUNT(*) FROM crm_access.Factor"
                        " WHERE InstitutionId=? AND UserId=? AN"
                        "D State='enabled'"
                    ),
                    institution(self.settings),
                    identity,
                ).fetchval()
                if active:
                    raw = token()
                    c.execute(
                        (
                            "INSERT crm_access.Challenge(Institutio"
                            "nId,ChallengeId,UserId,TokenHash,Kind,"
                            "AuthVersion,Attempts,ExpiresAt) VALUES"
                            "(?,?,?,?,'login_mfa',?,0,DATEADD(minut"
                            "e,5,SYSUTCDATETIME()))"
                        ),
                        institution(self.settings),
                        str(uuid4()),
                        identity,
                        bound_hash(self.settings, raw, "challenge"),
                        value["AuthVersion"],
                    )
                    result = {"mfa_required": True, "challenge_token": raw}
                else:
                    result = start_session(c, self.settings, value)
        if not result:
            raise HTTPException(
                429 if not allowed else 401,
                "rate_limited" if not allowed else "invalid_credentials",
            )
        return result

    def verify_login(self, body):
        with transaction(self.settings, True, anonymous=True) as c:
            challenge = one(
                c,
                (
                    "SELECT * FROM crm_access.Challenge WIT"
                    "H(UPDLOCK,HOLDLOCK) WHERE InstitutionI"
                    "d=? AND TokenHash=? AND Kind='login_mf"
                    "a' AND ConsumedAt IS NULL AND ExpiresA"
                    "t>SYSUTCDATETIME() AND Attempts<8"
                ),
                institution(self.settings),
                bound_hash(
                    self.settings, body.challenge_token.get_secret_value(), "challenge"
                ),
            )
            result = None
            if challenge:
                identity = uid(str(challenge["UserId"]))
                value = user(c, self.settings, identity)
                c.execute(
                    (
                        "UPDATE crm_access.Challenge SET Attemp"
                        "ts=Attempts+1 WHERE InstitutionId=? AN"
                        "D ChallengeId=?"
                    ),
                    institution(self.settings),
                    challenge["ChallengeId"],
                )
                if (
                    value
                    and value["AuthVersion"] == challenge["AuthVersion"]
                    and factor_code(
                        c, self.settings, identity, body.code.get_secret_value()
                    )
                ):
                    c.execute(
                        (
                            "UPDATE crm_access.Challenge SET Consum"
                            "edAt=SYSUTCDATETIME() WHERE Institutio"
                            "nId=? AND ChallengeId=? AND ConsumedAt"
                            " IS NULL"
                        ),
                        institution(self.settings),
                        challenge["ChallengeId"],
                    )
                    if c.rowcount == 1:
                        result = start_session(c, self.settings, value, mfa=True)
            if not result:
                audit(c, self.settings, None, "auth.mfa_failed", outcome="denied")
        if not result:
            raise HTTPException(401, "invalid_challenge_or_code")
        return result

    def authenticate(self, authority):
        with transaction(self.settings, True, anonymous=True) as c:
            value = authorize(
                c, self.settings, authority, authority.get("permission", "self")
            )
            configured = c.execute(
                (
                    "SELECT Document FROM crm_access.Settin"
                    "g WHERE InstitutionId=? AND Section='b"
                    "udgets'"
                ),
                institution(self.settings),
            ).fetchval()
            allowed = rate(
                c,
                self.settings,
                "api:" + value["UserId"],
                json.loads(configured)["requests_per_minute"],
                60,
            )
            if not allowed:
                audit(
                    c,
                    self.settings,
                    value["UserId"],
                    "auth.rate_denied",
                    outcome="denied",
                )
        if not allowed:
            raise HTTPException(429, "rate_limited")
        return value

    def me(self, authority):
        with transaction(self.settings, anonymous=True) as c:
            value = authorize(c, self.settings, authority)
            return {
                "user": public_user(value),
                "session_id": value["SessionId"],
                "actions": json.loads(value["Actions"]),
                "csrf_token": csrf_token(self.settings, authority["token"]),
                "mfa_enabled": value["MFAState"] == "enabled",
            }

    def logout(self, authority):
        with transaction(self.settings, True, anonymous=True) as c:
            value = authorize(c, self.settings, authority)
            c.execute(
                (
                    "UPDATE crm_access.Session SET RevokedA"
                    "t=SYSUTCDATETIME() WHERE InstitutionId"
                    "=? AND SessionId=?"
                ),
                institution(self.settings),
                value["SessionId"],
            )
            audit(c, self.settings, value["UserId"], "auth.logout", value["SessionId"])
        return {"signed_out": True}

    def reauthenticate(self, authority, body):
        with transaction(self.settings, True, anonymous=True) as c:
            value = authorize(c, self.settings, authority)
            allowed = rate(c, self.settings, "reauth:" + value["UserId"], 10, 900)
            valid = allowed and password_matches(
                body.current_password.get_secret_value(), value["PasswordHash"]
            )
            mfa_ok = value["MFAState"] != "enabled" or bool(value["RecentMFA"])
            if valid and not mfa_ok and body.code:
                mfa_ok = factor_code(
                    c, self.settings, value["UserId"], body.code.get_secret_value()
                )
                if mfa_ok:
                    c.execute(
                        (
                            "UPDATE crm_access.Session SET MFAAt=SY"
                            "SUTCDATETIME() WHERE InstitutionId=? A"
                            "ND SessionId=?"
                        ),
                        institution(self.settings),
                        value["SessionId"],
                    )
            if valid and mfa_ok:
                c.execute(
                    (
                        "UPDATE crm_access.Session SET RecentAt"
                        "=SYSUTCDATETIME() WHERE InstitutionId="
                        "? AND SessionId=?"
                    ),
                    institution(self.settings),
                    value["SessionId"],
                )
                audit(
                    c,
                    self.settings,
                    value["UserId"],
                    "auth.confirmed",
                    value["SessionId"],
                )
            else:
                audit(
                    c,
                    self.settings,
                    value["UserId"],
                    "auth.confirmation_failed",
                    value["SessionId"],
                    outcome="denied",
                )
        if not valid or not mfa_ok:
            raise HTTPException(401, "confirmation_failed")
        return {"confirmed": True}
