"""Offline, standard-library gates for the explicitly authorized archival snapshot."""
from pathlib import Path
import json, hashlib
from verify_integrity import ROOT, verify as integrity
from verify_release_coverage import verify as coverage
from verify_legacy_import import verify as imported
from verify_licensing import verify as licensing

REPOSITORY = 'Atalebe/dm_mass_loss_accretion_history'
TAG = 'v1.0.0'
VERSION = '1.0.0'
def need(ok, message):
    if not bool(ok):
        raise RuntimeError(message)
def validate_metadata(m, plan):
    need(m['upload_type']=='software' and m['access_right']=='open', 'Unexpected record type/access')
    need(m['version']==VERSION and plan['tag']==TAG and plan['version']==VERSION, 'Release version mismatch')
    need(plan['repository']==REPOSITORY and plan['github_release_creation_authorized'] is True, 'Missing release authority')
    need(plan['scientific_changes_authorized'] is False and plan['scientific_findings_closed']==[], 'Scientific scope upgraded')
    need(m['creators']==[{'name':'Atalebe, Stephen'}], 'Unverified author metadata')
    need(m['license']=='other-open', 'Mixed material must not be assigned one blanket licence')
    for term in ['MIT','CC BY 4.0','distinct materials','third-party','LICENSE.md']:
        need(term in m['description'], 'Missing licence scope: '+term)
    need(not any(k in m for k in ['doi','prereserve_doi','grants']), 'Unverified identifier/funding')
    need('1.0.0' == plan['version'], 'Unknown release')
def verify(root=ROOT):
    root=Path(root); checks=integrity(root); cov=coverage(root); legacy=imported(root); lic=licensing(root)
    m=json.loads((root/'.zenodo.json').read_text());plan=json.loads((root/'docs/archival_release_plan.json').read_text());validate_metadata(m,plan)
    old=json.loads((root/'provenance/archival_scientific_preservation.json').read_text())
    for e in old['files']:
        p=root/e['path']
        need(p.is_file() and p.stat().st_size==e['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==e['sha256'], 'Scientific payload altered: '+e['path'])
    cff=(root/'CITATION.cff').read_text()
    need('version: "1.0.0"' in cff and 'family-names: "Atalebe"' in cff and 'MIT' in cff and 'CC-BY-4.0' in cff,'Citation metadata mismatch')
    policy=json.loads((root/'provenance/upstream_distribution_review.json').read_text())
    need(policy['author_rights_only'] is True and policy['provider_rights_relicensed'] is False, 'Unsupported upstream relicensing')
    need(policy['raw_hdf5_or_raw_tree_files_included'] is False, 'Raw provider archive not in scope')
    state=json.loads((root/'docs/release_status.json').read_text())
    need(state['explicit_reproduction_scope_approved'] is True, 'Reproduction scope not approved')
    need(state['scientific_findings_open']==['ABA26-001','ABA26-002'] and state['v176_started'] is False,'Scientific boundary differs')
    wf=(root/'.github/workflows/publish-v1.yml').read_text()
    need("'v1.0.0'" in wf and 'contents: write' in wf and 'pull_request' not in wf,'Unsafe workflow trigger')
    need('uses:' not in wf, 'Unexpected third-party action')
    return {'status':'ARCHIVAL_SNAPSHOT_VERIFIED','tag':TAG,'version':VERSION,'files':checks['files'],
        'scientific_files_unchanged':len(old['files']),'coverage_assets':cov['assets'],
        'licences':{'original_code':'MIT','other_author_owned_material':'CC-BY-4.0'},
        'new_scientific_computations':0,'scientific_findings_closed':[],'release_publication_authorized':True,
        'zenodo_doi_assumed':False}
if __name__=='__main__':
    print(json.dumps(verify(),indent=2))
