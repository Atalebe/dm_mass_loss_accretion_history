"""Reproduce preserved formation/threshold searches and the separate spline cross-check.

Only the original samples, controls and recorded streams are evaluated. This is
archival replay, not another experiment or a claim of spatial calibration.
"""
from pathlib import Path
import os
for k in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS'):os.environ[k]='1'
import argparse,hashlib,json,sys,time,traceback,socket
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/legacy'))
import original_functions as original
import supp_core as sc
import spline_crosscheck as spline
N=0; MAXERR=0.
def need(x,s):
 global N
 N+=1
 if not bool(x):raise RuntimeError(s)
def close(a,b,label,tol=1e-8):
 global N,MAXERR
 a,b=np.asarray(a,float),np.asarray(b,float)
 need(a.shape==b.shape and np.isfinite(a).all() and np.isfinite(b).all(),'Invalid comparison:'+label)
 err=float(np.max(abs(a-b))) if a.size else 0.;MAXERR=max(MAXERR,err)
 need(np.allclose(a,b,atol=tol,rtol=1e-8),'Mismatch:'+label+':'+str(err));N+=a.size

def load(p):
 with np.load(p,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}
def csv(p):return pd.read_csv(p,keep_default_na=False,na_values=[''])
def baseframe(sample):
 d=ROOT/'analysis_data/catalogues'/sample
 f=csv(d/'feature.csv.gz');f=f[f.tree_status=='ok'].copy()
 f['_join_id']=f[original.resolve_feature_id(f)].map(original.canonical_id)
 f,meta,controls=original.add_yv_and_base_columns(f,sample,8)
 h=csv(d/'formation.csv.gz');h['_join_id']=h.halo_id.map(original.canonical_id)
 need(f._join_id.is_unique and h._join_id.is_unique,'Nonunique IDs')
 need(set(f._join_id)==set(h._join_id),'Feature/formation denominator mismatch')
 merged=f.merge(h,on='_join_id',validate='one_to_one',sort=False,suffixes=('','_formation'))
 return merged,controls

def formation(full):
 folder=ROOT/'analysis_data/legacy/formation_search';fits=csv(folder/'observed_fits.csv')
 report=[]
 for p in sorted(folder.glob('*__design.json')):
  key=p.name.removesuffix('__design.json');cfg=json.loads(p.read_text());sample=cfg['sample'];case=cfg['case']
  ids=(folder/(key+'__ids.txt')).read_text().splitlines()
  frame,controls=baseframe(sample)
  if case.startswith('extended'):
   ext=csv(ROOT/'analysis_data/catalogues'/sample/'extended.csv.gz');ext['_join_id']=ext.halo_id.map(original.canonical_id)
   frame=frame.merge(ext[['_join_id','a05','a90']],on='_join_id',validate='one_to_one',sort=False)
  frame=frame.set_index('_join_id',verify_integrity=True).loc[ids].reset_index()
  cols=controls+['a10','a25','a50','a75']+(['a05','a90'] if case=='extended_C6' else [])
  rows=fits[(fits['sample']==sample)&(fits['case']==case)];grid=rows.gamma.to_numpy(float)
  model=sc.Model.from_frame(frame,'target_yv_log_vmax_mass_scaled',cols,[sc.gamma_column(g) for g in grid])
  need(len(ids)==model.n==cfg['n'],'Formation n');need(model.k==cfg['k_controls'],'Formation rank')
  values=model.observed()
  for field,arr in values.items():close(arr,rows[field].to_numpy(),key+':'+field,1e-6 if field=='delta_bic' else 1e-8)
  nn=folder/(key+'__null.npz');recomputed=0
  if nn.exists():
   z=load(nn);stream=json.loads((folder/(key+'__random_stream.json')).read_text());rng=np.random.Generator(np.random.PCG64(stream['seed']))
   need(rng.bit_generator.state==stream['before'],'Formation initial RNG')
   need(z['delta_bic'].shape==(1000,26),'Formation null dimensions')
   for b in range(1000):
    perm=rng.permutation(model.n)
    need(hashlib.sha256(np.asarray(perm,dtype='<i8').tobytes()).hexdigest()==stream['permutation_index_sha256'][b],'Formation permutation identity')
    if full or b in (0,499,999):
     out=model.permuted(perm)
     for name in ['delta_bic','delta_r2','A_standardized']:close(out[name],z[name][b],key+' null '+name,1e-6 if name=='delta_bic' else 1e-8)
     recomputed+=26
   need(rng.bit_generator.state==stream['after'],'Formation final RNG')
   expected=json.loads((folder/(key+'__result.json')).read_text())
   summaries=sc.summarize_null(z['delta_bic'],values['delta_bic'],grid,expected['historical_gamma'],[.5,1.2,1.8,2.6,3.,4.5])
   for group in ['full26','published6']:
    for k,v in summaries[group].items():
     if isinstance(v,dict):
      for kk,vv in v.items():close(vv,expected['null_summary'][group][k][kk],'Formation summary '+kk)
     else:close(v,expected['null_summary'][group][k],'Formation summary '+k)
  report.append({'case':key,'n':model.n,'observed_candidates':len(grid),'null_candidates_replayed':recomputed})
  print('FORMATION_REPLAY',key,flush=True)
 need(len(report)==15,'Formation model count')
 return report

