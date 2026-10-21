"""Offline replay of released numerical inputs, with new output directories only.

The default checks observed fits, spatial deletions and saved-null summaries,
plus three recalculated permutations per design. --full-nulls recalculates
all saved draws. No science service, development checkout or API key is used.
"""
from __future__ import annotations
import os
for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[name] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import argparse, datetime, hashlib, json, socket, sys, time, traceback
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
from verify_integrity import ROOT, verify
sys.path.insert(0, str(ROOT/'src'))
from core import Model, design, standardize, original_ols_functions, oracle
from sensitivity import increment, poststratification

DATA = ROOT/'analysis_data'
PAPER = ROOT/'paper/data'
CHECKS = 0
MAX_ERROR = 0.0

def need(ok, message):
    global CHECKS
    CHECKS += 1
    if not bool(ok):
        raise RuntimeError(message)

def same(a, b, label, bic=False):
    global CHECKS, MAX_ERROR
    a, b = np.asarray(a, float), np.asarray(b, float)
    need(a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all(), 'Nonfinite/shape: '+label)
    error = float(np.max(np.abs(a-b))) if a.size else 0.0
    MAX_ERROR = max(MAX_ERROR, error)
    need(np.allclose(a,b,atol=1e-6 if bic else 1e-8,rtol=1e-8), 'Numerical mismatch: '+label+': '+str(error))
    CHECKS += a.size

def table(path, **kwargs):
    return pd.read_csv(path, float_precision='round_trip', **kwargs)

def arrays(path):
    with np.load(path, allow_pickle=False) as z:
        return {k:z[k].copy() for k in z.files}

def save(path, obj):
    with Path(path).open('x') as f:
        json.dump(obj,f,indent=2,sort_keys=True,allow_nan=False)
        f.write('\n')

def no_network(*args, **kwargs):
    raise RuntimeError('Numerical reproduction does not access the network')

def catalogue_design(sample, a):
    """Rebuild the four-epoch design from the released per-object CSVs."""
    folder=DATA/'catalogues'/sample
    idcol='subhalo_id' if sample.startswith('tng_') else 'tree_root_id'
    f=table(folder/'feature.csv.gz',dtype={idcol:str}).set_index(idcol,verify_integrity=True)
    h=table(folder/'formation.csv.gz',dtype={'halo_id':str}).set_index('halo_id',verify_integrity=True)
    ids=a['ids'].astype(str)
    need(len(set(ids))==len(ids), 'Duplicate matrix IDs')
    d=f.loc[ids]; epochs=h.loc[ids,['a10','a25','a50','a75']].to_numpy(float)
    lm=np.log10(d.present_mass_tree.to_numpy(float)) if sample.startswith('tng_') else d.present_log_mass.to_numpy(float)
    lv=np.log10(d.present_vmax_tree.to_numpy(float))
    same(lm,a['logmass'],'catalogue logmass');same(lv,a['logV'],'catalogue logV')
    same(lv-lm/3,a['y'],'catalogue target')
    bins=d.mass_bin.astype(str).to_numpy()
    need(np.array_equal(bins,a['mass_bins'].astype(str)), 'Mass-bin identity')
    mass=standardize(lm)[0]
    columns=[mass,mass**2,mass**3,d.present_acc_rate.to_numpy(float)]
    levels=sorted(set(bins))
    columns += [(bins==level).astype(float) for level in levels[1:]]
    columns += [epochs[:,j] for j in range(4)]
    C=np.column_stack([np.ones(len(ids))]+[standardize(x)[0] for x in columns])
    same(C,a['C'],'reconstructed four-epoch design')
    return f

