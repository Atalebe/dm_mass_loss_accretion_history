"""Verify material-scoped licensing without refitting any scientific model."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def need(x,message):
    if not bool(x):raise RuntimeError(message)
def validate_map(r):
    need(r['schema']=='halo-scoped-licensing-v1','Wrong licence map')
    need(r['licensor']=='Stephen Atalebe','Wrong licensor')
    need(r['licences']['original_code']['spdx']=='MIT','Code licence differs from approval')
    need(r['licences']['original_figures']['spdx']=='CC-BY-4.0','Figure licence differs from approval')
    need(r['whole_repository_licence'] is None,'Blanket licence not authorized')
    need(r['third_party_rights_relicensed'] is False,'Third-party relicensing not authorized')
    need(r['standalone_manuscript_documentation_licence'] is None,'Standalone prose licence not authorized')
    need(r['standalone_datasets_licence'] is None,'Standalone dataset licence not authorized')
    code=r['licences']['original_code']['files'];figs=r['licences']['original_figures']['files']
    need(len(code)==len(set(code)) and len(figs)==len(set(figs)),'Duplicate licence path')
    need(not set(code)&set(figs),'Ambiguous alternative licensing')
    for p in code:
        q=Path(p)
        need(not q.is_absolute() and '..' not in q.parts,'Unsafe code path')
        need(q.suffix in ('.py','.sh'),'Non-code path assigned MIT')
        need(q.parts[0] in ['src','tools','tests','reference'] or (len(q.parts)==1 and q.suffix=='.sh'),'Unexpected code scope')
    for p in figs:
        q=Path(p)
        need(not q.is_absolute() and '..' not in q.parts,'Unsafe figure path')
        need(q.parts[:2]==('paper','figures') and q.suffix in ('.pdf','.png','.svg'),'Non-figure assigned CC BY')
    need(len(figs)==24 and len({Path(p).stem for p in figs})==8,'Expected eight figures in three formats')
    need(r['release_published_by_this_operation'] is False,'Release publication outside scope')

def verify(root=ROOT):
    root=Path(root);r=json.loads((root/'docs/licensing.json').read_text());validate_map(r)
    for group in r['licences'].values():
        for rel in group['files']:
            p=root/rel
            need(p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(root.resolve()),'Missing/unsafe licensed file:'+rel)
    seen=sorted(str(p.relative_to(root)) for d in ['src','tools','tests','reference'] for p in (root/d).rglob('*.py'))+sorted(p.name for p in root.glob('*.sh'))
    need(sorted(seen)==sorted(r['licences']['original_code']['files']),'Source membership differs; update explicit licence map')
    figures=sorted(str(p.relative_to(root)) for p in (root/'paper/figures').iterdir() if p.suffix in ('.pdf','.png','.svg'))
    need(figures==sorted(r['licences']['original_figures']['files']),'Figure membership differs')
    for e in r['figure_identities']:
        need(hashlib.sha256((root/e['path']).read_bytes()).hexdigest()==e['sha256'],'Figure altered:'+e['path'])
    for e in r['legal_texts']:
        need(hashlib.sha256((root/e['path']).read_bytes()).hexdigest()==e['sha256'],'Legal text differs')
    status=json.loads((root/'docs/release_status.json').read_text())
    need(status['licences']=={'original_code':'MIT','original_figures':'CC-BY-4.0'},'Release scope inconsistent')
    need(status['licence_selection_complete_for_entire_package'] is False,'Whole package falsely declared licensed')
    need(status['github_release_created'] is False and status['archive_doi'] is None,'Release status inconsistent with this snapshot')
    notice=(root/'LICENSE.md').read_text()
    need('not licensed wholesale' in notice and 'standalone documentation' in notice,'Scope notice missing')
    return {'status':'SCOPED_LICENSING_VERIFIED','original_code_files':len(seen),'original_figures':8,'figure_files':24,
            'code_spdx':'MIT','figure_spdx':'CC-BY-4.0','whole_repository_licence':None,
            'manuscript_figures_and_data_bytes_changed':False,'new_fits':0,'new_permutations':0,'release_published':False}
if __name__=='__main__':print(json.dumps(verify(),indent=2))
