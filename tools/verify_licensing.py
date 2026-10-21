"""Verify MIT software and CC BY 4.0 non-code author contributions; no scientific run."""
from pathlib import Path, PurePosixPath
import json, hashlib
from verify_integrity import payload
ROOT = Path(__file__).resolve().parents[1]

def need(ok, message):
    if not bool(ok):
        raise RuntimeError(message)

def safe_relative(name):
    q = PurePosixPath(name)
    need(bool(name) and not q.is_absolute() and '..' not in q.parts and '\\' not in name, 'Unsafe licence path')
    need(str(q) == name, 'Noncanonical licence path')
    return q

def validate_map(r):
    need(r['schema'] == 'halo-material-licensing-v2', 'Wrong licence schema')
    need(r['licensor'] == 'Stephen Atalebe', 'Wrong licensor')
    need(set(r['licences']) == {'original_code', 'other_author_owned_material'}, 'Wrong material split')
    code = r['licences']['original_code']
    other = r['licences']['other_author_owned_material']
    need(code['spdx'] == 'MIT' and code['text'] == 'LICENSES/MIT.txt', 'Code must retain MIT')
    need(other['spdx'] == 'CC-BY-4.0' and other['text'] == 'LICENSES/CC-BY-4.0.txt', 'Non-code must use CC BY 4.0')
    need(other['scope_rule'] == 'ALL_NON_CODE_AUTHOR_OWNED_MATERIAL', 'Non-code scope incorrectly narrowed')
    need(r['non_code_default'] == 'CC-BY-4.0', 'Non-code default missing')
    need(r['whole_repository_licence'] is None, 'One blanket licence would obscure the code exception')
    need(r['third_party_rights_relicensed'] is False and r['grant_limited_to_licensor_rights'] is True, 'Third-party rights must be preserved')
    need(r['licence_texts_retain_existing_terms'] is True, 'Legal notice terms must be preserved')
    need(r['standalone_manuscript_documentation_licence'] == 'CC-BY-4.0', 'Manuscript/documentation grant missing')
    need(r['standalone_datasets_licence'] == 'CC-BY-4.0', 'Author dataset grant missing')
    names = code['files']
    need(len(names) == len(set(names)), 'Duplicate code path')
    for name in names:
        q = safe_relative(name)
        need(q.suffix in ('.py', '.sh'), 'Non-code listed as MIT software')
        need(q.parts[0] in ['src', 'tools', 'tests', 'reference'] or (len(q.parts) == 1 and q.suffix == '.sh'), 'Unexpected code scope')
    figures = r['figure_files']
    need(len(figures) == len(set(figures)) == 24 and len({Path(p).stem for p in figures}) == 8, 'Figure set changed')
    for name in figures:
        q = safe_relative(name)
        need(q.parts[:2] == ('paper', 'figures') and q.suffix in ('.pdf', '.png', '.svg'), 'Unexpected figure path')
    need({e['path'] for e in r['legal_texts']} == {'LICENSES/MIT.txt', 'LICENSES/CC-BY-4.0.txt'}, 'Legal text set differs')
    need(len(r['legal_texts']) == 2, 'Duplicate legal text')
    need({e['path'] for e in r['figure_identities']} == set(figures) and len(r['figure_identities']) == 24, 'Figure identities incomplete')
    need(r['release_published_by_this_operation'] is False, 'Release publication is outside this change')

def classify(name, r):
    q = safe_relative(name)
    if name in {e['path'] for e in r['legal_texts']}:
        return 'EXISTING_LEGAL_TEXT_TERMS'
    if name in r['licences']['original_code']['files']:
        return 'MIT'
    need(q.suffix not in ('.py', '.sh', '.js', '.ts', '.r', '.R', '.c', '.cpp', '.f', '.f90'), 'Unmapped software file')
    return 'CC-BY-4.0_AUTHOR_RIGHTS_ONLY'

def verify(root=ROOT):
    root = Path(root)
    r = json.loads((root/'docs/licensing.json').read_text())
    validate_map(r)
    names = payload(root) + ['MANIFEST.json']
    actual_code = sorted(n for n in names if Path(n).suffix in ('.py', '.sh'))
    need(actual_code == sorted(r['licences']['original_code']['files']), 'Update code membership before licensing new scripts')
    figures = sorted(str(p.relative_to(root)) for p in (root/'paper/figures').iterdir() if p.suffix in ('.pdf', '.png', '.svg'))
    need(figures == sorted(r['figure_files']), 'Figure membership differs')
    counts = {'MIT': 0, 'CC-BY-4.0_AUTHOR_RIGHTS_ONLY': 0, 'EXISTING_LEGAL_TEXT_TERMS': 0}
    for name in names:
        p = root/name
        need(p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(root.resolve()), 'Missing or unsafe material')
        counts[classify(name, r)] += 1
    for e in r['figure_identities'] + r['legal_texts']:
        need(hashlib.sha256((root/e['path']).read_bytes()).hexdigest() == e['sha256'], 'Preserved figure or licence text changed: '+e['path'])
    status = json.loads((root/'docs/release_status.json').read_text())
    need(status['licences'] == {'original_code': 'MIT', 'other_author_owned_material': 'CC-BY-4.0'}, 'Release licence scope differs')
    need(status['licence_selection_complete_for_entire_package'] is True, 'Author licence choice must be recorded as complete')
    need(status['third_party_redistribution_review_complete'] is False, 'Licensing does not itself clear upstream redistribution')
    need(status['github_release_created'] is False and status['archive_doi'] is None, 'Unapproved archival-release claim')
    notice = (root/'LICENSE.md').read_text().lower()
    for phrase in ['all other author-owned material', 'manuscript', 'datasets', 'underlying third-party content is not relicensed']:
        need(phrase in notice, 'Missing material-scope notice: '+phrase)
    return {'status': 'CODE_MIT_NONCODE_CC_BY_4_0_VERIFIED', 'material_counts': counts,
            'original_figures': 8, 'figure_representations': 24, 'author_licence_selection_complete': True,
            'third_party_rights_relicensed': False, 'new_fits': 0, 'new_permutations': 0,
            'release_published': False}

if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
