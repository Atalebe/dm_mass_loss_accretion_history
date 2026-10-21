import unittest,sys,math
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src/legacy'))
import supp_core as s
import original_functions as original
import spline_crosscheck as other
class LegacyTests(unittest.TestCase):
 def fixture(self):
  r=np.random.default_rng(414);n=80;d=pd.DataFrame({'x':r.normal(size=n),'z':r.normal(size=n),'k':r.normal(size=n)})
  d['y']=.3*d.x-.2*d.k+r.normal(size=n);return d
 def test_original_observed(self):
  d=self.fixture();a=s.Model.from_frame(d,'y',['x','z'],['k']).observed();b=original.fit_increment(d,'y','k',['x','z'])
  np.testing.assert_allclose(a['delta_bic'][0],b['delta_bic_memory_vs_controls'],atol=1e-8)
 def test_identity_shuffle(self):
  d=self.fixture();m=s.Model.from_frame(d,'y',['x','z'],['k'])
  for k,v in m.observed().items():np.testing.assert_allclose(v,m.permuted(np.arange(len(d)))[k],atol=1e-9)
 def test_empty_grid(self):
  with self.assertRaises(s.AuditError):s.check_grid([])
 def test_duplicate_grid(self):
  with self.assertRaises(s.AuditError):s.check_grid([1.,1.])
 def test_bad_gamma(self):
  with self.assertRaises(s.AuditError):s.check_grid([-.2])
 def test_nonfinite_grid(self):
  with self.assertRaises(s.AuditError):s.check_grid([float('nan')])
 def test_bad_shuffle(self):
  d=self.fixture();m=s.Model.from_frame(d,'y',['x','z'],['k'])
  with self.assertRaises(s.AuditError):m.permuted(np.zeros(len(d),int))
 def test_degenerate_history(self):
  d=self.fixture();d['k']=d.x
  with self.assertRaises(s.AuditError):s.Model.from_frame(d,'y',['x','z'],['k'])
 def test_add_one_count(self):self.assertEqual(s.empirical_p(np.array([0.,1.,2.]),-1.)['p'],.25)
 def test_original_grid(self):self.assertEqual(len(other.GRID),26);self.assertEqual(other.GRID[0],.2);self.assertEqual(other.GRID[-1],20.)
 def test_spline_functions_finite(self):
  x=np.linspace(0,1,51);r=other.rcs(x,np.array([.05,.35,.65,.95]))
  self.assertTrue(all(np.isfinite(v).all() for v in r))
 def test_common_permutation_ols(self):
  d=self.fixture();m=s.Model.from_frame(d,'y',['x','z'],['k']);p=np.random.default_rng(17).permutation(len(d))
  f=original.ols(m.y,np.c_[m.X,m.E[p]]);b=original.ols(m.y,m.X)
  np.testing.assert_allclose(m.permuted(p)['delta_bic'][0],f['bic']-b['bic'],atol=1e-8)
if __name__=='__main__':unittest.main()
