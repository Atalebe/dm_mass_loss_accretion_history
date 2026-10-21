"""Verify the DOI-only availability amendment without changing the archived tag."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
ALLOWED={'paper/manuscript/availability.tex','paper/Mass_Loss_Accretion_History.pdf'}
def need(ok,msg):
    if not bool(ok):raise RuntimeError(msg)
def validate(record,archive):
    need(record['status']=='VERIFIED_DOI_ONLY_AVAILABILITY_UPDATE','Unverified publication edit')
    need({e['path'] for e in record['files']}==ALLOWED and len(record['files'])==2,'Unapproved publication file')
    need(record['doi']==archive['doi']=='10.5281/zenodo.23529740','Wrong archive DOI')
    need(record['archived_commit']==archive['commit']=='11da155816d72342ce162ecdd7e07d9f492ce072','Wrong archived source')
    need(archive['status']=='PUBLISHED_ARCHIVE_DOWNLOADED_AND_ALL_FILES_VERIFIED' and archive['payload_files_verified']==793,'Archive not verified')
    need(record['numerical_inputs_results_tables_figures_or_scientific_prose_changed'] is False,'Scientific edit not authorized')
    need(record['tag_or_zenodo_archive_modified'] is False,'Released source must remain immutable')
    need(record['changed_main_pages']==[20] and record['main_pages_before']==record['main_pages_after']==22,'Unexpected page changes')
    need(record['supplementary_byte_identical'] is True and record['changed_page_visually_inspected'] is True,'PDF inspection incomplete')
def verify(root=ROOT):
    root=Path(root);r=json.loads((root/'provenance/availability_update_verification.json').read_text());a=json.loads((root/'provenance/zenodo_release_receipt.json').read_text());validate(r,a)
    old={e['path']:e for e in json.loads((root/'provenance/archival_scientific_preservation.json').read_text())['files']}
    for e in r['files']:
        p=root/e['path'];need(old[e['path']]['sha256']==e['archived_sha256'],'Original identity changed')
        need(p.stat().st_size==e['current_bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==e['current_sha256'],'Publication file differs')
    need((root/'paper/manuscript/availability.tex').read_text()==r['availability_after'],'Availability wording differs')
    need('can be obtained from the author' not in r['availability_after'],'Obsolete availability claim')
    return {'status':'DOI_ONLY_PUBLICATION_UPDATE_VERIFIED','doi':a['doi'],'changed_files':2,'changed_rendered_pages':[20],'new_scientific_results':0}
if __name__=='__main__':print(json.dumps(verify(),indent=2))
