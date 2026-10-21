import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from verify_legacy_import import validate_record
class ImportTests(unittest.TestCase):
 def setUp(self):self.r=json.loads((ROOT/'provenance/legacy_import_verification.json').read_text())
 def test_valid(self):validate_record(self.r)
 def test_archive(self):
  self.r['archive_sha256']='0'*64
  with self.assertRaises(RuntimeError):validate_record(self.r)
 def test_incomplete_minima(self):
  self.r['counts']['crosscheck_minima']=359999
  with self.assertRaises(RuntimeError):validate_record(self.r)
 def test_overwrite(self):
  self.r['overwritten_existing_paths']=1
  with self.assertRaises(RuntimeError):validate_record(self.r)
 def test_changed_payload(self):
  self.r['all_companion_bytes_preserved']=False
  with self.assertRaises(RuntimeError):validate_record(self.r)
 def test_fresh_stream(self):
  self.r['new_random_streams']=1
  with self.assertRaises(RuntimeError):validate_record(self.r)
 def test_false_closure(self):
  self.r['scientific_findings_closed']=['ABA26-001']
  with self.assertRaises(RuntimeError):validate_record(self.r)
 def test_partial_replay(self):
  self.r['full_saved_null_replay']=False
  with self.assertRaises(RuntimeError):validate_record(self.r)
if __name__=='__main__':unittest.main()
