import json, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from verify_licensing import validate_map, classify

class LicensingTests(unittest.TestCase):
    def setUp(self):
        self.r = json.loads((ROOT/'docs/licensing.json').read_text())
    def test_valid_material_split(self): validate_map(self.r)
    def test_code_retains_mit(self): self.assertEqual(classify('src/core.py', self.r), 'MIT')
    def test_manuscript_cc(self): self.assertEqual(classify('paper/manuscript/main.tex', self.r), 'CC-BY-4.0_AUTHOR_RIGHTS_ONLY')
    def test_documentation_cc(self): self.assertEqual(classify('README.md', self.r), 'CC-BY-4.0_AUTHOR_RIGHTS_ONLY')
    def test_numerical_outputs_cc_for_author_rights(self): self.assertEqual(classify('analysis_data/result.npz', self.r), 'CC-BY-4.0_AUTHOR_RIGHTS_ONLY')
    def test_synthetic_dataset_cc(self): self.assertEqual(classify('data/reference.csv', self.r), 'CC-BY-4.0_AUTHOR_RIGHTS_ONLY')
    def test_figures_cc(self): self.assertEqual(classify(self.r['figure_files'][0], self.r), 'CC-BY-4.0_AUTHOR_RIGHTS_ONLY')
    def test_legal_notices_preserved(self): self.assertEqual(classify('LICENSES/MIT.txt', self.r), 'EXISTING_LEGAL_TEXT_TERMS')
    def test_blanket_rejected(self):
        self.r['whole_repository_licence'] = 'CC-BY-4.0'
        with self.assertRaises(RuntimeError): validate_map(self.r)
    def test_provider_relicensing_rejected(self):
        self.r['third_party_rights_relicensed'] = True
        with self.assertRaises(RuntimeError): validate_map(self.r)
    def test_missing_manuscript_grant_rejected(self):
        self.r['standalone_manuscript_documentation_licence'] = None
        with self.assertRaises(RuntimeError): validate_map(self.r)
    def test_missing_dataset_grant_rejected(self):
        self.r['standalone_datasets_licence'] = None
        with self.assertRaises(RuntimeError): validate_map(self.r)
    def test_wrong_code_licence_rejected(self):
        self.r['licences']['original_code']['spdx'] = 'CC-BY-4.0'
        with self.assertRaises(RuntimeError): validate_map(self.r)
    def test_default_scope_cannot_shrink_to_figures(self):
        self.r['licences']['other_author_owned_material']['scope_rule'] = 'FIGURES_ONLY'
        with self.assertRaises(RuntimeError): validate_map(self.r)
    def test_path_escape_rejected(self):
        with self.assertRaises(RuntimeError): classify('../outside.txt', self.r)
    def test_unmapped_code_rejected(self):
        with self.assertRaises(RuntimeError): classify('src/unknown.py', self.r)
    def test_release_claim_rejected(self):
        self.r['release_published_by_this_operation'] = True
        with self.assertRaises(RuntimeError): validate_map(self.r)
    def test_duplicate_code_rejected(self):
        self.r['licences']['original_code']['files'].append('src/core.py')
        with self.assertRaises(RuntimeError): validate_map(self.r)

if __name__ == '__main__': unittest.main()
