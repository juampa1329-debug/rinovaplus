"""Issue an independent profile for a populated native P2 restoration.

Only the new target receives login/ACL changes and anti-replay retirement.
Institutional accounts, encrypted material, settings and audit history survive.
"""
import base64
import hashlib
import secrets
import time

from app.es_schema_profile import journal_digest
from app.institutional.db import audit, institution, key, uid
from app.institutional.crypto import unseal
from app.institutional.spanish import RIGHTS, load, qualified_shape, transaction
from app.institutional.spanish_bindings import Cursor, principal
from app.parity_channels.catalog import metadata
from app.parity_channels.policy import COLUMNS
from app.sql_profile import SqlProfileStore
from tools.foundation_snapshot import quote_name as q, sha
from tools.rehearse_foundation import literal
from tools.rehearse_p2_spanish import WORK, admin, fresh, save
from tools.p2_es_recovery import restore
from tools.es_schema_migrate_v2 import identity


def restore_profile(checkpoint, source_settings):
    if checkpoint.get("source") != source_settings.ticket["identity"]:
        raise ValueError("P2ES_backup_profile_identity_mismatch")
    if hashlib.sha256(key(source_settings)).hexdigest() != source_settings.ticket["secret_key_sha256"]:
        raise ValueError("P2ES_backup_profile_key_mismatch")
    # This read-only guard precedes creating a target or login. A valid profile
    # of a different copy is not authority to select the backup's AES key.
    with transaction(source_settings,anonymous=True):
        pass
    name=fresh("RECOVERY")
    with admin("master") as connection:
        native=restore(connection,checkpoint,name,restricted=True)
    with admin(name) as connection:
        actual=identity(connection.cursor())
    user = principal(name)
    directory = WORK / "profiles" / name
    assert not directory.exists()
    value = {"revision": 1, "connection": dict(source_settings.connection, database=name, username=user, password="CBN!"+secrets.token_urlsafe(48)), "review": {"session_token": secrets.token_urlsafe(48), "secrets_key": source_settings.review["secrets_key"]}}
    mapping = source_settings.ticket["table_map"]
    with admin("master") as connection:
        c = connection.cursor()
        c.execute("CREATE LOGIN "+q(user)+" WITH PASSWORD="+literal(value["connection"]["password"])+",DEFAULT_DATABASE="+q(name)+",CHECK_POLICY=ON,CHECK_EXPIRATION=OFF")
        sid=c.execute("SELECT CONVERT(varchar(170),SUSER_SID(?),2)",user).fetchval()
        protected=[r[0] for r in c.execute("SELECT name FROM sys.server_principals WHERE type IN('S','U','G') AND name<>?",user).fetchall()]
    with admin(name) as connection:
        c=connection.cursor()
        c.execute("DENY CONNECT TO "+q(source_settings.connection["username"]))
        c.execute("CREATE USER "+q(user)+" FOR LOGIN "+q(user)+" WITH DEFAULT_SCHEMA=dbo;GRANT CONNECT,VIEW DEFINITION TO "+q(user))
        for logical, rights in RIGHTS.items():
            c.execute("GRANT "+",".join(rights)+" ON OBJECT::"+mapping.get(logical,logical)+" TO "+q(user))
        for logical, columns in COLUMNS.items():
            c.execute("GRANT SELECT ON OBJECT::"+mapping[logical]+"("+",".join(map(q,columns))+") TO "+q(user))
        for table in source_settings.ticket["academic_tables"]:
            c.execute("DENY SELECT,INSERT,UPDATE,DELETE,ALTER,REFERENCES ON OBJECT::"+table+" TO "+q(user))
        c.execute("DENY EXECUTE ON SCHEMA::dbo TO "+q(user))
        # Database-bound HMACs and a new session key already reject old tokens.
        # Explicitly retire restored factors that could otherwise roll back a
        # one-use code consumed after the backup. Never disable the authenticator.
        mapped=Cursor(c,mapping)
        # Authenticate every encrypted record before issuing a usable profile.
        # A native structural/data comparison alone cannot prove decryptability.
        encrypted=mapped.execute("SELECT SecretId,Scope,OwnerRef,Kind,VersionNo,KeyId,Nonce,Ciphertext FROM crm_access.Secret").fetchall()
        for row in encrypted:
            binding={"institution":institution(source_settings),"scope":row[1],"owner":row[2],"kind":row[3],"version":row[4],"secret_id":uid(str(row[0]))}
            if row[5] != hashlib.sha256(key(source_settings)).hexdigest()[:32]:
                raise ValueError("P2ES_restored_secret_key_id")
            unseal(key(source_settings),binding,row[6],row[7])
        mapped.execute("BEGIN TRANSACTION")
        try:
            # Same clock as auth.factor_code; the helper host can be skewed.
            floor=int(mapped.execute("SELECT DATEDIFF_BIG(second,'19700101',SYSUTCDATETIME())/30").fetchval())+1
            mapped.execute("UPDATE crm_access.Session SET RevokedAt=ISNULL(RevokedAt,SYSUTCDATETIME())")
            mapped.execute("UPDATE crm_access.Challenge SET ConsumedAt=ISNULL(ConsumedAt,SYSUTCDATETIME())")
            mapped.execute("UPDATE crm_access.RecoveryCode SET ConsumedAt=ISNULL(ConsumedAt,SYSUTCDATETIME())")
            mapped.execute("UPDATE crm_access.Factor SET LastStep=CASE WHEN LastStep<? THEN ? ELSE LastStep END,PendingSecretId=NULL,SetupId=NULL,SetupSessionId=NULL,SetupExpiresAt=NULL",floor,floor)
            audit(mapped,source_settings,None,"security.native_restore",name,reason="retire_restored_tokens_and_recovery_codes")
            mapped.execute("COMMIT")
        except BaseException:
            mapped.execute("IF @@TRANCOUNT>0 ROLLBACK")
            raise
        catalog=metadata(c)
        ticket=dict(source_settings.ticket,identity=actual,sid=sid,catalog_sha256=sha(catalog),qualified_shape_sha256=qualified_shape(c),journal_sha256=journal_digest(c),secret_key_sha256=hashlib.sha256(base64.b64decode(value["review"]["secrets_key"])).hexdigest(),session_sha256=hashlib.sha256(value["review"]["session_token"].encode()).hexdigest(),protected_logins=protected,principals=sorted(r["name"] for r in catalog["principals"]),expires_at=int(time.time())+365*86400,mfa_floor=floor,restored_from={"source_database":checkpoint["source"]["database"],"backup_uuid":checkpoint["backup_uuid"]})
    directory.mkdir(mode=0o700,parents=True)
    save(directory/"ticket.json",ticket)
    value["review"]["ticket_sha256"]=hashlib.sha256((directory/"ticket.json").read_bytes()).hexdigest()
    SqlProfileStore(directory/"runtime").save(value)
    restored_settings=load(directory)
    with admin(name) as connection:
        c=connection.cursor()
        assert c.execute("SELECT user_access_desc FROM sys.databases WHERE database_id=DB_ID()").fetchval()=="RESTRICTED_USER"
        c.execute("ALTER DATABASE "+q(name)+" SET MULTI_USER")
    with transaction(restored_settings,anonymous=True) as c:
        assert c.execute("SELECT COUNT(*) FROM crm_access.AccessUser").fetchval()>0
    return {"database":name,"directory":str(directory),"native_restore":native,"identity":actual,"mfa_floor":floor}
