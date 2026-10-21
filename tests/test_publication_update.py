import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from verify_publication_update import validate
class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.r=json.loads((ROOT/'provenance/availability_update_verification.json').read_text());self.a=json.loads((ROOT/'provenance/zenodo_release_receipt.json').read_text())
    def test_valid(self):validate(self.r,self.a)
    def test_bad_doi(self):
        self.r['doi']='10.5281/zenodo.1'
        with self.assertRaises(RuntimeError):validate(self.r,self.a)
    def test_science_change(self):
        self.r['numerical_inputs_results_tables_figures_or_scientific_prose_changed']=True
        with self.assertRaises(RuntimeError):validate(self.r,self.a)
    def test_tag_rewrite(self):
        self.r['tag_or_zenodo_archive_modified']=True
        with self.assertRaises(RuntimeError):validate(self.r,self.a)
    def test_extra_file(self):
        self.r['files'].append({'path':'analysis_data/changed.csv'})
        with self.assertRaises(RuntimeError):validate(self.r,self.a)
    def test_missing_archive_verification(self):
        self.a['status']='PENDING'
        with self.assertRaises(RuntimeError):validate(self.r,self.a)
    def test_unexpected_page(self):
        self.r['changed_main_pages']=[1,20]
        with self.assertRaises(RuntimeError):validate(self.r,self.a)
    def test_missing_visual_inspection(self):
        self.r['changed_page_visually_inspected']=False
        with self.assertRaises(RuntimeError):validate(self.r,self.a)

class ManuscriptDoiTests(unittest.TestCase):
    def setUp(self):
        from verify_publication_update import validate_manuscript_doi, restore_manuscript_source
        self.validate = validate_manuscript_doi
        self.restore = restore_manuscript_source
        self.m = json.loads((ROOT/'provenance/manuscript_doi_update_verification.json').read_text())
        self.a = json.loads((ROOT/'provenance/availability_update_verification.json').read_text())
        self.z = json.loads((ROOT/'provenance/zenodo_release_receipt.json').read_text())
        self.o = json.loads((ROOT/'provenance/archival_scientific_preservation.json').read_text())
    def check(self):self.validate(self.m, self.a, self.z, self.o)
    def test_valid_manuscript_amendment(self):self.check()
    def test_wrong_manuscript_doi(self):
        self.m['manuscript_doi'] = self.m['analysis_doi']
        with self.assertRaises(RuntimeError):self.check()
    def test_wrong_analysis_doi(self):
        self.m['analysis_doi'] = self.m['manuscript_doi']
        with self.assertRaises(RuntimeError):self.check()
    def test_no_publication_claim_from_reservation(self):
        self.m['publication_verified'] = True
        with self.assertRaises(RuntimeError):self.check()
    def test_no_changed_scientific_content(self):
        self.m['scientific_content_changed'] = True
        with self.assertRaises(RuntimeError):self.check()
    def test_no_archive_rewrite(self):
        self.m['tag_or_zenodo_archive_modified'] = True
        with self.assertRaises(RuntimeError):self.check()
    def test_no_extra_file(self):
        self.m['files'].append(dict(self.m['files'][0]))
        with self.assertRaises(RuntimeError):self.check()
    def test_wrong_predecessor_file(self):
        self.m['files'][0]['before_sha256'] = '0'*64
        with self.assertRaises(RuntimeError):self.check()
    def test_no_body_page_change(self):
        self.m['changed_main_pages'] = [1, 2]
        with self.assertRaises(RuntimeError):self.check()
    def test_inspection_required(self):
        self.m['changed_page_visually_inspected'] = False
        with self.assertRaises(RuntimeError):self.check()
    def test_supplement_preserved(self):
        self.m['supplementary_byte_identical'] = False
        with self.assertRaises(RuntimeError):self.check()
    def test_no_upload_claim(self):
        self.m['zenodo_manuscript_uploaded_or_published_by_this_operation'] = True
        with self.assertRaises(RuntimeError):self.check()
    def test_reverse_edit_exact_predecessor(self):
        import hashlib
        restored = self.restore((ROOT/'paper/manuscript/main.tex').read_text())
        e = next(e for e in self.m['files'] if e['path'] == 'paper/manuscript/main.tex')
        self.assertEqual(hashlib.sha256(restored.encode()).hexdigest(), e['before_sha256'])
    def test_wrong_header_rejected(self):
        text = (ROOT/'paper/manuscript/main.tex').read_text().replace('23530614','23530615')
        with self.assertRaises(RuntimeError):self.restore(text)
    def test_duplicate_header_rejected(self):
        from verify_publication_update import MANUSCRIPT_HEADER
        text = (ROOT/'paper/manuscript/main.tex').read_text() + MANUSCRIPT_HEADER
        with self.assertRaises(RuntimeError):self.restore(text)

if __name__=='__main__':unittest.main()
