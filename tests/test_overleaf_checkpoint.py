import io,sys,unittest,zipfile,json,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from verify_overleaf_checkpoint import zip_payload,verify,CP
class OverleafCheckpointTests(unittest.TestCase):
 def z(self,names):
  b=io.BytesIO()
  with zipfile.ZipFile(b,'w') as z:
   for n in names:z.writestr(n,b'test')
  return b.getvalue()
 def test_valid_zip(self):self.assertEqual(zip_payload(self.z(['main.tex'])),{'main.tex':b'test'})
 def test_parent_path(self):
  with self.assertRaises(RuntimeError):zip_payload(self.z(['../escape']))
 def test_absolute_path(self):
  with self.assertRaises(RuntimeError):zip_payload(self.z(['/escape']))
 def test_backslash_path(self):
  with self.assertRaises(RuntimeError):zip_payload(self.z(['folder\\escape']))
 def test_duplicate(self):
  with self.assertRaises(RuntimeError):zip_payload(self.z(['main.tex','main.tex']))
 def test_complete_frozen_checkpoint(self):self.assertEqual(verify(ROOT)['canonical_paper_files'],101)
 def test_wrong_doi(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/CP;p.mkdir(parents=True);r=json.loads((ROOT/CP/'CHECKPOINT_VERIFICATION.json').read_text());r['manuscript_doi']=r['analysis_doi'];(p/'CHECKPOINT_VERIFICATION.json').write_text(json.dumps(r))
   with self.assertRaises(RuntimeError):verify(Path(td))
 def test_no_scientific_promotion(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/CP;p.mkdir(parents=True);r=json.loads((ROOT/CP/'CHECKPOINT_VERIFICATION.json').read_text());r['v176_started']=True;(p/'CHECKPOINT_VERIFICATION.json').write_text(json.dumps(r))
   with self.assertRaises(RuntimeError):verify(Path(td))
if __name__=='__main__':unittest.main()
