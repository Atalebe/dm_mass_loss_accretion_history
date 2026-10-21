import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from verify_licensing import validate_map
class LicensingTests(unittest.TestCase):
    def setUp(self):self.r=json.loads((ROOT/'docs/licensing.json').read_text())
    def test_valid_scopes(self):validate_map(self.r)
    def test_blanket_rejected(self):
        self.r['whole_repository_licence']='CC-BY-4.0'
        with self.assertRaises(RuntimeError):validate_map(self.r)
    def test_relicensed_provider_data_rejected(self):
        self.r['third_party_rights_relicensed']=True
        with self.assertRaises(RuntimeError):validate_map(self.r)
    def test_documentation_expansion_rejected(self):
        self.r['standalone_manuscript_documentation_licence']='CC-BY-4.0'
        with self.assertRaises(RuntimeError):validate_map(self.r)
    def test_dataset_expansion_rejected(self):
        self.r['standalone_datasets_licence']='CC-BY-4.0'
        with self.assertRaises(RuntimeError):validate_map(self.r)
    def test_source_wrong_licence_rejected(self):
        self.r['licences']['original_code']['spdx']='CC-BY-4.0'
        with self.assertRaises(RuntimeError):validate_map(self.r)
    def test_path_escape_rejected(self):
        self.r['licences']['original_code']['files'].append('../outside.py')
        with self.assertRaises(RuntimeError):validate_map(self.r)
    def test_release_claim_rejected(self):
        self.r['release_published_by_this_operation']=True
        with self.assertRaises(RuntimeError):validate_map(self.r)
if __name__=='__main__':unittest.main()