def search_replay(out, full):
    summary=table(DATA/'search/SUMMARY.csv')
    reference=table(PAPER/'continuous_logL_summary.csv').set_index(['sample','case'])
    need(len(summary)==30,'Expected 30 loss designs')
    fields=['delta_bic','delta_r2','partial_r2','A_standardized','SE_standardized','b_native','SE_native','t','residual_K_variance_fraction']
    populations=set(); observed_count=0; null_count=0; permutation_digests=0
    ols=original_ols_functions((ROOT/'reference/original_ols.py').read_text())
    reports=[]
    for _,row in summary.iterrows():
        sample,case,kind=row['sample'],row['case'],row['design']
        tag=sample+'__'+case+'__'+kind; folder=DATA/'search'/tag
        z=arrays(folder/'matrices.npz'); cfg=json.loads((folder/'DESIGN.json').read_text())
        need(len(z['ids'])==row['n'] and len(set(z['ids']))==len(z['ids']),'Object count')
        need(hashlib.sha256(('\n'.join(z['ids'])+'\n').encode()).hexdigest()==cfg['ordered_ids_sha256'],'ID digest')
        same(design(z['C4'],z['ell'],kind),z['X'],'loss design')
        m=Model(z['X'],z['y_native'],z['K_native'])
        same(m.M,z['M'],'standardized history');same(m.y,z['y'],'standardized target')
        need(m.p==int(row['k_controls']),'Control rank')
        expected=table(folder/'observed_all_gamma.csv'); actual=m.observed()
        for field in fields:same(actual[field],expected[field].to_numpy(),tag+': '+field,bic=field=='delta_bic')
        oracle(m,m.M,actual,ols)
        observed_count+=len(z['gamma'])
        j=int(np.flatnonzero(z['gamma']==float(row['gamma'])).item())
        for field in fields:same(actual[field][j],row[field],'fiducial '+field,bic=field=='delta_bic')
        if (sample,case) not in populations:
            a=arrays(DATA/'populations'/(sample+'__'+case+'__matrices.npz'))
            catalogue_design(sample,a)
            need(np.array_equal(a['ids'],z['ids']),'Population ordered IDs')
            same(a['ell'],z['ell'],'stored log loss')
            base=Model(a['C'],a['y'],a['K'][:,None]);s=base.observed();old=reference.loc[(sample,case)]
            for field in fields:same(s[field][0],old[field+'_before'],'four-epoch reference '+field,bic=field=='delta_bic')
            if case=='centrals_C4':
                f=table(DATA/'catalogues'/sample/'feature.csv.gz',dtype={'subhalo_id':str}).set_index('subhalo_id')
                need(np.all(f.loc[a['ids'],'primary_flag_api'].to_numpy()==1),'Central-only selection')
            if case.startswith('Qpeak_ge'):
                cutoff=int(case.split('ge')[1]);need(np.all(.1*10**a['logmaximum']/1.55e8>=cutoff),'Threshold selection')
            populations.add((sample,case))
        null=arrays(folder/'null_all_gamma.npz'); stream=table(folder/'permutations.csv')
        need(null['delta_bic'].shape==(1000,26) and null['A_standardized'].shape==(1000,26),'Saved null shape')
        need(np.isfinite(null['delta_bic']).all() and np.isfinite(null['A_standardized']).all(),'Saved null finite')
        minima=null['delta_bic'].min(axis=1)
        same(minima,stream.minimum_delta_bic.to_numpy(),'all saved minima',bic=True)
        same(z['gamma'][null['delta_bic'].argmin(axis=1)],stream.argmin_gamma.to_numpy(),'all null argmins')
        candidates=table(folder/'candidate_search_comparisons.csv')
        for jj,g in enumerate(z['gamma']):
            e=int(np.count_nonzero(minima<=expected.delta_bic.iloc[jj]))
            need(e==candidates.exceedances.iloc[jj],'Candidate exceedance count')
            same((e+1)/1001,candidates.p_search.iloc[jj],'Candidate tail')
        fid_e=int(np.count_nonzero(minima<=expected.delta_bic.iloc[j]));min_e=int(np.count_nonzero(minima<=expected.delta_bic.min()))
        need(fid_e==row.exceedances and min_e==row.gridmin_exceedances,'Summary exceedances')
        same((fid_e+1)/1001,row.p_search,'fiducial p');same((min_e+1)/1001,row.gridmin_p_search,'grid p')
        spec=json.loads((folder/'RNG_SPEC.json').read_text());rng=np.random.Generator(np.random.PCG64(spec['seed']))
        need(rng.bit_generator.state==json.loads((folder/'RNG_INITIAL.json').read_text()),'Initial random state')
        for b in range(1000):
            idx=rng.permutation(m.n)
            need(hashlib.sha256(np.asarray(idx,dtype='<i8').tobytes()).hexdigest()==stream.permutation_sha256.iloc[b],'Permutation-index digest')
            permutation_digests+=1
            if full or b in (0,499,999):
                st=m.permuted(idx)
                same(st['delta_bic'],null['delta_bic'][b],'replayed null BIC',bic=True)
                same(st['A_standardized'],null['A_standardized'][b],'replayed null coefficient')
                null_count+=26
        need(rng.bit_generator.state==json.loads((folder/'RNG_FINAL.json').read_text()),'Final random state')
        reports.append({'case':tag,'n':m.n,'control_rank':m.p,'observed_candidates':26,'null_candidates_recomputed':26000 if full else 78})
        print('SEARCH_REPLAY',tag,flush=True)
    p=summary.p_search.to_numpy()
    same(np.minimum(1,30*p),summary.p_bonferroni30.to_numpy(),'Bonferroni30')
    for values,expected,label in [(p,summary.p_holm30.to_numpy(),'Holm30'),
        (np.r_[p,summary.gridmin_p_search.to_numpy()],np.r_[summary.p_holm60_primary.to_numpy(),summary.p_holm60_gridmin.to_numpy()],'Holm60')]:
        order=np.argsort(values,kind='stable');adjusted=np.minimum(1,np.maximum.accumulate(values[order]*np.arange(len(values),0,-1)))
        same(adjusted,expected[order],label)
    report={'designs':len(reports),'populations':len(populations),'observed_candidates':observed_count,'random_permutation_digests':permutation_digests,'null_candidates_recomputed':null_count,'saved_candidate_nulls_checked_for_minima_and_counts':780000,'cases':reports}
    save(out/'search_replay.json',report)
    return report

