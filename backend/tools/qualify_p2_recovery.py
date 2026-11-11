"""Populated backup/restore and anti-replay qualification on a new copy."""
import contextlib
import hashlib
import json
import time
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from app.institutional.api import create_app
from app.institutional.crypto import totp_code
from app.institutional.spanish import load
from app.institutional.spanish_bindings import Cursor
from tools.foundation_snapshot import encode
from tools.p2_es_recovery import backup
from tools.p2_profile_restore import restore_profile
from tools.qualify_p2_spanish import Browser, operation
from tools.rehearse_p2_spanish import WORK, admin, read, save


def fingerprint(cursor, table, *, max_event=None):
    sql="SELECT * FROM "+table
    args=[]
    if max_event is not None:
        sql+=" WHERE EventId<=?"
        args=[max_event]
    values=[hashlib.sha256(encode(list(row))).digest() for row in cursor.execute(sql,*args).fetchall()]
    return {"rows":len(values),"sha256":hashlib.sha256(b"".join(sorted(values))).hexdigest()}


def main():
    profile,private=read(WORK/"profile.json"),read(WORK/"http-private.json")
    settings=load(Path(profile["directory"]))
    app=create_app(settings)
    owner=Browser(app)
    owner.login(private["users"]["admin"]["email"],private["users"]["admin"]["password"])
    invite=owner.request("users","POST",operation(email="restore.invite@cbn.local",full_name="Invitación del respaldo",role="viewer")).json()
    # Use the actual cookie contract; its value is never put in the report.
    from app.institutional.auth import COOKIE
    old_cookie=owner.client.cookies.get(COOKIE)
    with admin(profile["database"]) as connection:
        c=connection.cursor()
        before={logical:fingerprint(c,settings.ticket["table_map"][logical]) for logical in ("crm_access.AccessUser","crm_access.Role","crm_access.Secret","crm_access.Setting","crm_access.SettingHistory")}
        audit_table=settings.ticket["table_map"]["crm_access.Audit"]
        audit_max=c.execute("SELECT MAX(EventId) FROM "+audit_table).fetchval()
        old_audit=fingerprint(c,audit_table,max_event=audit_max)
        checkpoint=backup(connection,settings.ticket["identity"])
        sql_step=int(c.execute("SELECT DATEDIFF_BIG(second,'19700101',SYSUTCDATETIME())/30").fetchval())
    save(WORK/"populated-backup.json",checkpoint)
    # Consume a code after the backup; restoring its previous unused row must
    # not make it usable again. Keep source accounts and ordinary passwords.
    mfa=Browser(app)
    challenge=mfa.login(private["email"],private["password"])
    mfa.request("auth/verify","POST",{"challenge_token":challenge["challenge_token"],"code":private["recovery_codes"][1]})
    mfa2=Browser(app)
    challenge=mfa2.login(private["email"],private["password"])
    old_totp=totp_code(private["totp_secret"],sql_step+1)
    mfa2.request("auth/verify","POST",{"challenge_token":challenge["challenge_token"],"code":old_totp})
    # A profile of another valid copy with the same InstitutionId is rejected
    # before any destination/login side effect.
    other=next(p for p in (WORK/"profiles").iterdir() if p.name!=profile["database"] and (p/"ticket.json").is_file())
    with admin("master") as connection:
        c=connection.cursor()
        counts=tuple(c.execute("SELECT (SELECT COUNT(*) FROM sys.databases),(SELECT COUNT(*) FROM sys.server_principals)").fetchone())
    try:
        restore_profile(checkpoint,load(other))
    except ValueError as error:
        assert str(error)=="P2ES_backup_profile_identity_mismatch"
    else:
        raise AssertionError("foreign_profile_accepted")
    with admin("master") as connection:
        assert tuple(connection.cursor().execute("SELECT (SELECT COUNT(*) FROM sys.databases),(SELECT COUNT(*) FROM sys.server_principals)").fetchone())==counts
    # Deliberately skew the process by a day. SQL UTC remains authoritative for
    # the replay floor and is verified independently after the helper returns.
    with patch("tools.p2_profile_restore.time.time",return_value=time.time()-86400):
        restored=restore_profile(checkpoint,settings)
    recovered=load(Path(restored["directory"]))
    with admin(restored["database"]) as connection:
        c=connection.cursor()
        for logical, expected in before.items():
            assert fingerprint(c,recovered.ticket["table_map"][logical])==expected,logical
        assert fingerprint(c,recovered.ticket["table_map"]["crm_access.Audit"],max_event=audit_max)==old_audit
        now=int(c.execute("SELECT DATEDIFF_BIG(second,'19700101',SYSUTCDATETIME())/30").fetchval())
        assert now <= restored["mfa_floor"] <= now+1
        mapped=Cursor(c)
        assert mapped.execute("SELECT COUNT(*) FROM crm_access.RecoveryCode WHERE ConsumedAt IS NULL").fetchval()==0
        assert mapped.execute("SELECT COUNT(*) FROM crm_access.Factor WHERE State='enabled'").fetchval()==1
        assert c.execute("SELECT user_access_desc FROM sys.databases WHERE database_id=DB_ID()").fetchval()=="MULTI_USER"
        # The source login is denied access only on the restored database.
        assert c.execute("SELECT state_desc FROM sys.database_permissions WHERE class=0 AND permission_name='CONNECT' AND grantee_principal_id=USER_ID(?)",settings.connection["username"]).fetchval()=="DENY"
    target=Browser(create_app(recovered))
    target.client.cookies.set(COOKIE,old_cookie,domain="127.0.0.1",path="/api")
    target.request("auth/me",expected=401)
    target.request("auth/redeem","POST",{"token":invite["activation_token"],"new_password":"CBN!"+uuid4().hex},expected=401)
    challenge=target.login(private["email"],private["password"])
    target.request("auth/verify","POST",{"challenge_token":challenge["challenge_token"],"code":private["recovery_codes"][1]},expected=401)
    target.request("auth/verify","POST",{"challenge_token":challenge["challenge_token"],"code":old_totp},expected=401)
    # Wait for a genuinely new current TOTP, without moving either SQL clock or
    # accepted replay barrier. The tool runs asynchronously; no user UI sleeps.
    while True:
        with admin(restored["database"],readonly=True) as connection:
            current=int(connection.cursor().execute("SELECT DATEDIFF_BIG(second,'19700101',SYSUTCDATETIME())/30").fetchval())
        if current>restored["mfa_floor"]:
            break
        time.sleep(1)
    signed=target.request("auth/verify","POST",{"challenge_token":challenge["challenge_token"],"code":totp_code(private["totp_secret"],current)}).json()
    target.csrf=signed["csrf_token"]
    setting=target.request("settings/institution").json()
    result=target.request("settings/institution/restore/1","POST",operation(revision=setting["revision"],document={})).json()
    assert result["revision"]==setting["revision"]+1
    assert target.request("users").json()["items"]
    assert target.request("auth/me").json()["mfa_enabled"]
    # Only the private acceptance volume gets the new cookie for running the
    # previous immutable application image against this compatible profile.
    save(WORK/"restore-consumer-private.json",{"cookie":target.client.cookies.get(COOKIE),"csrf":target.csrf,"profile":restored["directory"],"users":before["crm_access.AccessUser"]["rows"],"audit_prefix":old_audit,"audit_max":audit_max})
    save(WORK/"restore-profile.json",restored)
    report={"status":"passed","source":profile["database"],"target":restored["database"],"native":restored["native_restore"],"populated_accounts":before["crm_access.AccessUser"]["rows"],"preserved_tables":before,"audit_prefix_preserved":old_audit,"all_ciphertexts_authenticated":True,"MFA_remains_enabled":True,"old_cookie_and_invite_rejected":True,"post_backup_consumed_recovery_rejected":True,"post_backup_TOTP_replay_rejected":True,"fresh_current_TOTP_accepted":True,"SQL_clock_floor_with_process_skew":True,"mismatched_profile_rejected_before_effects":True,"old_SQL_login_denied_only_in_new_target":True,"configuration_history_restore":True,"source_academic_writes":False,"scope":"checkpoint_contents_preserved; later source changes are outside backup"}
    save(WORK/"recovery-result.json",report)
    print(json.dumps({"populated_recovery":"passed","accounts":report["populated_accounts"],"target":restored["database"]}))


if __name__=="__main__":
    try:
        main()
    except BaseException as error:
        with contextlib.suppress(Exception):
            import traceback
            save(WORK/("recovery-failure-"+uuid4().hex+".json"),{"type":type(error).__name__,"message":str(error),"frames":traceback.format_exc()})
        print(json.dumps({"populated_recovery":"failed","type":type(error).__name__}))
        raise SystemExit(1)
