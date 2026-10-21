"""Fixed-model sensitivity calculations. No filesystem or network effects on import."""
import numpy as np
from scipy.linalg import qr, solve_triangular

class InvalidAnalysis(ValueError): pass

def require(v, msg):
    if not v: raise InvalidAnalysis(msg)

def partition(coords, lo, hi, q):
    x=np.asarray(coords,float);lo=np.asarray(lo,float);hi=np.asarray(hi,float)
    require(x.ndim==2 and x.shape[1]==3 and len(x)>0,'GEOMETRY_SHAPE')
    require(lo.shape==hi.shape==(3,) and np.all(hi>lo),'INVALID_BOUNDS')
    require(isinstance(q,int) and q>=2,'INVALID_GRID')
    require(np.isfinite(x).all() and np.all(x>=lo-1e-8) and np.all(x<=hi+1e-8),'COORDINATES_OUTSIDE')
    ix=np.minimum(q-1,np.floor(q*(x-lo)/(hi-lo)).astype(int))
    require(np.all(ix>=0) and np.all(ix<q),'INVALID_CELLS')
    return (ix[:,0]*q+ix[:,1])*q+ix[:,2]

def poststratification(parent_bins, observed_bins):
    p=np.asarray(parent_bins,str);o=np.asarray(observed_bins,str)
    require(p.ndim==o.ndim==1 and len(p)>0 and len(o)>0,'BIN_SHAPE')
    labels,counts=np.unique(p,return_counts=True);oc={s:int((o==s).sum()) for s in labels}
    require(set(o)<=set(labels),'UNKNOWN_STRATUM')
    require(all(v>0 for v in oc.values()),'ZERO_COMPLETE_SUPPORT')
    by={s:float(n/oc[s]) for s,n in zip(labels,counts)}
    w=np.array([by[s] for s in o])
    rows=[dict(mass_bin=str(s),n_available=int(n),n_complete=oc[s],weight=by[s]) for s,n in zip(labels,counts)]
    return w,rows

def svd_fit(X,y,w=None):
    X=np.asarray(X,float);y=np.asarray(y,float)
    require(X.ndim==2 and y.ndim==1 and X.shape[0]==len(y),'FIT_SHAPE')
    require(len(y)>X.shape[1]+1 and np.isfinite(X).all() and np.isfinite(y).all(),'FIT_FINITE_OR_DOF')
    if w is None:w=np.ones(len(y))
    w=np.asarray(w,float)
    require(w.shape==y.shape and np.isfinite(w).all() and np.all(w>0),'INVALID_WEIGHTS')
    wn=w/w.mean();sw=np.sqrt(wn);W=X*sw[:,None];wy=y*sw
    U,s,Vt=np.linalg.svd(W,full_matrices=False);rank=int((s>s[0]*1e-12).sum())
    b=Vt[:rank].T@((U[:,:rank].T@wy)/s[:rank]);e=y-X@b
    rss=float(np.dot(wn,e*e));mean=float(np.average(y,weights=wn));tss=float(np.dot(wn,(y-mean)**2))
    require(tss>0 and rss>1e-24*tss,'CONSTANT_OR_PERFECT_RESPONSE')
    return dict(beta=b,rank=rank,rss=rss,tss=tss,s=s,wn=wn,Vt=Vt)

def qr_fit(X,y,w=None):
    X=np.asarray(X,float);y=np.asarray(y,float)
    w=np.ones(len(y)) if w is None else np.asarray(w,float)/np.mean(w)
    W=X*np.sqrt(w[:,None]);z=y*np.sqrt(w)
    Q,R,p=qr(W,mode='economic',pivoting=True);s=np.linalg.svd(W,compute_uv=False);r=int((s>s[0]*1e-12).sum())
    b=np.zeros(X.shape[1]);b[p[:r]]=solve_triangular(R[:r,:r],Q[:,:r].T@z)
    return b,float(np.dot(w,(y-X@b)**2)),r

def increment(C,k,y,sk,sy,w=None,oracle=False):
    C=np.asarray(C,float);k=np.asarray(k,float);y=np.asarray(y,float)
    require(k.shape==y.shape and sk>0 and sy>0,'INVALID_SCALE')
    a=svd_fit(C,y,w);X=np.column_stack([C,k]);b=svd_fit(X,y,w)
    require(b['rank']==a['rank']+1,'HISTORY_NOT_IDENTIFIABLE')
    if b['rank']<X.shape[1]:
        require(np.max(np.abs(b['Vt'][b['rank']:, -1]))<1e-8,'HISTORY_NULLSPACE')
    red=(a['rss']-b['rss']);require(red>=-1e-10*a['tss'],'NEGATIVE_INCREMENT')
    wn=b['wn'];sw=np.sqrt(wn);kc=k-C@svd_fit(C,k,w)['beta']
    syw=np.sqrt(np.average((y-np.average(y,weights=wn))**2,weights=wn))
    skw=np.sqrt(np.average((k-np.average(k,weights=wn))**2,weights=wn))
    history_beta=float(b['beta'][-1]);result=dict(n=len(y),k_controls=a['rank'],k_full=b['rank'],control_columns=C.shape[1],
       b_native=history_beta/sk,A_fixed=history_beta/sy,A_local=history_beta*skw/syw,
       delta_r2=red/a['tss'],partial_r2=red/a['rss'],r2_controls=1-a['rss']/a['tss'],
       delta_bic=float(len(y)*np.log(b['rss']/a['rss'])+np.log(len(y))) if w is None else None,
       se_ols_native=float(np.sqrt((b['rss']/(len(y)-b['rank']))/np.dot(wn,kc*kc))/sk) if w is None else None)
    # Independent pivoted-QR fit; coefficients for nuisance aliases can differ, history must not.
    if oracle:
        qb,qrss,rank=qr_fit(X,y,w);_,qcrss,crank=qr_fit(C,y,w)
        require(rank==b['rank'] and crank==a['rank'],'ORACLE_RANK')
        require(np.allclose([qb[-1],qrss,qcrss],[history_beta,b['rss'],a['rss']],rtol=2e-9,atol=1e-9),'QR_ORACLE')
        result['oracle_max_abs_error']=float(max(abs(qb[-1]-history_beta),abs(qrss-b['rss']),abs(qcrss-a['rss'])))
    # Check weighted variance identity independent of arbitrary overall weights scale.
    expected=(history_beta**2)*np.dot(wn,kc*kc)/a['tss']
    require(np.isclose(result['delta_r2'],expected,rtol=1e-8,atol=1e-10),'VARIANCE_IDENTITY')
    return result