def spatial_replay(out):
    folder=DATA/'spatial';t=table(folder/'spatial_delete_region_fits.csv');s=table(folder/'spatial_summary.csv')
    geom={a['sample']:a for a in json.loads((folder/'GEOMETRY.json').read_text())}
    need(len(t)==945 and len(s)==54,'Spatial dimensions')
    done=0;rankloss=0
    for (sample,case,kind),df in t.groupby(['sample','case','design'],sort=False):
        selected='linear' if kind=='C4' else kind
        a=arrays(DATA/'search'/f'{sample}__{case}__{selected}'/'matrices.npz')
        C=a['C4'] if kind=='C4' else a['X'];y=a['y_native'];j=int(np.flatnonzero(a['gamma']==float(df.gamma.iloc[0])).item())
        k=a['M'][:,j];sk=float(a['sm'][j]);sy=float(a['sy']);ids=a['ids'].astype(str)
        coords=table(folder/f'{sample}__coordinates.csv.gz',dtype={'object_id':str}).set_index('object_id',verify_integrity=True).loc[ids,['x','y','z']].to_numpy()
        lo=np.asarray(geom[sample]['lo']);hi=np.asarray(geom[sample]['hi'])
        for q in (2,3):
            grid=np.empty(coords.shape,int)
            for axis in range(3):grid[:,axis]=np.searchsorted(np.linspace(lo[axis],hi[axis],q+1)[1:-1],coords[:,axis],side='right')
            labels=(grid[:,0]*q+grid[:,1])*q+grid[:,2]
            membership=table(folder/f'{sample}__{case}__q{q}_membership.csv.gz',dtype={'object_id':str})
            need(np.array_equal(ids,membership.object_id.to_numpy()) and np.array_equal(labels,membership.region.to_numpy()),'Spatial membership')
            occupancy=json.loads((folder/f'{sample}__{case}__q{q}_occupancy.json').read_text())
            need(np.array_equal(np.bincount(labels,minlength=q**3),occupancy['counts']),'Region counts')
            rows=df[df.q==q]
            need(len(rows)==q**3 and set(rows.region)==set(labels),'Region set')
            for row in rows.itertuples():
                keep=labels!=row.region
                need(int((~keep).sum())==row.n_removed,'Removal count')
                need(hashlib.sha256(('\n'.join(ids[~keep])+'\n').encode()).hexdigest()==row.deleted_id_sha256,'Deleted identity')
                x=C[keep]; yy=y[keep]; kk=k[keep]
                coef,_,rank,_=np.linalg.lstsq(x,np.c_[yy,kk],rcond=1e-12)
                ry,rk=(np.c_[yy,kk]-x@coef).T
                beta=(rk@ry)/(rk@rk);e=ry-beta*rk;rss=float(ry@ry);rssf=float(e@e);tss=float(np.sum((yy-yy.mean())**2))
                vals={'b_native':beta/sk,'A_fixed':beta/sy,'delta_r2':(rss-rssf)/tss,'partial_r2':(rss-rssf)/rss,'delta_bic':len(yy)*np.log(rssf/rss)+np.log(len(yy))}
                for key,value in vals.items():same(value,getattr(row,key),'spatial '+key,bic=key=='delta_bic')
                need(rank==row.k_controls,'Deletion rank');rankloss+=int(rank<C.shape[1]);done+=1
            ref=s[(s['sample']==sample)&(s['case']==case)&(s.design==kind)&(s.q==q)].iloc[0]
            b=rows.b_native.to_numpy();scale=np.sqrt((len(b)-1)/len(b)*np.sum((b-b.mean())**2))
            for name,value in [('b_min',b.min()),('b_max',b.max()),('jackknife_dispersion_native',scale),('n_nonnegative',(b>=0).sum()),('delta_r2_min',rows.delta_r2.min()),('delta_r2_max',rows.delta_r2.max())]:same(ref[name],value,'Spatial summary '+name)
        print('SPATIAL_REPLAY',sample,case,kind,flush=True)
    report={'deletion_fits':done,'summaries':len(s),'nuisance_rank_reductions':rankloss,'new_spatial_probabilities':0}
    save(out/'spatial_replay.json',report)
    return report

