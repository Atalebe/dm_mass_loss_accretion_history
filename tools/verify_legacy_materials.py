"""Standard-library integrity check for the curated legacy material extension."""
from pathlib import Path
import json,hashlib,sys
ROOT=Path(__file__).resolve().parents[1]
def verify(root=ROOT):
    root=Path(root);rows=json.loads((root/'provenance/legacy_payload_manifest.json').read_text())['files']
    names=[x['path'] for x in rows]
    if len(names)!=len(set(names)):raise RuntimeError('Duplicate extension path')
    for e in rows:
        p=root/e['path']
        if not p.resolve().is_relative_to(root.resolve()) or p.is_symlink():raise RuntimeError('Unsafe extension path')
        if not p.is_file() or p.stat().st_size!=e['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=e['sha256']:raise RuntimeError('Legacy extension changed: '+e['path'])
    return {'status':'LEGACY_MATERIALS_VERIFIED','files':len(rows),'new_fits':0,'new_permutations':0}
if __name__=='__main__':
    try:print(json.dumps(verify(),indent=2))
    except Exception as e:print('HOLD: '+str(e),file=sys.stderr);sys.exit(2)
