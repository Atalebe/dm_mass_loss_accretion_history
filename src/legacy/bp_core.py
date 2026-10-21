"""BolshoiP threshold selection and bracketing diagnostics; no scientific I/O on import."""
from __future__ import annotations
import ast, gzip, hashlib, io, json, math
from pathlib import Path
import numpy as np
import pandas as pd
from supp_core import (AuditError, require, sha_bytes, sha_file, save_json, Model,
                       assert_close, canonical_series, gamma_column)

TARGET = 'target_yv_log_vmax_mass_scaled'
EPOCHS = ['a10','a25','a50','a75']

def stream_seed(root: int, sample: str, threshold: int) -> int:
    require(threshold in [20,50], 'UNDECLARED_THRESHOLD')
    text=f'DM-PAPER-SUPP-002|{root}|{sample}|Q10_ge_{threshold}'
    return int.from_bytes(hashlib.sha256(text.encode()).digest()[:16], 'little')

def threshold_mask(values, threshold):
    require(threshold in [20,50], 'UNDECLARED_THRESHOLD')
    q=np.asarray(values,dtype=float)
    require(q.ndim==1 and len(q)>0 and np.isfinite(q).all() and np.all(q>0), 'INVALID_Q10')
    return q>=threshold

def rebased_frame(frame, sample, ns):
    # The same full cubic and categorical model span; only its basis is regenerated.
    remove=[c for c in frame.columns if c.startswith('mass_bin_fe_') or c in ['mass_z','mass_z2','mass_z3',TARGET]]
    raw=frame.drop(columns=remove).copy()
    require('mass_bin' in raw and raw.mass_bin.notna().all(), 'MISSING_HISTORICAL_MASS_BIN')
    out,prov,controls=ns['add_yv_and_base_columns'](raw,sample,8)
    require(prov['mass_bin_policy']=='existing_column:mass_bin','UNAUTHORIZED_BINNING')
    require(np.array_equal(frame._join_id.to_numpy(),out._join_id.to_numpy()),'REBASE_ID_ORDER')
    require(np.array_equal(frame.mass_bin.astype(str),out.mass_bin.astype(str)),'BIN_LABEL_CHANGE')
    return out,controls+EPOCHS,prov

def original_crossing_namespace(path, expected):
    b=Path(path).read_bytes();require(sha_bytes(b)==expected,'SOURCE96_HASH')
    t=ast.parse(b);n=[x for x in t.body if isinstance(x,ast.FunctionDef) and x.name=='crossing_scale']
    require(len(n)==1,'SOURCE96_FUNCTION')
    ns={'np':np,'math':math}
    exec(compile(ast.Module(n,type_ignores=[]),str(path),'exec'),ns)
    return ns

def bracket_diagnostic(a,m,phantom,mp):
    """Mass equivalents at actual raw nodes and cumulative-max crossing coordinates.
    Reproduces source96's filter/sort/first-duplicate policy, not a new estimator.
    """
    a=np.asarray(a,float);m=np.asarray(m,float);ph=np.asarray(phantom,float)
    require(a.ndim==1 and a.shape==m.shape==ph.shape,'BRACKET_SHAPES')
    require(math.isfinite(mp) and mp>0,'PARTICLE_MASS')
    ok=np.isfinite(a)&np.isfinite(m)&(a>0)&(m>0)
    a,m,ph=a[ok],m[ok],ph[ok]
    require(len(a)>=2,'SHORT_CHAIN')
    order=np.argsort(a);a,m,ph=a[order],m[order],ph[order]
    unique,ii=np.unique(a,return_index=True);a,m,ph=unique,m[ii],ph[ii]
    require(len(a)>=2,'SHORT_UNIQUE_CHAIN')
    track=np.maximum.accumulate(m);maximum=float(track[-1]);target=.1*maximum
    indices=np.flatnonzero(track>=target);require(len(indices)>0,'NO_MAXIMUM_CROSSING')
    hi=int(indices[0]);lo=hi-1
    result={'max_recorded_mass_native':maximum,'Q10':target/mp,'admitted_nodes':len(a),
            'first_admitted_mass_native':float(m[0]),'first_admitted_a':float(a[0]),
            'phantom_nodes':int(np.count_nonzero(ph>0)),
            'lower_a':None,'upper_a':None,'delta_a':None,'delta_ln_a':None,
            'lower_node_mass_equiv':None,'upper_node_mass_equiv':None,
            'lower_running_mass_equiv':None,'upper_running_mass_equiv':None,
            'lower_phantom':None,'upper_phantom':None,'interpolation_weight':None,
            'a10_reconstructed':None}
    if hi==0:
        if np.isclose(track[0],target,rtol=1e-10,atol=0):
            result.update(status='ok_initial_exact',upper_a=float(a[0]),upper_node_mass_equiv=float(m[0]/mp),
                          upper_running_mass_equiv=float(track[0]/mp),upper_phantom=bool(ph[0]>0),a10_reconstructed=float(a[0]))
        else:result['status']='left_censored'
        return result
    w=(math.log(target)-math.log(float(track[lo])))/(math.log(float(track[hi]))-math.log(float(track[lo])))
    w=min(1.,max(0.,w));result.update(status='ok',lower_a=float(a[lo]),upper_a=float(a[hi]),
        delta_a=float(a[hi]-a[lo]),delta_ln_a=math.log(float(a[hi]/a[lo])),
        lower_node_mass_equiv=float(m[lo]/mp),upper_node_mass_equiv=float(m[hi]/mp),
        lower_running_mass_equiv=float(track[lo]/mp),upper_running_mass_equiv=float(track[hi]/mp),
        lower_phantom=bool(ph[lo]>0),upper_phantom=bool(ph[hi]>0),interpolation_weight=w,
        a10_reconstructed=float(a[lo]+w*(a[hi]-a[lo])))
    return result

