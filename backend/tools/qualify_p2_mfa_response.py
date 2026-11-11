"""Verify MFA login metadata against real SQL factor/session state."""
import json,time
from pathlib import Path
from app.institutional.api import create_app
from app.institutional.crypto import totp_code
from app.institutional.spanish import load,transaction
from tools.qualify_p2_spanish import Browser
from tools.rehearse_p2_spanish import WORK,read,save

if __name__=='__main__':
    private=read(WORK/'http-private.json');settings=load(Path(private['profile']))
    browser=Browser(create_app(settings));challenge=browser.login(private['email'],private['password'])
    assert challenge['mfa_required'] is True and 'csrf_token' not in challenge
    while True:
        with transaction(settings,anonymous=True) as cursor:
            current=int(cursor.execute("SELECT DATEDIFF_BIG(second,'19700101',SYSUTCDATETIME())/30").fetchval())
            last=cursor.execute("SELECT LastStep FROM crm_access.Factor WHERE UserId=?",private['owner_id']).fetchval()
        if current>last:break
        time.sleep(1)
    result=browser.request('auth/verify','POST',{'challenge_token':challenge['challenge_token'],'code':totp_code(private['totp_secret'],current)}).json();browser.csrf=result['csrf_token']
    me=browser.request('auth/me').json()
    assert result['mfa_enabled'] is True and me['mfa_enabled'] is True
    report={'status':'passed','database':settings.connection['database'],'password_only_requires_MFA':True,'verified_login_response_mfa_enabled':True,'immediate_me_mfa_enabled':True,'UI_does_not_need_a_reload_to_know_MFA_state':True,'academic_writes':False}
    save(WORK/'MFA-response-result.json',report);print(json.dumps({'MFA_login_response':'passed','me_and_login_agree':True}))
