"""Verify publication-only amendments without changing the archived tag."""
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

MANUSCRIPT_DOI = '10.5281/zenodo.23530614'
MANUSCRIPT_ALLOWED = {'paper/manuscript/main.tex', 'paper/Mass_Loss_Accretion_History.pdf'}
MANUSCRIPT_HEADER = '% Author-reserved manuscript DOI; distinct from the analysis archive DOI.\n\\fancypagestyle{manuscriptdoi}{%\n\\fancyhf{}%\n\\fancyhead[L]{\\footnotesize Manuscript DOI: \\href{https://doi.org/10.5281/zenodo.23530614}{\\nolinkurl{10.5281/zenodo.23530614}}}%\n\\fancyfoot[C]{\\thepage}%\n\\renewcommand{\\headrulewidth}{0pt}}\n\\hypersetup{pdfkeywords={Manuscript DOI: 10.5281/zenodo.23530614}}\n'
MANUSCRIPT_STYLE = '\\thispagestyle{manuscriptdoi}\n'

def restore_manuscript_source(text):
    need(text.count(MANUSCRIPT_HEADER) == 1, 'Missing or changed manuscript DOI header')
    need(text.count(MANUSCRIPT_STYLE) == 1, 'Missing or changed title-page style')
    need(MANUSCRIPT_HEADER + chr(92) + 'begin{document}' + chr(10) in text, 'Header insertion moved')
    need(chr(92) + 'maketitle' + chr(10) + MANUSCRIPT_STYLE in text, 'Title style insertion moved')
    return text.replace(MANUSCRIPT_HEADER, '', 1).replace(MANUSCRIPT_STYLE, '', 1)

def validate_manuscript_doi(record, availability, archive, original):
    validate(availability, archive)
    need(record['schema'] == 'halo-manuscript-doi-update-v1' and record['status'] == 'MANUSCRIPT_DOI_INSERTION_VERIFIED', 'Unverified manuscript amendment')
    need(record['manuscript_doi'] == MANUSCRIPT_DOI, 'Wrong manuscript DOI')
    need(record['analysis_doi'] == archive['doi'] and record['analysis_doi'] != record['manuscript_doi'], 'Article/archive DOI confusion')
    need(record['doi_status'] == 'OWNER_REPORTED_RESERVED_PUBLICATION_NOT_VERIFIED' and record['publication_verified'] is False, 'Publication not established by reservation')
    need(record['base_commit'] == '69a7797cb528bb13ba57b50500786ff79eb76054' and record['archived_commit'] == archive['commit'], 'Wrong amendment predecessor')
    need(len(record['files']) == 2 and {e['path'] for e in record['files']} == MANUSCRIPT_ALLOWED, 'Unapproved manuscript file')
    previous = {e['path']:e for e in availability['files']}
    old = {e['path']:e for e in original['files']}
    for e in record['files']:
        p = e['path']
        before_sha = previous[p]['current_sha256'] if p in previous else old[p]['sha256']
        before_bytes = previous[p]['current_bytes'] if p in previous else old[p]['bytes']
        need(e['before_sha256'] == before_sha and e['before_bytes'] == before_bytes, 'Amendment predecessor identity differs')
        need(isinstance(e['current_bytes'], int) and e['current_bytes'] > 0, 'Invalid amended file size')
        need(len(e['current_sha256']) == 64 and all(c in '0123456789abcdef' for c in e['current_sha256']), 'Invalid amended file checksum')
    need(record['changed_main_pages'] == [1] and record['main_pages_before'] == record['main_pages_after'] == 22, 'Unexpected manuscript page changes')
    for key in ['all_other_main_pages_pixel_identical', 'first_page_scientific_text_unchanged', 'supplementary_byte_identical', 'changed_page_visually_inspected', 'analysis_availability_unchanged']:
        need(record[key] is True, 'Required document check missing: ' + key)
    for key in ['scientific_content_changed', 'tag_or_zenodo_archive_modified', 'new_release_created', 'zenodo_manuscript_uploaded_or_published_by_this_operation']:
        need(record[key] is False, 'Amendment exceeds authorization: ' + key)
    need(record['rendered_manuscript_doi_link'] == 'https://doi.org/' + MANUSCRIPT_DOI, 'Wrong rendered DOI link')
    need(record['pdf_keywords'] == 'Manuscript DOI: ' + MANUSCRIPT_DOI, 'Wrong PDF DOI metadata')