def weighting_replay(out):
    reference=table(PAPER/'mass_reweight_summary.csv');binref=table(PAPER/'mass_bin_weights.csv');reports=[]
    for sample in sorted(reference['sample'].unique()):
        a=arrays(DATA/'populations'/f'{sample}__baseline__matrices.npz')
        parent=table(DATA/'catalogues'/sample/'feature.csv.gz')
        weights,counts=poststratification(parent.mass_bin.astype(str).to_numpy(),a['mass_bins'])
        br=binref[binref['sample']==sample].set_index('mass_bin')
        for c in counts:
            need(c['n_available']==br.loc[c['mass_bin'],'n_available'] and c['n_complete']==br.loc[c['mass_bin'],'n_complete'],'Poststratum counts')
            same(c['weight'],br.loc[c['mass_bin'],'weight'],'Poststratum weight')
        kz=standardize(a['K'])[0];sk=float(a['K'].std());sy=float(a['y'].std())
        for kind,C in [('C4',a['C']),('linear',design(a['C'],a['ell'],'linear')),('indicator_quadratic',design(a['C'],a['ell'],'indicator_quadratic'))]:
            row=reference[(reference['sample']==sample)&(reference.design==kind)].iloc[0]
            for suffix,w in [('unweighted',None),('weighted',weights)]:
                result=increment(C,kz,a['y'],sk,sy,w,oracle=True)
                for name in ['n','k_controls','k_full','b_native','A_fixed','A_local','delta_r2','partial_r2','r2_controls']:
                    same(result[name],row[name+'_'+suffix],'WLS '+name)
            reports.append({'sample':sample,'design':kind,'n':len(a['y']),'available_count':len(parent)})
    save(out/'mass_reweight_replay.json',{'weighted_fits':len(reports),'cases':reports})
    return len(reports)

