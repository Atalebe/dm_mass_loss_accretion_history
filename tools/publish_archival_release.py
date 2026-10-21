"""Publish exactly v1.0.0 after hosted integrity checks; no local credentials.

Only the GitHub-provided, repository-scoped workflow token is used. A failed
upload leaves its draft for explicit inspection; it never deletes a tag or
creates an alternative release to conceal a failure.
"""
from pathlib import Path
import argparse, hashlib, json, os, re, subprocess, urllib.request, urllib.error
from verify_archival_release import ROOT, REPOSITORY, TAG, VERSION, verify, need
API='https://api.github.com'
def validate_environment(e):
    need(e.get('GITHUB_ACTIONS')=='true','Publication requires the authorized hosted workflow')
    need(e.get('GITHUB_REPOSITORY')==REPOSITORY,'Wrong repository')
    need(e.get('GITHUB_EVENT_NAME')=='push' and e.get('GITHUB_REF')=='refs/tags/'+TAG,'Wrong triggering event/tag')
    need(bool(re.fullmatch(r'[0-9a-f]{40}',e.get('GITHUB_SHA',''))),'Invalid source commit')
    need(bool(e.get('GITHUB_TOKEN')),'Missing short-lived workflow token')
def request(method,path,token,payload=None,data=None,content_type='application/json',allow_missing=False):
    url=path if path.startswith('https://') else API+path
    need(url.startswith(API+'/repos/'+REPOSITORY+'/') or url.startswith('https://uploads.github.com/repos/'+REPOSITORY+'/'),'Unexpected request destination')
    body=json.dumps(payload).encode() if payload is not None else data
    req=urllib.request.Request(url,data=body,method=method,headers={'Accept':'application/vnd.github+json','Authorization':'Bearer '+token,'X-GitHub-Api-Version':'2022-11-28','User-Agent':'halo-paper-authorized-release','Content-Type':content_type})
    try:
        with urllib.request.urlopen(req,timeout=180) as r:return json.load(r)
    except urllib.error.HTTPError as exc:
        if allow_missing and exc.code==404:return None
        raise RuntimeError('GitHub release API returned HTTP '+str(exc.code)) from None

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--publish',action='store_true');args=p.parse_args()
    verified=verify();print(json.dumps(verified),flush=True)
    if not args.publish:
        print('DRY_RUN_ONLY_NO_NETWORK_WRITE');return
    env=os.environ;validate_environment(env)
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    need(sha==env['GITHUB_SHA'],'Checkout differs from triggered commit')
    need(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()=='','Checkout changed')
    token=env['GITHUB_TOKEN'];prefix='/repos/'+REPOSITORY+'/releases'
    existing=request('GET',prefix+'/tags/'+TAG,token,allow_missing=True)
    need(existing is None,'Release already exists: inspect it rather than overwrite')
    listed=request('GET',prefix+'?per_page=100',token)
    need(not any(r['tag_name']==TAG for r in listed),'A draft/release for this tag already exists; inspect saved state')
    notes=(ROOT/'docs/RELEASE_NOTES_v1.0.0.md').read_text()+'\n\nExact source commit: `'+sha+'`.\n'
    record=request('POST',prefix,token,payload={'tag_name':TAG,'target_commitish':sha,'name':'v1.0.0 — Mass-loss dependence of accretion-history correlations','body':notes,'draft':True,'prerelease':False,'generate_release_notes':False})
    rid=record['id'];temp=Path(env['RUNNER_TEMP']);receipt=temp/'halo-release-publication.json'
    def save(status,**extra):
        receipt.write_text(json.dumps(dict(status=status,repository=REPOSITORY,tag=TAG,commit=sha,release_id=rid,**extra),indent=2)+'\n')
    save('DRAFT_CREATED')
    assets=[('Mass_Loss_Accretion_History.pdf',ROOT/'paper/Mass_Loss_Accretion_History.pdf'),('Supplementary_Material.pdf',ROOT/'paper/Supplementary_Material.pdf')]
    sums={'tag':TAG,'source_commit':sha,'manifest_sha256':hashlib.sha256((ROOT/'MANIFEST.json').read_bytes()).hexdigest(),'assets':{n:hashlib.sha256(f.read_bytes()).hexdigest() for n,f in assets},'science_unchanged_from_v12':True}
    (temp/'RELEASE_CHECKSUMS.json').write_text(json.dumps(sums,indent=2)+'\n');assets.append(('RELEASE_CHECKSUMS.json',temp/'RELEASE_CHECKSUMS.json'))
    uploaded=[]
    for name,path in assets:
        b=path.read_bytes();mime='application/pdf' if name.endswith('.pdf') else 'application/json'
        u='https://uploads.github.com/repos/'+REPOSITORY+'/releases/'+str(rid)+'/assets?name='+name
        a=request('POST',u,token,data=b,content_type=mime)
        need(a['name']==name and a['size']==len(b) and a['state']=='uploaded','Asset upload validation failed')
        expected='sha256:'+hashlib.sha256(b).hexdigest()
        if a.get('digest'):need(a['digest']==expected,'Asset checksum differs')
        uploaded.append({'name':name,'bytes':len(b),'sha256':expected.split(':',1)[1],'url':a['browser_download_url']})
    record=request('PATCH',prefix+'/'+str(rid),token,payload={'draft':False,'prerelease':False,'make_latest':'true'})
    need(record['tag_name']==TAG and record['draft'] is False and record['published_at'],'Release not published')
    save('GITHUB_RELEASE_PUBLISHED',url=record['html_url'],published_at=record['published_at'],assets=uploaded,zenodo_ingestion_verified=False)
    print(receipt.read_text(),flush=True)
    if env.get('GITHUB_STEP_SUMMARY'):
        with open(env['GITHUB_STEP_SUMMARY'],'a') as f:f.write('Published '+record['html_url']+'\n\nSource: `'+sha+'`. Zenodo ingestion must be checked separately.\n')
if __name__=='__main__':main()
