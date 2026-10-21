import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from verify_archival_release import validate_metadata
from publish_archival_release import validate_environment
class ArchivalReleaseTests(unittest.TestCase):
    def setUp(self):
        self.m=json.loads((ROOT/'.zenodo.json').read_text());self.p=json.loads((ROOT/'docs/archival_release_plan.json').read_text())
        self.e={'GITHUB_ACTIONS':'true','GITHUB_REPOSITORY':'Atalebe/dm_mass_loss_accretion_history','GITHUB_EVENT_NAME':'push','GITHUB_REF':'refs/tags/v1.0.0','GITHUB_SHA':'a'*40,'GITHUB_TOKEN':'synthetic-test-token-not-a-credential'}
    def test_metadata_valid(self):validate_metadata(self.m,self.p)
    def test_wrong_version(self):
        self.m['version']='2.0.0'
        with self.assertRaises(RuntimeError):validate_metadata(self.m,self.p)
    def test_no_blanket_licence(self):
        self.m['license']='cc-by-4.0'
        with self.assertRaises(RuntimeError):validate_metadata(self.m,self.p)
    def test_no_invented_doi(self):
        self.m['doi']='10.5281/zenodo.0000'
        with self.assertRaises(RuntimeError):validate_metadata(self.m,self.p)
    def test_no_inferred_affiliation(self):
        self.m['creators'][0]['affiliation']='unverified'
        with self.assertRaises(RuntimeError):validate_metadata(self.m,self.p)
    def test_no_scientific_closure(self):
        self.p['scientific_findings_closed']=['ABA26-001']
        with self.assertRaises(RuntimeError):validate_metadata(self.m,self.p)
    def test_hosted_valid_fixture(self):validate_environment(self.e)
    def test_local_cannot_publish(self):
        self.e['GITHUB_ACTIONS']='false'
        with self.assertRaises(RuntimeError):validate_environment(self.e)
    def test_other_repository(self):
        self.e['GITHUB_REPOSITORY']='Atalebe/dark_matter_memory_sims'
        with self.assertRaises(RuntimeError):validate_environment(self.e)
    def test_wrong_tag(self):
        self.e['GITHUB_REF']='refs/tags/v2.0.0'
        with self.assertRaises(RuntimeError):validate_environment(self.e)
    def test_no_branch_publication(self):
        self.e['GITHUB_REF']='refs/heads/main'
        with self.assertRaises(RuntimeError):validate_environment(self.e)
    def test_no_pull_request_publication(self):
        self.e['GITHUB_EVENT_NAME']='pull_request'
        with self.assertRaises(RuntimeError):validate_environment(self.e)
    def test_no_missing_token(self):
        self.e.pop('GITHUB_TOKEN')
        with self.assertRaises(RuntimeError):validate_environment(self.e)
if __name__=='__main__':unittest.main()