def nominal_references(out):
    r=table(PAPER/'DM_Spatial_Nominal_t_Reference.csv');base=table(DATA/'spatial/spatial_summary.csv')
    need(len(r)==len(base)==54,'Nominal table length')
    for _,row in r.iterrows():
        src=base[(base['sample']==row['sample'])&(base['case']==row['case'])&(base.design==row.design)&(base.q==row.q)]
        need(len(src)==1,'Nominal source match');src=src.iloc[0]
        same(row.full_b,src.full_b,'Nominal b');same(row.jackknife_dispersion_native,src.jackknife_dispersion_native,'Nominal scale')
        df=int(row.regions)-1;t=row.full_b/row.jackknife_dispersion_native;q=stats.t.ppf(.975,df)
        same(t,row.t_reference,'Nominal t');same(2*stats.t.sf(abs(t),df),row.p_two_sided_nominal,'Nominal probability')
        same(row.full_b-q*row.jackknife_dispersion_native,row.nominal_95_low,'Nominal lower');same(row.full_b+q*row.jackknife_dispersion_native,row.nominal_95_high,'Nominal upper')
    cube=table(PAPER/'DM_BolshoiP_Cube_Compatibility.csv')
    for _,row in cube.iterrows():
        d=base[(base['sample'].str.startswith('bolshoip'))&(base.design==row.design)&(base.q==2)].sort_values('sample')
        b=d.full_b.to_numpy();se=d.OLS_SE_native.to_numpy();w=1/se**2;mu=np.dot(w,b)/w.sum();Q=np.dot(w,(b-mu)**2)
        same(b,np.array([row.b_I,row.b_II,row.b_III]),'Cube coefficients')
        same(np.std(b,ddof=1),row.between_cube_sample_sd,'Cube spread');same(Q,row.Q_OLS_variance_reference,'Cube Q');same(np.exp(-Q/2),row.p_chi2_nominal,'Cube nominal p')
    save(out/'nominal_reference_replay.json',{'nominal_rows':54,'cube_rows':3,'spatial_calibration_established':False})

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--full-nulls',action='store_true',help='Recompute all saved 30,000 permutations, not a new random stream')
    args=parser.parse_args();out=args.output.resolve()
    if out.is_relative_to(ROOT.resolve()):
        need(out.is_relative_to((ROOT/'outputs').resolve()),'In-repository outputs must be under outputs/')
    need(not out.exists(),'Output exists; refusing overwrite')
    before=verify();out.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    socket.create_connection=no_network;socket.socket.connect=no_network;socket.socket.connect_ex=no_network
    try:
        search=search_replay(out,args.full_nulls)
        spatial=spatial_replay(out)
        weighted=weighting_replay(out)
        nominal_references(out)
        after=verify();need(before==after,'Input payload changed')
        report={'status':'REPRODUCTION_VERIFIED','mode':'full_saved_null_replay' if args.full_nulls else 'observed_and_selected_null_replay',
            'search':{k:v for k,v in search.items() if k!='cases'},'spatial':spatial,'weighted_fits':weighted,
            'nominal_references':54,'cube_references':3,'checks':int(CHECKS),'maximum_absolute_comparison_difference':MAX_ERROR,
            'elapsed_seconds':time.monotonic()-start,'python':sys.version.split()[0],'numpy':np.__version__,'pandas':pd.__version__,
            'new_simulations':0,'new_scientific_settings':False,'source_inputs_unchanged':True,
            'completed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
        save(out/'COMPLETION.json',report)
        print(json.dumps(report,indent=2));print('OUTPUT_DIRECTORY='+str(out))
    except BaseException as exc:
        save(out/'FAILURE.json',{'status':'HOLD','error':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc(),'success_logbook_written':False})
        raise
if __name__=='__main__':
    try:main()
    except Exception:
        traceback.print_exc();sys.exit(2)
