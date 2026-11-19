"""Native SQL and real ffmpeg under rollback; no provider IO, no persistent CRM writes."""
import json, subprocess
from uuid import uuid4
from fastapi import HTTPException
from app.institutional.postgres_rehearsal import apply_environment
from app.institutional.store import transaction
from app.institutional.db import institution, one
from app.institutional import voice_audio as v, channel_media as media
from app.institutional.voice_policy import VoicePolicy
from app.modules.inbox.infrastructure import media_files as files
s=apply_environment(); inst=institution(s); ids=[]; mediaid=str(uuid4()); checks={}
class Rollback(Exception): pass
original=v.policy
try:
    with transaction(s,True,anonymous=True) as c:
        identity=one(c,"SELECT TOP(1) i.* FROM crm_channels2.ExternalIdentity i JOIN crm_channels2.Integration a ON a.InstitutionId=i.InstitutionId AND a.IntegrationId=i.IntegrationId WHERE i.InstitutionId=? AND a.Channel='whatsapp' AND i.ExternalId LIKE '%44' ORDER BY i.CreatedAt",inst)
        assert identity
        application=c.execute("SELECT ApplicationId FROM crm_channels2.Integration WHERE InstitutionId=? AND IntegrationId=?",inst,identity['IntegrationId']).fetchval()
        p=VoicePolicy(enabled=True,scope='all',max_audios_per_conversation=2,default_profile_id='native-fixture',profiles=[{'id':'native-fixture','name':'P19 native rollback fixture','voice_id':'synthetic-voice','model_id':'synthetic-model'}])
        v.policy=lambda *_:p
        base=v.usage(c,s,str(identity['ConversationId']))['used']
        p.max_audios_per_conversation=base+2
        def reserve():
            id=str(uuid4()); ids.append(id)
            data={'conversation':str(identity['ConversationId']),'characters':4,'profile':p.profiles[0].model_dump(),'media':str(uuid4())}
            return id,data,v.reserve(c,s,id,application,identity['IntegrationId'],v.ACTOR,data)
        id,data,first=reserve(); assert first
        assert not v.reserve(c,s,id,application,identity['IntegrationId'],v.ACTOR,data)
        checks['duplicate_paid_intent_suppressed']=True
        v.complete(c,s,id,'uncertain','synthetic_timeout',data)
        assert reserve()[2]
        try: reserve(); raise AssertionError('quota not enforced')
        except HTTPException as e: assert e.detail=='voice_conversation_limit'
        checks['quota_includes_uncertain_and_survives_policy_reload']=v.usage(c,s,str(identity['ConversationId']))['used']==base+2
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i','sine=frequency=440:duration=1','-codec:a','libmp3lame','-f','mp3',str(files.path(mediaid,'.part'))],check=True,timeout=15)
        info=files.inspect_file(mediaid,'synthetic.mp3'); info['name']='nota-de-voz.ogg'
        assert info['mime']=='audio/ogg' and 0<info['duration']<3
        c.execute("INSERT crm_channels4.MediaAsset(MediaId,InstitutionId,IntegrationId,IdentityId,ConversationId,SourceKind,State,Kind,FileName,ProviderReference) VALUES(?,?,?,?,?,'provider','processing','audio','nota-de-voz.ogg','{}')",mediaid,inst,identity['IntegrationId'],identity['IdentityId'],identity['ConversationId'])
        media.mark_ready(c,s,mediaid,info,{'voice':True,'generatedBy':'p19-native-fixture'})
        row,blob=media.file_for(c,s,mediaid,conversation=str(identity['ConversationId']))
        assert blob['mime']=='audio/ogg'
        checks['real_ffmpeg_ogg_opus_and_private_asset_binding']=True
        checks['duration_seconds']=round(info['duration'],3)
        raise Rollback()
except Rollback: pass
finally:
    v.policy=original
    for suffix in ['.part','.checked','.bin']: files.path(mediaid,suffix).unlink(missing_ok=True)
with transaction(s,anonymous=True) as c:
    assert all(not c.execute('SELECT 1 FROM crm_channels2.ProviderOperation WHERE InstitutionId=? AND OperationId=?',inst,id).fetchone() for id in ids)
    assert not c.execute('SELECT 1 FROM crm_channels4.MediaAsset WHERE InstitutionId=? AND MediaId=?',inst,mediaid).fetchone()
checks['rollback_and_exact_file_cleanup']=True
print('P19_NATIVE_ROLLBACK',json.dumps(checks))
