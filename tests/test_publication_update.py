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
if __name__=='__main__':unittest.main()
