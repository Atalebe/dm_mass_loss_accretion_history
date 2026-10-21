import sys, unittest, json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from core import Model,design,standardize,pvalue,holm,rng_seed,perm_hash,original_ols_functions,oracle,InvalidAnalysis

class Tests(unittest.TestCase):
    def setUp(self):
        r=np.random.Generator(np.random.PCG64(70401));n=96
        self.ell=np.r_[np.zeros(n//2),r.uniform(.01,.8,n//2)]
        self.C=np.c_[np.ones(n),r.normal(size=(n,3))]
        self.K=r.normal(size=(n,4))+self.ell[:,None]
        self.y=self.C@np.array([.2,.1,.3,-.2])+.4*self.ell-.25*self.K[:,0]+r.normal(scale=.5,size=n)
        self.ols=original_ols_functions((ROOT/'reference/original_ols.py').read_text())
    def test_shapes(self):
        self.assertEqual(design(self.C,self.ell,'linear').shape,(96,5))
        self.assertEqual(design(self.C,self.ell,'indicator_quadratic').shape,(96,7))
    def test_indicator_exact(self):
        ell=self.ell.copy();ell[0]=np.nextafter(0.,1.)
        X=design(self.C,ell,'indicator_quadratic')
        np.testing.assert_allclose(X[:,-1],standardize((ell>0).astype(float))[0])
    def test_observed_original(self):
        for name in ['linear','indicator_quadratic']:
            m=Model(design(self.C,self.ell,name),self.y,self.K)
            self.assertEqual(oracle(m,m.M,m.observed(),self.ols)['fits'],4)
    def test_permuted_original(self):
        for name in ['linear','indicator_quadratic']:
            m=Model(design(self.C,self.ell,name),self.y,self.K)
            p=np.random.default_rng(442).permutation(m.n)
            self.assertEqual(oracle(m,m.E[p],m.permuted(p),self.ols)['fits'],4)
    def test_identity_permutation(self):
        m=Model(design(self.C,self.ell,'linear'),self.y,self.K)
        for k,v in m.observed().items():np.testing.assert_allclose(v,m.permuted(np.arange(m.n))[k],rtol=1e-10,atol=1e-10)
    def test_common_columns(self):
        K=np.c_[self.K,self.K[:,0]];m=Model(self.C,self.y,K)
        p=np.random.default_rng(23).permutation(m.n)
        a=m.permuted(p);self.assertAlmostEqual(a['delta_bic'][0],a['delta_bic'][-1],10)
    def test_scale_invariance(self):
        a=Model(self.C,self.y,self.K).observed();b=Model(self.C,self.y,self.K*17+33).observed()
        np.testing.assert_allclose(a['delta_bic'],b['delta_bic'],rtol=1e-9,atol=1e-9)
    def test_control_response_invariance(self):
        a=Model(self.C,self.y,self.K).observed();b=Model(self.C,self.y+self.C[:,1]/3,self.K).observed()
        np.testing.assert_allclose(a['delta_bic'],b['delta_bic'],rtol=1e-9,atol=1e-9)
        np.testing.assert_allclose(a['b_native'],b['b_native'],rtol=1e-9,atol=1e-9)
    def test_loss_response_invariance(self):
        X=design(self.C,self.ell,'linear')
        a=Model(X,self.y,self.K).observed();b=Model(X,self.y-self.ell/3,self.K).observed()
        np.testing.assert_allclose(a['delta_bic'],b['delta_bic'],rtol=1e-9,atol=1e-9)
    def test_variance_identity(self):
        m=Model(self.C,self.y,self.K);a=m.observed()
        np.testing.assert_allclose(a['delta_r2'],a['A_standardized']**2*a['residual_K_variance_fraction'])
        np.testing.assert_allclose(a['partial_r2'],1-np.exp((a['delta_bic']-np.log(m.n))/m.n))
    def test_missing_rank(self):
        with self.assertRaises(InvalidAnalysis):Model(np.c_[self.C,self.C[:,1]],self.y,self.K)
    def test_degenerate_candidate(self):
        with self.assertRaises(InvalidAnalysis):Model(self.C,self.y,np.c_[self.K,self.C[:,1]])
    def test_nonfinite(self):
        k=self.K.copy();k[0,0]=np.nan
        with self.assertRaises(InvalidAnalysis):Model(self.C,self.y,k)
    def test_invalid_dimension(self):
        with self.assertRaises(InvalidAnalysis):Model(self.C,self.y,self.K[:,0])
    def test_bad_permutation(self):
        m=Model(self.C,self.y,self.K)
        for p in [np.zeros(m.n,dtype=int),np.arange(m.n-1),np.arange(m.n,dtype=float)]:
            with self.assertRaises(InvalidAnalysis):m.permuted(p)
    def test_bad_design(self):
        with self.assertRaises(InvalidAnalysis):design(self.C,self.ell,'spline')
    def test_negative_loss(self):
        l=self.ell.copy();l[0]=-.1
        with self.assertRaises(InvalidAnalysis):design(self.C,l,'linear')
    def test_constant_indicator(self):
        with self.assertRaises(InvalidAnalysis):design(self.C,self.ell+.1,'indicator_quadratic')
    def test_constant(self):
        with self.assertRaises(InvalidAnalysis):standardize(np.ones(10))
    def test_empirical_p(self):
        self.assertEqual(pvalue(np.array([1.,2.,3.]),0.),(0,.25))
        self.assertEqual(pvalue(np.array([1.,2.,3.]),2.),(2,.75))
    def test_invalid_null(self):
        for v in [[],[np.nan],[[1,2]]]:
            with self.assertRaises(InvalidAnalysis):pvalue(v,1.)
    def test_holm(self):
        np.testing.assert_allclose(holm([.02,.001,.9]),[.04,.003,.9])
    def test_seed_separation(self):
        vals=[rng_seed(2026101905,s,c,d) for s in ['a','b'] for c in ['x','y'] for d in ['linear','indicator_quadratic']]
        self.assertEqual(len(set(vals)),8)
    def test_rng_state(self):
        r=np.random.Generator(np.random.PCG64(rng_seed(9,'s','c','linear')));state=r.bit_generator.state;p=r.permutation(96)
        q=np.random.Generator(np.random.PCG64());q.bit_generator.state=state
        self.assertEqual(perm_hash(p),perm_hash(q.permutation(96)))
    def test_shared_nuisance_refit_matters(self):
        m=Model(design(self.C,self.ell,'linear'),self.y,self.K)
        p=np.argsort(m.E[:,0]);Z=m.E[p];a=m.permuted(p)
        wrong=m.stats(m.ey@Z,m.enorm)
        self.assertGreater(float(np.max(abs(a['delta_bic']-wrong['delta_bic']))),1e-6)

if __name__=='__main__':unittest.main(verbosity=2)