def threshold(full):
 folder=ROOT/'analysis_data/legacy/threshold_search';fits=csv(folder/'observed_fits.csv');summary=csv(folder/'sensitivity_summary.csv');report=[]
 for p in sorted(folder.glob('*__prepared.npz')):
  key=p.name.removesuffix('__prepared.npz');cfg=json.loads((folder/(key+'__design.json')).read_text());z=load(p)
  ids=(folder/(key+'__ids.txt')).read_text().splitlines();X,y,M=z['X'],z['y'],z['M'];n=len(y)
  U,s,_=np.linalg.svd(X,full_matrices=False);need(s[-1]>1e-12*s[0],'Threshold rank')
  ey=y-U@(U.T@y);E=M-U@(U.T@M);rss=float(ey@ey);tss=float(np.sum((y-y.mean())**2))
  def statistics(Z):
   e=Z-U@(U.T@Z);norm=np.sum(e*e,axis=0);score=ey@e;red=score**2/norm;b=score/norm
   return dict(delta_bic=n*np.log1p(-red/rss)+np.log(n),delta_r2=red/tss,A_standardized=b)
  obs=statistics(M);rows=fits[(fits['sample']==cfg['sample'])&(fits['case']==cfg['case'])]
  need(len(ids)==n==cfg['n'] and len(set(ids))==n,'Threshold identity count')
  need(hashlib.sha256((folder/(key+'__ids.txt')).read_bytes()).hexdigest()==cfg['ids_sha256'],'Threshold identity hash')
  for k,v in obs.items():close(v,rows[k].to_numpy(),key+' observed '+k,1e-6 if k=='delta_bic' else 1e-8)
  nn=folder/(key+'__null.npz');recomputed=0
  if nn.exists():
   null=load(nn);stream=json.loads((folder/(key+'__random_stream.json')).read_text());rng=np.random.Generator(np.random.PCG64(stream['seed']))
   need(rng.bit_generator.state==stream['before'],'Threshold initial RNG')
   for b in range(1000):
    perm=rng.permutation(n)
    need(hashlib.sha256(np.asarray(perm,dtype='<i8').tobytes()).hexdigest()==stream['permutation_index_sha256'][b],'Threshold permutation identity')
    if full or b in (0,499,999):
     out=statistics(E[perm])
     for k,v in out.items():close(v,null[k][b],key+' null '+k,1e-6 if k=='delta_bic' else 1e-8)
     recomputed+=26
   need(rng.bit_generator.state==stream['after'],'Threshold final RNG')
   cutoff=int(cfg['case'].split('_')[-1]);sr=summary[(summary['sample']==cfg['sample'])&(summary.threshold==cutoff)].iloc[0]
   j=int(np.flatnonzero(z['gamma']==1.2).item());exc=int((null['delta_bic'].min(axis=1)<=rows.delta_bic.iloc[j]).sum())
   close(exc,sr.search_adjusted_exceedances,'Threshold exceedance');close((exc+1)/1001,sr.search_adjusted_p,'Threshold p')
  report.append({'case':key,'n':n,'observed_candidates':26,'null_candidates_replayed':recomputed})
  print('THRESHOLD_REPLAY',key,flush=True)
 need(len(report)==9,'Threshold model count')
 return report

