"""AI-assisted second implementation (Claude, Anthropic).
Numerical bodies retained; acquisition paths and module-level execution excluded.
Not independent human review and not new simulation data.
"""
import numpy as np
import pandas as pd
import math

GRID=[0.2,0.3,0.5,0.8,1.2,1.8,2.6,3.0,3.5,4.0,4.25,4.5,4.75,5.0,5.25,5.5,5.75,6.0,6.5,7.0,7.5,8.0,10.0,12.0,16.0,20.0]

def gcol(g): return 'M_acc_gamma_'+str(float(g)).replace('.','p')

EPOCHS=['a10','a25','a50','a75']

def zs(x):
    x=np.asarray(x,float); s=x.std(); return (x-x.mean())/s

def controls(d, epochs=True, extra=()):
    m=zs(d['logm']); cols=[m,m**2,m**3,np.asarray(d['present_acc_rate'],float)]
    bins=d['mass_bin'].astype(str); lv=sorted(bins.unique())
    for v in lv[1:]: cols.append((bins==v).to_numpy(float))
    if epochs: cols+= [d[e].to_numpy(float) for e in EPOCHS]
    for e in extra: cols.append(np.asarray(e,float))
    X=np.column_stack([np.ones(len(d))]+[zs(c) for c in cols])
    return X

def qr_basis(X, tol=1e-10):
    U_,s,Vt=np.linalg.svd(X,full_matrices=False); r=int((s>tol*s[0]).sum()); return U_[:,:r], r

def fit(d, kcol, epochs=True, extra=()):
    y=zs(d['Yv']); k=zs(d[kcol]); X=controls(d,epochs,extra); n=len(y)
    Q,r=qr_basis(X); yr=y-Q@(Q.T@y); kr=k-Q@(Q.T@k)
    rss0=yr@yr; b=(kr@yr)/(kr@kr); rss1=rss0-b*b*(kr@kr)
    q=rss1/rss0; dbic=n*math.log(q)+math.log(n); tss=n*1.0
    se=math.sqrt(rss1/(n-r-1)/(kr@kr))
    sy=np.std(d['Yv']); sk=np.std(d[kcol])
    return dict(n=n,rank=r,dR2=(rss0-rss1)/tss,partial=1-q,dBIC=dbic,A=b,SE=se,b_native=b*sy/sk,r2c=1-rss0/tss,vk=(kr@kr)/n)

def joint_null(d, epochs=True, extra=(), B=1000, seed=12345, grid=GRID):
    y=zs(d['Yv']); X=controls(d,epochs,extra); n=len(y); Q,r=qr_basis(X)
    K=np.column_stack([zs(d[gcol(g)]) for g in grid])
    yr=y-Q@(Q.T@y); E=K-Q@(Q.T@K); yy=yr@yr
    obs=n*np.log(1-((E.T@yr)**2)/(yy*(E*E).sum(0)))+math.log(n)
    rng=np.random.default_rng(seed); out=np.empty(B)
    for i in range(B):
        P=E[rng.permutation(n)]; Rr=P-Q@(Q.T@P)   # residual of H K + P E on controls
        c=(Rr.T@yr)**2/(yy*(Rr*Rr).sum(0)); out[i]=np.min(n*np.log(1-c)+math.log(n))
    return obs,out

def rcs(x, knots):
    # restricted cubic spline basis (Harrell), excluding linear term
    k=np.asarray(knots); t=lambda u: np.maximum(u,0)**3
    K=len(k); out=[]
    for j in range(K-2):
        out.append(t(x-k[j]) - t(x-k[K-2])*(k[K-1]-k[j])/(k[K-1]-k[K-2]) + t(x-k[K-1])*(k[K-2]-k[j])/(k[K-1]-k[K-2]))
    return out
