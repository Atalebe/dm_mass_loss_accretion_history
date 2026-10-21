"""Verify exact release payload and lossless-source identities; standard library only."""
from pathlib import Path
import gzip, hashlib, json, sys
ROOT = Path(__file__).resolve().parents[1]
def need(ok, message):
    if not ok:
        raise RuntimeError(message)
def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(4 << 20), b''):
            h.update(block)
    return h.hexdigest()
def payload(root):
    ignored = {'.git', '.venv', '__pycache__', '.cache', 'outputs'}
    result = []
    for p in root.rglob('*'):
        rel = p.relative_to(root)
        if any(x in ignored for x in rel.parts):
            continue
        need(not p.is_symlink(), 'Symlink forbidden: ' + str(rel))
        if p.is_file() and str(rel) != 'MANIFEST.json':
            result.append(str(rel))
    return sorted(result)
def verify(root=ROOT):
    root = Path(root)
    manifest = json.loads((root / 'MANIFEST.json').read_text())
    entries = manifest['files']
    names = [e['path'] for e in entries]
    need(len(names) == len(set(names)), 'Duplicate manifest path')
    need(sorted(names) == payload(root), 'Payload membership mismatch')
    for e in entries:
        p = root / e['path']
        need(p.resolve().is_relative_to(root.resolve()), 'Path escapes repository')
        need(p.stat().st_size == e['bytes'], 'Size mismatch: ' + e['path'])
        need(sha(p) == e['sha256'], 'Checksum mismatch: ' + e['path'])
    decoded = 0
    for e in json.loads((root/'provenance/source_map.json').read_text())['records']:
        p = root/e['path']
        need(sha(p) == e['sha256'], 'Scientific source identity: ' + e['path'])
        if e['representation'] == 'lossless-gzip':
            b = gzip.decompress(p.read_bytes())
            need(hashlib.sha256(b).hexdigest() == e['decoded_sha256'], 'Decoded identity: ' + e['path'])
            need(len(b) == e['decoded_bytes'], 'Decoded size: ' + e['path'])
            decoded += 1
    return {'status':'PAYLOAD_VERIFIED', 'files':len(entries), 'decoded_catalogues':decoded}
if __name__ == '__main__':
    try:
        print(json.dumps(verify(), indent=2))
    except Exception as exc:
        print('HOLD: ' + str(exc), file=sys.stderr)
        sys.exit(2)