def grouped_chain_stream(archive,sample,chunksize=150000):
    """One pass with only a partial final group carried across chunk boundaries."""
    name=f'bolshoip_chains_{sample}.csv.gz'
    cols=['formation_key','formation_chain_index','scale','mvir','phantom']
    carry=None;seen=set()
    with archive.z.open(name) as raw, gzip.GzipFile(fileobj=raw) as gz:
        for chunk in pd.read_csv(gz,usecols=cols,dtype={'formation_key':str},chunksize=chunksize):
            if carry is not None:chunk=pd.concat([carry,chunk],ignore_index=True)
            # Input is grouped by root; refuse any repeated finished block.
            keys=chunk.formation_key.to_numpy();boundary=np.r_[0,np.flatnonzero(keys[1:]!=keys[:-1])+1,len(chunk)]
            for left,right in zip(boundary[:-2],boundary[1:-1]):
                key=str(keys[left]);require(key not in seen,'REPEATED_CHAIN_BLOCK:'+key);seen.add(key)
                yield key,chunk.iloc[left:right]
            carry=chunk.iloc[boundary[-2]:].copy()
        if carry is not None and len(carry):
            key=str(carry.formation_key.iloc[0]);require(key not in seen,'REPEATED_FINAL_CHAIN')
            yield key,carry

def audit_brackets(archive,sample,censor,formation,mp,ns96,out,progress):
    require(not censor.object_id.duplicated().any(),'DUPLICATE_CENSOR_ID')
    expected=censor.set_index('object_id');form=formation.set_index('_join_id')
    require(set(expected.index)==set(form.index),'BRACKET_EXPECTED_IDS')
    rows=[];seen=set();node_total=0;maxerr=0.;maxqerr=0.
    for key,frame in grouped_chain_stream(archive,sample):
        require(key in expected.index and key not in seen,'CHAIN_ID_SET');seen.add(key)
        node_total+=len(frame)
        vals=frame[['formation_chain_index','scale','mvir','phantom']].apply(pd.to_numeric,errors='coerce')
        vals=vals.loc[vals.formation_chain_index.notna()]
        vals=vals.sort_values('formation_chain_index')
        a=vals.scale.to_numpy(float);m=vals.mvir.to_numpy(float);ph=vals.phantom.to_numpy(float)
        d=bracket_diagnostic(a,m,ph,mp);old=expected.loc[key];f=form.loc[key]
        require(d['admitted_nodes']==int(f.n_history_points)==int(old.history_points),'ADMITTED_NODE_COUNT')
        assert_close(d['max_recorded_mass_native'],float(old.max_recorded_mass_native),'MAXIMUM_REFERENCE',atol=0,rtol=1e-12)
        assert_close(d['Q10'],float(old.N10_mass_equivalent),'Q10_REFERENCE',atol=1e-10,rtol=1e-12)
        maxqerr=max(maxqerr,abs(d['Q10']-float(old.N10_mass_equivalent)))
        for cut in [20,50]: require((d['Q10']>=cut)==(float(old.N10_mass_equivalent)>=cut),'THRESHOLD_PARSER_DISAGREEMENT')
        v,status=ns96['crossing_scale'](a,m,.1)
        require(status==str(f.a10_status)==d['status'],'CROSSING_STATUS')
        oldv=float(f.a10)
        require(math.isfinite(v)==math.isfinite(oldv)==(d['a10_reconstructed'] is not None),'CROSSING_MISSINGNESS')
        if math.isfinite(v):
            require(abs(v-oldv)<=1e-10 and abs(v-d['a10_reconstructed'])<=1e-10,'CROSSING_VALUE')
            maxerr=max(maxerr,abs(v-oldv),abs(v-d['a10_reconstructed']))
        rows.append({'sample':sample,'object_id':key,**d})
        if len(rows)%10000==0:progress('BRACKET_PROGRESS',sample=sample,objects=len(rows))
    require(seen==set(expected.index),'MISSING_CHAIN_ROOT')
    df=pd.DataFrame(rows)
    df.to_csv(out/f'brackets_{sample}.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    audit={'sample':sample,'objects':len(df),'node_rows':node_total,'maximum_a10_absolute_error':maxerr,
           'maximum_Q10_absolute_error':maxqerr,'threshold_membership_disagreements':0,'source96_replay':True}
    return df,audit

