"""SUPP005 fixed-design scalar OLS increments. No file/network I/O on import."""
from __future__ import annotations
import hashlib, json
import numpy as np

class InvalidAnalysis(RuntimeError):
    pass

def require(ok, message):
    if not bool(ok):
        raise InvalidAnalysis(message)

def standardize(v):
    v=np.asarray(v,dtype=float)
    require(v.ndim in (1,2) and len(v)>0 and np.isfinite(v).all(),'INVALID_STANDARDIZATION')
    mean=v.mean(axis=0);sd=v.std(axis=0,ddof=0)
    require(np.all(sd>0),'CONSTANT_STANDARDIZATION')
    return (v-mean)/sd,mean,sd

def design(C,ell,kind):
    C=np.asarray(C,float);ell=np.asarray(ell,float)
    require(C.ndim==2 and ell.ndim==1 and len(C)==len(ell),'DESIGN_SHAPE')
    require(np.isfinite(C).all() and np.isfinite(ell).all() and np.all(ell>=-1e-12),'DESIGN_VALUES')
    require(kind in ('linear','indicator_quadratic'),'UNKNOWN_DESIGN')
    columns=[standardize(ell)[0]]
    if kind=='indicator_quadratic':
        columns.extend([standardize(ell**2)[0],standardize((ell>0).astype(float))[0]])
    return np.column_stack([C,*columns])

def rng_seed(root,sample,case,kind):
    return int.from_bytes(hashlib.sha256(f'DM-PAPER-SUPP-005|{root}|{sample}|{case}|{kind}'.encode()).digest()[:16],'little')

def perm_hash(p):
    return hashlib.sha256(np.asarray(p,dtype='<i8').tobytes()).hexdigest()

def close(a,b,what='',bic=False):
    aa=np.asarray(a,dtype=float);bb=np.asarray(b,dtype=float)
    require(aa.shape==bb.shape and np.isfinite(aa).all() and np.isfinite(bb).all(),'COMPARISON_VALUES:'+what)
    error=float(np.max(np.abs(aa-bb))) if aa.size else 0.
    require(np.allclose(aa,bb,atol=1e-6 if bic else 1e-8,rtol=1e-8),'NUMERICAL_MISMATCH:'+what+':'+str(error))
    return error

class Model:
    def __init__(self,X,y_native,K_native):
        self.X=np.asarray(X,float);self.yn=np.asarray(y_native,float);self.Kn=np.asarray(K_native,float)
        require(self.X.ndim==2 and self.yn.ndim==1 and self.Kn.ndim==2,'MODEL_SHAPE')
        self.n=len(self.yn);self.p=self.X.shape[1]
        require(len(self.X)==self.n==len(self.Kn) and self.p>0 and self.n>self.p+2,'MODEL_SIZE')
        require(np.isfinite(self.X).all(),'NONFINITE_CONTROLS')
        self.y,self.my,self.sy=standardize(self.yn)
        self.M,self.mk,self.sk=standardize(self.Kn)
        self.singular=np.linalg.svd(self.X,compute_uv=False)
        require(np.count_nonzero(self.singular>self.singular[0]*1e-12)==self.p,'RANK_DEFICIENT_CONTROLS')
        self.Q=np.linalg.qr(self.X,mode='reduced')[0]
        self.ey=self.y-self.Q@(self.Q.T@self.y)
        self.E=self.M-self.Q@(self.Q.T@self.M)
        self.enorm=np.einsum('ij,ij->j',self.E,self.E)
        self.rss=float(self.ey@self.ey);self.tss=float((self.y-self.y.mean())@(self.y-self.y.mean()))
        require(self.rss>1e-12*self.tss,'EXACT_CONTROL_FIT')
        require(np.all(self.enorm>1e-12*self.n),'DEGENERATE_CANDIDATE')
    def stats(self,score,norm):
        score=np.asarray(score,float);norm=np.asarray(norm,float)
        require(score.shape==self.enorm.shape==norm.shape,'SCORE_SHAPE')
        require(np.isfinite(score).all() and np.isfinite(norm).all() and np.all(norm>1e-12*self.n),'INVALID_SCORE')
        red=score**2/norm
        require(np.all(red>=0) and np.all(red<self.rss),'INVALID_REDUCTION')
        beta=score/norm;se=np.sqrt((self.rss-red)/(self.n-self.p-1)/norm)
        return {'delta_bic':self.n*np.log1p(-red/self.rss)+np.log(self.n),
          'delta_r2':red/self.tss,'partial_r2':red/self.rss,
          'A_standardized':beta,'SE_standardized':se,'t':beta/se,
          'b_native':beta*self.sy/self.sk,'SE_native':se*self.sy/self.sk,
          'residual_K_variance_fraction':norm/self.n}
    def observed(self):
        return self.stats(self.ey@self.E,self.enorm)
    def permuted(self,p):
        p=np.asarray(p)
        require(p.shape==(self.n,) and np.issubdtype(p.dtype,np.integer),'PERMUTATION_SHAPE')
        require(np.array_equal(np.sort(p),np.arange(self.n)),'NONBIJECTIVE_PERMUTATION')
        Z=self.E[p,:];proj=self.Q.T@Z
        norm=self.enorm-np.einsum('ij,ij->j',proj,proj)
        return self.stats(self.ey@Z,norm)

def pvalue(null,observed):
    null=np.asarray(null,float)
    require(null.ndim==1 and len(null)>0 and np.isfinite(null).all() and np.isfinite(observed),'INVALID_NULL')
    b=int(np.count_nonzero(null<=observed))
    return b,(b+1)/(len(null)+1)

def holm(values):
    p=np.asarray(values,float)
    require(p.ndim==1 and len(p)>0 and np.isfinite(p).all() and np.all((p>=0)&(p<=1)),'INVALID_PVALUES')
    order=np.argsort(p,kind='stable');out=np.empty(len(p));last=0.
    for rank,i in enumerate(order):
        last=max(last,(len(p)-rank)*p[i]);out[i]=min(1.,last)
    return out

def original_ols_functions(source):
    import ast,math
    t=ast.parse(source)
    fn=[n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='ols']
    require(len(fn)==1,'ORIGINAL_OLS_NOT_UNIQUE')
    ns={'np':np,'math':math}
    exec(compile(ast.Module(fn,type_ignores=[]),'<original111:ols>','exec'),ns)
    return ns['ols']

def oracle(model,Z,statistics,ols):
    base=ols(model.y,model.X);maximum={}
    for j in range(Z.shape[1]):
        fitted=ols(model.y,np.column_stack([model.X,Z[:,j]]))
        expected={'delta_bic':fitted['bic']-base['bic'],
          'delta_r2':fitted['r2']-base['r2'],'partial_r2':1-fitted['rss']/base['rss'],
          'A_standardized':fitted['beta'][-1],'SE_standardized':fitted['se'][-1],
          'b_native':fitted['beta'][-1]*model.sy/model.sk[j],
          'SE_native':fitted['se'][-1]*model.sy/model.sk[j]}
        for key,v in expected.items():
            error=close(statistics[key][j],v,key,bic=key=='delta_bic')
            maximum[key]=max(maximum.get(key,0.),error)
    return {'fits':Z.shape[1],'checks':Z.shape[1]*7,'maximum_absolute_errors':maximum}
