"""Document every installed HTTP method/path without opening SQL."""
import json
from pathlib import Path
from types import SimpleNamespace

from app.institutional.api import PUBLIC, core_permission, create_app
from app.institutional.policy import ACTIONS
from app.institutional.spanish_bindings import VERSION

ROOT=Path(__file__).resolve().parents[2]


def matrix():
    app=create_app(SimpleNamespace(ticket={'version':VERSION}),workspace=object())
    result=[]
    for path,operations in sorted(app.openapi()['paths'].items()):
        for method in sorted(operations):
            method=method.upper();action='self';recent=False;conditions=[]
            if path in PUBLIC or path=='/health/live':action='anonymous_local_boundary'
            elif path.startswith('/api/local/'):
                action,module=core_permission(path,method);conditions.append('institutional module '+str(module)+' must be enabled')
            elif path.startswith('/api/institution/settings/'):
                action='settings.{scope(section)}.'+('read' if method=='GET' else 'write')
                conditions.append('section: institution,ai,models→providers,webhooks,modules,budgets only')
                recent=True if '/restore/' in path else 'only models/budgets/webhooks on PUT' if method=='PUT' else False
            elif path.startswith('/api/institution/credentials'):
                action='settings.{scope(provider|channel|webhook)}.'+('read' if method=='GET' else 'write');recent=method!='GET';conditions.append('typed scope/kind and real institution-bound application/integration/endpoint owner')
            elif path.startswith('/api/institution/users'):
                action='users.read' if method=='GET' else 'users.manage';recent=method!='GET';conditions.extend(['owner assignment requires owner','last useful owner/administrator must remain','revisions and AuthVersion revoke stale sessions'])
            elif path.startswith('/api/institution/roles'):
                action='roles.read' if method=='GET' else 'roles.manage';recent=method!='GET';conditions.extend(['protected owner/admin immutable','no permission grant beyond actor authority'])
            elif path.startswith('/api/institution/channels'):
                action='settings.channels.'+('read' if method=='GET' else 'write');recent=method!='GET';conditions.extend(['immutable application/account namespace','rowversion + configuration revision','provider operations disabled'])
            elif path.startswith('/api/institution/webhooks'):
                action='settings.webhooks.'+('read' if method=='GET' else 'write');recent=method!='GET';conditions.extend(['real integration/application IDs','one endpoint UUID for config/links/secrets','one-time generated secrets never stored in operation receipt','no public ingress'])
            elif path.startswith('/api/institution/sessions'):
                conditions.append('self sessions only; sessions.manage required to list/revoke another user session; owner target requires owner actor');recent='only revoking another user session' if method!='GET' else False
            elif path=='/api/institution/audit':action='audit.read'
            elif path.startswith('/api/institution/security/'):
                recent=True;conditions.append('current password and enabled MFA verified by server; one-use setup/recovery/challenges')
            elif path=='/api/institution/profile':conditions.append('own user only; current password + recent auth and session revocation on email change')
            elif path=='/api/institution/auth/confirm':conditions.append('verifies current password and enabled MFA; confirmation does not grant a new role')
            elif path in {'/api/institution/runtime','/api/institution/contracts'}:conditions.append('authenticated metadata only; no credentials or SQL configuration')
            result.append({'method':method,'path':path,'action':action,'recent_authentication':recent,'conditions':conditions,'audit':'accepted business mutations append safe metadata in the same SQL transaction; denied/failed requests independently append status/resource pattern, never body/query/secret' if path.startswith('/api/') else 'liveness only'})
    assert result and all(row['action']=='self' or row['action']=='anonymous_local_boundary' or row['action'] in ACTIONS or '{scope' in row['action'] for row in result)
    return {'version':'cbn-p2-method-route-action-v1','SQL_connections':0,'known_actions':list(ACTIONS),'rows':result,'count':len(result),'default':'unknown method/path denied404; no owner-preview fallback','live_roles':'re-read and authorize in same serializable business transaction; middleware also checks core permission before DTO','audit_SQL_permissions':'SELECT/INSERT only; UPDATE/DELETE/ALTER denied','provider_and_academic_writes':False}


if __name__=='__main__':
    value=matrix();path=ROOT/'docs/adaptation/sql/p2-endpoint-permissions.json';path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'route_method_action_rows':value['count'],'actions':len(value['known_actions']),'SQL_connections':0}))
