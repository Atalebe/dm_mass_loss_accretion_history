from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from sensitivity import partition,poststratification,increment,svd_fit,qr_fit,InvalidAnalysis
class Tests(unittest.TestCase):
 def setUp(self):
  g=np.random.default_rng(2026102006);self.n=140;self.x=g.normal(size=(self.n,3));self.C=np.c_[np.ones(self.n),self.x];self.k=g.normal(size=self.n);self.y=self.C@np.arange(4)+.3*self.k+g.normal(size=self.n)
 def test_known_coefficient(self):
  s=increment(self.C,self.k,self.y,1,1,oracle=True);self.assertGreater(s['b_native'],0)
 def test_rank_alias(self):
  a=increment(self.C,self.k,self.y,1,1,oracle=True);b=increment(np.c_[self.C,self.C[:,1]],self.k,self.y,1,1,oracle=True);self.assertAlmostEqual(a['b_native'],b['b_native'])
 def test_empty_dummy(self):
  a=increment(self.C,self.k,self.y,1,1);b=increment(np.c_[self.C,np.zeros(self.n)],self.k,self.y,1,1,oracle=True);self.assertAlmostEqual(a['delta_r2'],b['delta_r2'])
 def test_history_alias_rejected(self):
  with self.assertRaises(InvalidAnalysis):increment(self.C,self.C[:,1],self.y,1,1)
 def test_weights_scale(self):
  w=np.linspace(1,4,self.n);a=increment(self.C,self.k,self.y,1,1,w,True);b=increment(self.C,self.k,self.y,1,1,w*1e7,True)
  for k in ['b_native','delta_r2','partial_r2']:self.assertAlmostEqual(a[k],b[k],places=10)
 def test_weights_ones(self):
  a=increment(self.C,self.k,self.y,1,1);b=increment(self.C,self.k,self.y,1,1,np.ones(self.n))
  self.assertAlmostEqual(a['b_native'],b['b_native']);self.assertIsNone(b['delta_bic'])
 def test_negative_weights(self):
  with self.assertRaises(InvalidAnalysis):increment(self.C,self.k,self.y,1,1,-np.ones(self.n))
 def test_zero_weight(self):
  w=np.ones(self.n);w[0]=0
  with self.assertRaises(InvalidAnalysis):increment(self.C,self.k,self.y,1,1,w)
 def test_nan(self):
  x=self.C.copy();x[0,0]=np.nan
  with self.assertRaises(InvalidAnalysis):increment(x,self.k,self.y,1,1)
 def test_response_constant(self):
  with self.assertRaises(InvalidAnalysis):increment(self.C,self.k,np.ones(self.n),1,1)
 def test_zero_scale(self):
  with self.assertRaises(InvalidAnalysis):increment(self.C,self.k,self.y,0,1)
 def test_partition_corners(self):
  x=np.array([[0,0,0],[1,1,1],[.5,0,0],[.49,.5,.5]]);self.assertEqual(list(partition(x,[0]*3,[1]*3,2)),[0,7,4,3])
 def test_partition_geometry_translation(self):
  x=np.random.default_rng(6).random((100,3));a=partition(x,[0]*3,[1]*3,3);b=partition(x+4,[4]*3,[5]*3,3);np.testing.assert_array_equal(a,b)
 def test_partition_reject(self):
  with self.assertRaises(InvalidAnalysis):partition(np.ones((3,2)),[0]*3,[1]*3,2)
 def test_partition_outside(self):
  with self.assertRaises(InvalidAnalysis):partition(np.array([[4,0,0]]),[0]*3,[1]*3,2)
 def test_partition_degenerate(self):
  with self.assertRaises(InvalidAnalysis):partition(np.zeros((3,3)),[0]*3,[0]*3,2)
 def test_partition_exhaustive(self):
  x=np.random.default_rng(2).random((100,3));a=partition(x,[0]*3,[1]*3,2); masks=[a==i for i in np.unique(a)];np.testing.assert_array_equal(np.stack(masks).sum(0),np.ones(100))
 def test_poststrat_totals(self):
  w,r=poststratification(['a']*8+['b']*2,['a']*2+['b']);self.assertAlmostEqual(w.sum(),10);self.assertEqual(w.tolist(),[4,4,2])
 def test_poststrat_no_missing(self):
  w,r=poststratification(['a','b'],['a','b']);np.testing.assert_array_equal(w,[1,1])
 def test_poststrat_support(self):
  with self.assertRaises(InvalidAnalysis):poststratification(['a','b'],['a'])
 def test_poststrat_unknown(self):
  with self.assertRaises(InvalidAnalysis):poststratification(['a','b'],['a','c'])
 def test_rescale_invariance(self):
  a=increment(self.C,self.k,self.y,1,1);b=increment(self.C,self.k*3+7,self.y,3,1);self.assertAlmostEqual(a['b_native'],b['b_native']*9)
 def test_orthogonal_history(self):
  a=increment(self.C,self.k,self.y,1,1,oracle=True);Q=np.linalg.qr(self.C)[0];r=self.k-Q@(Q.T@self.k);b=increment(self.C,r,self.y,1,1,oracle=True);self.assertAlmostEqual(a['b_native'],b['b_native'])
 def test_weight_normal_equations(self):
  w=np.linspace(1,3,self.n);a=increment(self.C,self.k,self.y,1,1,w,True);X=np.c_[self.C,self.k];b=np.linalg.solve(X.T@(w[:,None]*X),X.T@(w*self.y));self.assertAlmostEqual(a['b_native'],b[-1])
if __name__=='__main__':unittest.main()