def verify_manuscript_doi(root=ROOT):
    root = Path(root)
    record = json.loads((root/'provenance/manuscript_doi_update_verification.json').read_text())
    availability = json.loads((root/'provenance/availability_update_verification.json').read_text())
    archive = json.loads((root/'provenance/zenodo_release_receipt.json').read_text())
    original = json.loads((root/'provenance/archival_scientific_preservation.json').read_text())
    validate_manuscript_doi(record, availability, archive, original)
    for e in record['files']:
        p = root/e['path']
        need(p.is_file() and not p.is_symlink() and p.stat().st_size == e['current_bytes'] and hashlib.sha256(p.read_bytes()).hexdigest() == e['current_sha256'], 'Amended manuscript identity differs')
    source = restore_manuscript_source((root/'paper/manuscript/main.tex').read_text())
    source_before = next(e for e in record['files'] if e['path'] == 'paper/manuscript/main.tex')
    need(hashlib.sha256(source.encode()).hexdigest() == source_before['before_sha256'], 'Non-bibliographic manuscript edit detected')
    need((root/'paper/manuscript/availability.tex').read_text() == availability['availability_after'], 'Analysis availability changed')
    old = {e['path']:e for e in original['files']}
    p = root/'paper/Supplementary_Material.pdf'
    need(hashlib.sha256(p.read_bytes()).hexdigest() == old['paper/Supplementary_Material.pdf']['sha256'], 'Supplement changed')
    need('doi: "' + archive['doi'] + '"' in (root/'CITATION.cff').read_text(), 'Software DOI changed')
    return {'status':'MANUSCRIPT_DOI_INSERTION_VERIFIED', 'manuscript_doi':MANUSCRIPT_DOI, 'publication_verified':False, 'changed_pages':[1]}

def verify(root=ROOT):
    root=Path(root);r=json.loads((root/'provenance/availability_update_verification.json').read_text());a=json.loads((root/'provenance/zenodo_release_receipt.json').read_text());validate(r,a)
    old={e['path']:e for e in json.loads((root/'provenance/archival_scientific_preservation.json').read_text())['files']}
    amendment = {}
    if (root/'provenance/manuscript_doi_update_verification.json').exists():
        verify_manuscript_doi(root)
        amendment = {e['path']:e for e in json.loads((root/'provenance/manuscript_doi_update_verification.json').read_text())['files']}
    for e in r['files']:
        p=root/e['path'];need(old[e['path']]['sha256']==e['archived_sha256'],'Original identity changed')
        current = amendment.get(e['path'], e)
        need(p.stat().st_size==current['current_bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==current['current_sha256'],'Publication file differs')
    need((root/'paper/manuscript/availability.tex').read_text()==r['availability_after'],'Availability wording differs')
    need('can be obtained from the author' not in r['availability_after'],'Obsolete availability claim')
    return {'status':'DOI_ONLY_PUBLICATION_UPDATE_VERIFIED','analysis_archive_doi':a['doi'],
        'availability_changed_pages':[20],
        'subsequent_manuscript_doi':MANUSCRIPT_DOI if amendment else None,
        'subsequent_manuscript_changed_pages':[1] if amendment else [],
        'changed_rendered_pages_since_archived_v1':[1,20] if amendment else [20],
        'new_scientific_results':0}
if __name__=='__main__':print(json.dumps(verify(),indent=2))