def massloss():
 folder=ROOT/'analysis_data/legacy/mass_loss';ref=csv(ROOT/'paper/data/mass_loss_sensitivity.csv');report=[]
 for row in ref.itertuples():
  key=row.sample+'__'+row.case;a=load(folder/(key+'__matrices.npz'));X,y,k=a['X'],a['y'],a['m']
  # These are saved standardized response/history coordinates on each fitted population.
  b0,_,r,_=np.linalg.lstsq(X,y,rcond=1e-12);Z=np.c_[X,k];b1,_,rr,_=np.linalg.lstsq(Z,y,rcond=1e-12)
  e0=y-X@b0;e1=y-Z@b1;rss=e0@e0;rssf=e1@e1;tss=np.sum((y-y.mean())**2)
  norm=np.sum((k-X@np.linalg.lstsq(X,k,rcond=1e-12)[0])**2);se=np.sqrt(rssf/(len(y)-rr)/norm)
  out={'delta_r2':(rss-rssf)/tss,'partial_r2':1-rssf/rss,'delta_bic':len(y)*np.log(rssf/rss)+np.log(len(y)),
       'A_standardized':b1[-1],'SE_standardized':se,'b_native':b1[-1]*a['native_y'].std()/a['native_m'].std(),
       'SE_native':se*a['native_y'].std()/a['native_m'].std()}
  need(r==row.k_controls and rr==r+1 and len(y)==row.n,'Mass-loss rank/count')
  for k,v in out.items():close(v,getattr(row,k),'Mass-loss '+key+':'+k,1e-6 if k=='delta_bic' else 1e-8)
  report.append({'case':key,'n':len(y),'rank':int(r)})
 need(len(report)==27,'Mass-loss model count')
 return report