def finite_summary(values):
    v=np.asarray(values,dtype=float);v=v[np.isfinite(v)]
    if not len(v):return {'n':0,'min':None,'median':None,'max':None,'q10':None,'q90':None}
    return {'n':len(v),'min':float(v.min()),'median':float(np.median(v)),'max':float(v.max()),
            'q10':float(np.quantile(v,.1)),'q90':float(np.quantile(v,.9))}

def bracket_summary(brackets,ids,sample,threshold):
    b=brackets.set_index('object_id').loc[list(ids)]
    require(b.status.isin(['ok','ok_initial_exact']).all(),'UNDEFINED_SELECTED_BRACKET')
    res={'sample':sample,'threshold':threshold,'n':len(b),'two_node_brackets':int(b.lower_a.notna().sum()),
         'any_phantom_bracket':int((b.lower_phantom.fillna(False).astype(bool)|b.upper_phantom.fillna(False).astype(bool)).sum())}
    for c in ['lower_node_mass_equiv','upper_node_mass_equiv','lower_running_mass_equiv','upper_running_mass_equiv','delta_a','delta_ln_a','interpolation_weight']:
        res[c]=finite_summary(b[c])
    for cut in [20,50]:
        res[f'lower_node_below{cut}']=int((b.lower_node_mass_equiv<cut).sum())
        res[f'upper_node_below{cut}']=int((b.upper_node_mass_equiv<cut).sum())
    return res

def oracle_fits(frame,controls,memories,model,obs,ns):
    mapping={'delta_bic':'delta_bic_memory_vs_controls','delta_r2':'delta_r2_memory_vs_controls',
             'A_standardized':'A_memory_standardized','SE_standardized':'SE_memory_standardized','t':'t_memory'}
    errors={key:0. for key in mapping}
    for j,col in enumerate(memories):
        ref=ns['fit_increment'](frame,TARGET,col,controls)
        require(ref['n_model']==model.n and ref['k_controls']==model.k,'ORACLE_DESIGN')
        for key,name in mapping.items():
            assert_close(obs[key][j],ref[name],key,atol=1e-6 if key=='delta_bic' else 1e-8,rtol=1e-8)
            errors[key]=max(errors[key],abs(float(obs[key][j])-float(ref[name])))
        # Native slope checked by an independent full normalised-control OLS fit.
        nat=ns['ols'](frame[TARGET].to_numpy(float),np.column_stack([model.X,frame[col].to_numpy(float)]))
        assert_close(obs['b_native'][j],nat['beta'][-1],'NATIVE_BETA')
        assert_close(obs['SE_native'][j],nat['se'][-1],'NATIVE_SE')
    return {'original_candidate_fits':len(memories),'native_candidate_fits':len(memories),'max_errors':errors}

def oracle_permutation(model,perm,values,ns):
    base=ns['ols'](model.y,model.X);err=0.
    for j in range(model.M.shape[1]):
        v=model.M[:,j]-model.E[:,j]+model.E[perm,j]
        full=ns['ols'](model.y,np.column_stack([model.X,v]))
        assert_close(values['delta_bic'][j],full['bic']-base['bic'],'NULL_BIC',atol=1e-6)
        assert_close(values['delta_r2'][j],full['r2']-base['r2'],'NULL_R2')
        assert_close(values['A_standardized'][j],full['beta'][-1],'NULL_BETA')
        err=max(err,abs(float(values['delta_bic'][j])-(full['bic']-base['bic'])))
    return err
