import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from verify_release_coverage import validate_findings
class CoverageTests(unittest.TestCase):
 def setUp(self):self.r=json.loads((ROOT/'docs/audit_continuity/ABA0001_followup.json').read_text())
 def test_valid_scoped_status(self):validate_findings(self.r)
 def test_scientific_closed_rejected(self):
  self.r['findings'][0]['scientific_acceptance_status']='CLOSED'
  with self.assertRaises(RuntimeError):validate_findings(self.r)
 def test_population_claim_rejected(self):
  self.r['findings'][1]['missing_epochs_recovered']=True
  with self.assertRaises(RuntimeError):validate_findings(self.r)
 def test_joint_calibration_rejected(self):
  self.r['findings'][0]['joint_calibration_established']=True
  with self.assertRaises(RuntimeError):validate_findings(self.r)
 def test_other_branch_rejected(self):
  self.r['findings'].append({'id':'ABA26-003'})
  with self.assertRaises(RuntimeError):validate_findings(self.r)
 def test_authority_upgrade_rejected(self):
  self.r['new_scientific_authorization']=True
  with self.assertRaises(RuntimeError):validate_findings(self.r)
 def test_severity_change_rejected(self):
  self.r['findings'][0]['severity']='MINOR'
  with self.assertRaises(RuntimeError):validate_findings(self.r)
 def test_v176_rejected(self):
  self.r['v176_started']=True
  with self.assertRaises(RuntimeError):validate_findings(self.r)
if __name__=='__main__':unittest.main()