def spline_replay(full):
 folder=ROOT/'analysis_data/legacy/spline_crosscheck';ref=json.loads((folder/'REPLAY_SUMMARY.json').read_text());report=[];cache={}
 for row in ref:
  s,c,kind=row['sample'],row['case'],row['design'];key=s+'__'+c+'__'+kind
  z=load(folder/(key+'.npz'));a=load(ROOT/'analysis_data/populations'/(s+'__'+c+'__matrices.npz'));ids=a['ids'].astype('int64')
  need(np.array_equal(ids,z['ids']),'Spline identities')
  if s not in cache:
   f=csv(ROOT/'analysis_data/catalogues'/s/'feature.csv.gz');idc='tree_root_id' if s.startswith('bolshoip') else 'subhalo_id';f['id']=f[idc].astype('int64')
   f=f[f.tree_status=='ok'];h=csv(ROOT/'analysis_data/catalogues'/s/'formation.csv.gz');h['id']=h.halo_id.astype('int64')
   cache[s]=f.merge(h[['id']+spline.EPOCHS],on='id',validate='one_to_one',sort=False).set_index('id')
  d=cache[s].loc[ids].reset_index().copy();d['ell']=a['ell'];d['logm']=d.present_log_mass.astype(float) if s.startswith('bolshoip') else np.log10(d.present_mass_tree.astype(float));d['Yv']=np.log10(d.present_vmax_tree.astype(float))-d.logm/3
  ell=d.ell.to_numpy();knots=np.quantile(ell[ell>0],[.05,.35,.65,.95]);extra=[] if kind=='C4' else [ell]
  if kind=='spline':
   extra+=[(ell>0).astype(float)]+spline.rcs(ell,knots);close(knots,row['knots'],'Spline knots')
  fit=spline.fit(d,spline.gcol(row['gamma']),extra=extra)
  for k,v in fit.items():close(v,row[k],key+':'+k,1e-6 if k=='dBIC' else 1e-8)
  X=spline.controls(d,extra=extra);Q,r=spline.qr_basis(X);y=spline.zs(d.Yv);K=np.c_[[spline.zs(d[spline.gcol(g)]) for g in spline.GRID]].T
  yr=y-Q@(Q.T@y);E=K-Q@(Q.T@K);yy=yr@yr;n=len(y)
  observed=n*np.log(1-(E.T@yr)**2/(yy*(E*E).sum(0)))+np.log(n)
  close(observed,z['observed'],key+' observed grid',1e-6)
  j=spline.GRID.index(row['gamma']);need(z['null_minima'].shape==(10000,),'Spline null minima dimension')
  exc=int((z['null_minima']<=z['observed'][j]).sum());close(exc,row['exceedances'],'Spline exceedances');close((exc+1)/10001,row['p'],'Spline p');close(z['null_minima'].min(),row['null_min'],'Spline null extreme',1e-6)
  rng=np.random.default_rng(int(z['seed']));need(int(z['seed'])==row['seed'],'Spline seed');recomputed=0
  for b in range(10000):
   perm=rng.permutation(n)
   if full or b in (0,4999,9999):
    P=E[perm];Rr=P-Q@(Q.T@P);con=(Rr.T@yr)**2/(yy*(Rr*Rr).sum(0));calc=np.min(n*np.log(1-con)+np.log(n))
    close(calc,z['null_minima'][b],key+' archived minimum',1e-6);recomputed+=1
  report.append({'case':key,'n':n,'seed':row['seed'],'archived_minima_checked':10000,'minima_recomputed':recomputed})
  print('SPLINE_REPLAY',key,flush=True)
 need(len(report)==36,'Spline reference count')
 return report

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--full-nulls',action='store_true');args=p.parse_args();out=args.output.resolve()
 need(not out.exists(),'Output already exists')
 need(not out.is_relative_to(ROOT) or out.is_relative_to(ROOT/'outputs'),'In-repo output outside outputs')
 out.mkdir(parents=True,exist_ok=False);start=time.monotonic()
 def deny(*a,**k):raise RuntimeError('No network allowed in numerical replay')
 socket.socket.connect=deny;socket.create_connection=deny
 try:
  source=json.loads((ROOT/'provenance/legacy_source_map.json').read_text())
  for e in source['records']:
   path=ROOT/e['path'];need(path.stat().st_size==e['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==e['sha256'],'Legacy source checksum:'+e['path'])
  result={'formation':formation(args.full_nulls),'threshold':threshold(args.full_nulls),'mass_loss':massloss(),'spline_crosscheck':spline_replay(args.full_nulls)}
  result.update(status='PRESERVED_LEGACY_RESULTS_REPRODUCED',full_saved_null_replay=args.full_nulls,checks=N,maximum_absolute_difference=MAXERR,elapsed_seconds=time.monotonic()-start,python=sys.version.split()[0],numpy=np.__version__,pandas=pd.__version__,new_scientific_random_streams=0,raw_tree_scans=0,scientific_findings_closed=[])
  (out/'COMPLETION.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if not isinstance(v,list)},indent=2))
 except BaseException as e:
  (out/'FAILURE.json').write_text(json.dumps({'status':'HOLD','message':str(e),'traceback':traceback.format_exc(),'success_logbook_written':False},indent=2)+'\n');raise
if __name__=='__main__':main()
