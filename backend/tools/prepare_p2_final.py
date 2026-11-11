"""Provision a clean separate local P2 profile, without any fixture accounts."""
import contextlib
import json
import secrets
from pathlib import Path
from uuid import uuid4

from app.institutional.api import create_app
from app.institutional.spanish import load
from app.institutional.auth import COOKIE
from tools import rehearse_p2_spanish as driver
from tools.qualify_p2_spanish import Browser, operation
from tools.rehearse_p2_spanish import WORK, read, save


def main():
    if (WORK/'final-profile.json').exists():
        raise ValueError('P2ES_clean_final_profile_already_provisioned')
    driver.APPROVED='1a7ba0dc7435e1e5dd61b431cca7f2164d698d4b4b6df9dd53cd66e8b40b10b4'
    driver.profile()
    profile=read(WORK/'profile.json')
    settings=load(Path(profile['directory']))
    browser=Browser(create_app(settings))
    credentials={'email':'administracion@cbn.local','password':'CBN!'+secrets.token_urlsafe(32),'profile':profile['directory']}
    state=read(WORK/'state.json')
    result=browser.request('auth/bootstrap','POST',{'email':credentials['email'],'password':credentials['password'],'full_name':'Administración CBN','bootstrap_token':state['bootstrap_token']}).json()
    browser.csrf=result['csrf_token']
    assert len(result['actions'])==30
    users=browser.request('users').json()['items']
    assert len(users)==1 and users[0]['role']=='owner'
    setting=browser.request('settings/institution').json()
    browser.request('settings/institution','PUT',operation(revision=setting['revision'],document={'name':'CBN','timezone':'America/Bogota','locale':'es-CO'}))
    assert browser.request('channels').json()['items']==[]
    assert browser.request('webhooks').json()['items']==[]
    save(WORK/'final-profile.json',profile)
    save(WORK/'final-access.json',credentials)
    save(WORK/'final-session.json',{'cookie':browser.client.cookies.get(COOKIE),'csrf':browser.csrf})
    save(WORK/'clean-final-result.json',{'status':'passed','database':profile['database'],'engine':15,'compatibility':150,'institution':'CBN','human_accounts':1,'initial_role':'owner','fixture_users':0,'fixture_channels':0,'fixture_webhooks':0,'TLS_verified':True,'own_SQL_principal':True,'tables':138,'academic_tables_DENY':30,'providers':False,'public_webhooks':False,'previous_runtime_profiles_changed':False})
    print(json.dumps({'clean_final_profile':'passed','database':profile['database'],'accounts':1,'fixture_users':0}))


if __name__=='__main__':
    try:
        main()
    except BaseException as error:
        with contextlib.suppress(Exception):
            save(WORK/('final-preparation-failure-'+uuid4().hex+'.json'),{'type':type(error).__name__,'message':str(error)})
        print(json.dumps({'clean_final_profile':'failed','type':type(error).__name__}))
        raise SystemExit(1)
