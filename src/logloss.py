"""Fixed-model continuous historical mass-ratio sensitivity; no I/O on import."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

class InvalidAnalysis(RuntimeError): pass

def require(condition, message):
    if not condition: raise InvalidAnalysis(message)

def standardize(x):
    x=np.asarray(x,dtype=float)
    require(x.ndim==1 and len(x)>0 and np.isfinite(x).all(),'INVALID_VECTOR')
    sd=float(x.std(ddof=0)); require(sd>0,'CONSTANT_VECTOR')
    return (x-x.mean())/sd, float(x.mean()), sd

def loss_coordinate(maximum,terminal):
    maximum=np.asarray(maximum,float);terminal=np.asarray(terminal,float)
    require(maximum.ndim==1 and maximum.shape==terminal.shape and len(maximum)>0,'MASS_SHAPE')
    require(np.isfinite(maximum).all() and np.isfinite(terminal).all() and np.all(maximum>0) and np.all(terminal>0),'INVALID_MASS')
    ell=np.log10(maximum/terminal)
    require(np.all(ell>=-1e-12),'MAXIMUM_BELOW_TERMINAL')
    return ell  # No rounding or clipping of valid input values.

@dataclass
class Fit:
    X: np.ndarray
    y: np.ndarray
    beta: np.ndarray
    residual: np.ndarray
    se: np.ndarray
    inv: np.ndarray
    Q: np.ndarray
    singular: np.ndarray
    rss: float
    tss: float
    rank: int
    bic: float
    r2: float
    @property
    def n(self): return len(self.y)

def fit(X,y):
    X=np.asarray(X,float);y=np.asarray(y,float)
    require(X.ndim==2 and y.ndim==1 and len(X)==len(y),'FIT_SHAPE')
    require(np.isfinite(X).all() and np.isfinite(y).all(),'NONFINITE_FIT')
    n,p=X.shape;require(p>0 and n>p+1,'INSUFFICIENT_DOF')
    s=np.linalg.svd(X,compute_uv=False)
    rank=int((s>s[0]*1e-12).sum()); require(rank==p,'RANK_DEFICIENT')
    Q,R=np.linalg.qr(X,mode='reduced'); beta=np.linalg.solve(R,Q.T@y)
    e=y-X@beta;rss=float(e@e);tss=float((y-y.mean())@(y-y.mean()))
    require(tss>0 and rss>1e-24*tss,'ZERO_VARIANCE_OR_EXACT_FIT')
    Ri=np.linalg.solve(R,np.eye(p));inv=Ri@Ri.T
    se=np.sqrt(np.diag(inv)*(rss/(n-p)))
    return Fit(X,y,beta,e,se,inv,Q,s,rss,tss,p,n*np.log(rss/n)+p*np.log(n),1-rss/tss)

def residual(x,Q): return x-Q@(Q.T@x)

def increment(C,kz,y,sy,sk):
    c=fit(C,y);f=fit(np.c_[C,kz],y)
    rk=residual(kz,c.Q);red=c.rss-f.rss
    require(red>=-1e-10*c.tss,'NEGATIVE_NESTED_INCREMENT')
    stats={'n':len(y),'k_controls':c.rank,'rank_full':f.rank,
        'b_native':float(f.beta[-1]/sk),'SE_native':float(f.se[-1]/sk),
        'A_standardized':float(f.beta[-1]/sy),'SE_standardized':float(f.se[-1]/sy),
        't':float(f.beta[-1]/f.se[-1]),'delta_r2':red/c.tss,
        'partial_r2':red/c.rss,'delta_bic':f.bic-c.bic,'r2_controls':c.r2,
        'r2_full':f.r2,'rss_controls':c.rss,'rss_full':f.rss,
        'residual_K_variance_fraction':float(rk@rk/len(y)),
        'condition_controls':float(c.singular[0]/c.singular[-1]),
        'condition_full':float(f.singular[0]/f.singular[-1])}
    return stats,c,f

def compare(C,y,K,ell):
    y=np.asarray(y,float); C=np.asarray(C,float)
    kz,mk,sk=standardize(K);lz,ml,sl=standardize(ell);_,my,sy=standardize(y)
    require(len(kz)==len(y)==len(lz),'PAIRED_SHAPE')
    b,c,f=increment(C,kz,y,sy,sk)
    a,ca,fa=increment(np.c_[C,lz],kz,y,sy,sk)
    c_native=float(fa.beta[-2]/sl)
    kc=residual(np.asarray(K,float),c.Q);lc=residual(np.asarray(ell,float),c.Q)
    loading=float(kc@lc/(kc@kc));corr=float((kc@lc)/np.sqrt((kc@kc)*(lc@lc)))
    accounting=float(c_native*loading)
    extras={'ell_coefficient_native':c_native,'ell_SE_native':float(fa.se[-2]/sl),
       'ell_coefficient_standardized':float(fa.beta[-2]/sy),'ell_SE_standardized':float(fa.se[-2]/sy),
       'ell_sd':sl,'ell_mean':ml,'K_sd':sk,'Y_sd':sy,'K_mean':mk,'Y_mean':my,
       'conditional_corr_K_ell':corr,'ell_on_K_after_C_slope':loading,
       'native_b_change':b['b_native']-a['b_native'],'accounted_b_change':accounting,
       'accounting_error':abs(b['b_native']-a['b_native']-accounting),
       'fraction_increment_reduction':1-a['delta_r2']/b['delta_r2'] if b['delta_r2']>0 else None,
       'fraction_native_slope_reduction':1-abs(a['b_native'])/abs(b['b_native']) if b['b_native']!=0 else None}
    return b,a,extras,(c,f,ca,fa)

def influence(fit_result,sk):
    """Analytic fixed-coordinate deletion diagnostics. Formula matches OLS DFBETAS."""
    f=fit_result;n,p=f.X.shape;h=np.einsum('ij,ij->i',f.Q,f.Q);den=1-h
    valid=den>1e-10
    rows=[]
    for i in range(n):
        out={'row':i,'leverage':float(h[i]),'analytic_defined':bool(valid[i])}
        if not valid[i]:
            out.update(studentized_internal=None,studentized_external=None,DFBETA_K_native=None,DFBETAS_K=None,b_leave_one_out_native=None)
        else:
            delta=(f.inv@f.X[i])*f.residual[i]/den[i]
            s2del=(f.rss-f.residual[i]**2/den[i])/(n-p-1)
            require(s2del>0,'NONPOSITIVE_DELETED_VARIANCE')
            out.update(studentized_internal=float(f.residual[i]/np.sqrt(f.rss/(n-p)*den[i])),
                studentized_external=float(f.residual[i]/np.sqrt(s2del*den[i])),
                DFBETA_K_native=float(delta[-1]/sk),
                DFBETAS_K=float(delta[-1]/np.sqrt(s2del*f.inv[-1,-1])),
                b_leave_one_out_native=float((f.beta[-1]-delta[-1])/sk))
        rows.append(out)
    return rows
