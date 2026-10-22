"""Authenticate the document checkpoint only; no simulation or typesetting execution."""
from pathlib import Path, PurePosixPath
import hashlib, io, json, stat, zipfile
ROOT=Path(__file__).resolve().parents[1]
CP='checkpoints/manuscript_pre_v176_20261022'

def need(ok,message):
    if not bool(ok):raise RuntimeError(message)
def sha(b):return hashlib.sha256(b).hexdigest()
def zip_payload(blob):
    out={}
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        need(z.testzip() is None,'ZIP CRC mismatch')
        need(sum(i.file_size for i in z.infolist())<25*1024**2,'Unexpected document archive size')
        for i in z.infolist():
            q=PurePosixPath(i.filename)
            need(not q.is_absolute() and '..' not in q.parts and '\\' not in i.filename,'Unsafe ZIP path')
            need(not stat.S_ISLNK(i.external_attr>>16),'ZIP symlink forbidden')
            if i.is_dir():continue
            need(str(q)==i.filename and i.filename not in out,'Noncanonical/duplicate ZIP path')
            out[i.filename]=z.read(i)
    return out

def verify(root=ROOT):
    root=Path(root);folder=root/CP;r=json.loads((folder/'CHECKPOINT_VERIFICATION.json').read_text())
    need(r['status']=='DOCUMENT_CHECKPOINT_VERIFIED','Checkpoint not verified')
    need(r['source_commit']=='c46f207dad827ad44d4af2aa8958b6dba81a76dd','Wrong source checkpoint')
    need(r['manuscript_doi']=='10.5281/zenodo.23530614' and r['analysis_doi']=='10.5281/zenodo.23529740','DOI roles changed')
    need(r['v176_started'] is False and r['scientific_findings_closed']==[],'Scientific authority upgraded')
    need(r['public_paper_modified'] is False and r['new_release_or_tag_created'] is False,'Unexpected publication mutation')
    blobs={}
    for e in r['bundles']:
        name=e['filename'];need(PurePosixPath(name).name==name,'Unsafe bundle name');b=(folder/name).read_bytes()
        need(len(b)==e['bytes'] and sha(b)==e['sha256'],'Bundle hash/length mismatch')
        blobs[name]=b
    project=zip_payload(blobs['DM_Overleaf_Compilation_20261022.zip'])
    freeze=zip_payload(blobs['DM_Manuscript_Checkpoint_Pre_v176_20261022.zip'])
    manifest=json.loads(freeze['MANIFEST.json'])['files']
    need(set(e['path'] for e in manifest)==set(freeze)-{'MANIFEST.json'},'Checkpoint payload membership')
    for e in manifest:need(len(freeze[e['path']])==e['bytes'] and sha(freeze[e['path']])==e['sha256'],'Checkpoint inner checksum')
    need(freeze['DM_Overleaf_Compilation_20261022.zip']==blobs['DM_Overleaf_Compilation_20261022.zip'],'Nested project differs')
    paper=json.loads(freeze['verification/SOURCE_PAPER_MANIFEST.json'])['files']
    need(len(paper)==101,'Canonical paper membership count')
    for e in paper:need(sha(freeze['canonical_paper/'+e['path']])==e['sha256'],'Canonical paper file changed')
    source_map=json.loads(project['SOURCE_MAP.json'])
    need(len(project)==45 and len(source_map['files'])==36,'Project membership count')
    for e in source_map['files']:
        original=freeze['canonical_paper/'+e['repository_path'].removeprefix('paper/')]
        adapted=project[e['bundle_path']]
        need(sha(original)==e['source_sha256'] and sha(adapted)==e['bundle_sha256'],'Source map checksum')
        if e['transformation']=='graphicspath_only':
            need(adapted.replace(rb'\graphicspath{{figures/}}',rb'\graphicspath{{../figures/}}')==original,'Non-path TeX edit')
        else:need(adapted==original,'Byte-preservation failure')
    for line in project['SHA256SUMS.txt'].decode().splitlines():
        digest,name=line.split('  ',1);need(sha(project[name])==digest,'Overleaf inner checksum')
    need('main.tex' in project and 'supplementary.tex' in project,'Missing root documents')
    need(not any(n.endswith(('.ttf','.otf','.woff','.woff2')) for n in freeze),'Font file must not be distributed')
    need(r['build_verification']['same_engine_clean_rebuild_byte_identical'] is True,'Build not verified')
    need(r['build_verification']['visual_inspection_pending'] is False,'Visual inspection pending')
    return {'status':'OVERLEAF_AND_PRESERVATION_CHECKPOINT_VERIFIED','canonical_paper_files':101,'overleaf_project_files':45,'main_pages':22,'supplement_pages':11,'new_scientific_experiments':0,'v176_started':False}
if __name__=='__main__':print(json.dumps(verify(),indent=2))
