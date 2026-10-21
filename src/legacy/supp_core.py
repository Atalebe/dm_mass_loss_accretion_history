"""Auditable one-regressor OLS increments and joint Smith-type gamma rescan.

Numerical implementation is independent of original111. The reference functions
are extracted without executing the original module or its I/O entrypoint.
"""
from __future__ import annotations
import ast, hashlib, io, json, math, os, stat, zipfile
from pathlib import Path, PurePosixPath
from dataclasses import dataclass
import numpy as np
import pandas as pd

class AuditError(RuntimeError):
    pass

def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)

def sha_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''): h.update(b)
    return h.hexdigest()

def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def save_json(path: Path, obj) -> None:
    def convert(x):
        if isinstance(x,np.generic): return x.item()
        if isinstance(x,np.ndarray): return x.tolist()
        raise TypeError(type(x).__name__)
    b=(json.dumps(obj,sort_keys=True,indent=2,allow_nan=False,default=convert)+'\n').encode()
    with path.open('xb') as f:
        f.write(b); f.flush(); os.fsync(f.fileno())

def gamma_column(g: float) -> str:
    return 'M_acc_gamma_'+str(float(g)).replace('.','p')

def case_seed(root: int, sample: str, case: str) -> int:
    text=f'DM-PAPER-SUPP-001|{root}|{sample}|{case}'
    return int.from_bytes(hashlib.sha256(text.encode()).digest()[:16],'little')

def array_hash(a: np.ndarray) -> str:
    return sha_bytes(np.asarray(a,dtype='<i8').tobytes(order='C'))

def check_grid(grid) -> np.ndarray:
    g=np.asarray(grid,dtype=float)
    require(g.ndim==1 and len(g)>0,'EMPTY_OR_INVALID_GRID')
    require(bool(np.all(np.isfinite(g)) and np.all(g>0)),'INVALID_GAMMA')
    require(len(set(g))==len(g),'DUPLICATE_GAMMA')
    return g

def original_namespace(path: Path, expected_sha: str) -> dict:
    b=path.read_bytes(); require(sha_bytes(b)==expected_sha,'ORIGINAL_SOURCE_HASH')
    tree=ast.parse(b.decode())
    const={'FORMATION_CONTROLS','VMAX_CANDIDATES','LOG_MASS_CANDIDATES',
           'MASS_LINEAR_CANDIDATES','ACC_CANDIDATES','MASS_BIN_CANDIDATES'}
    fn={'canonical_id','gamma_col','log10_positive','first_existing','resolve_feature_id',
        'standardize','add_yv_and_base_columns','design_matrix','ols','fit_increment','conditional_shuffle'}
    nodes=[]
    for node in tree.body:
        if isinstance(node,ast.FunctionDef) and node.name in fn: nodes.append(node)
        elif isinstance(node,ast.Assign) and all(isinstance(t,ast.Name) and t.id in const for t in node.targets):
            ast.literal_eval(node.value);nodes.append(node)
    require({n.name for n in nodes if isinstance(n,ast.FunctionDef)}==fn,'ORIGINAL_FUNCTION_SET')
    ns={'np':np,'pd':pd,'math':math}
    exec(compile(ast.Module(nodes,type_ignores=[]),str(path),'exec'),ns)
    return ns

class VerifiedArchive:
    def __init__(self,path: Path,expected_sha: str,expected_bytes: int):
        self.path=path
        require(path.is_file(),'MISSING_REPORT')
        require(path.stat().st_size==expected_bytes,'REPORT_LENGTH')
        require(sha_file(path)==expected_sha,'REPORT_SHA256')
        self.sha=expected_sha; self.z=zipfile.ZipFile(path)
        infos=self.z.infolist();names=[i.filename for i in infos]
        require(len(names)==len(set(names)),'DUPLICATE_ZIP_MEMBER')
        for i in infos:
            p=PurePosixPath(i.filename)
            require(not p.is_absolute() and '..' not in p.parts and '\\' not in i.filename,'UNSAFE_ZIP_PATH')
            require(not stat.S_ISLNK(i.external_attr>>16),'ZIP_SYMLINK')
            require(i.file_size<=600*1024**2,'ZIP_MEMBER_SIZE')
        self.manifest=json.loads(self.z.read('MANIFEST.json'))
        entries=self.manifest['files']; self.members={e['path']:e for e in entries}
        require(len(self.members)==len(entries),'DUPLICATE_MANIFEST_ENTRY')
        require(set(names)==set(self.members)|{'MANIFEST.json'},'ZIP_MANIFEST_COVERAGE')
        self.verified=[]
        for name,e in self.members.items():
            h=hashlib.sha256();length=0
            with self.z.open(name) as f:
                for b in iter(lambda:f.read(4*1024**2),b''):length+=len(b);h.update(b)
            require(length==e['bytes'] and h.hexdigest()==e['sha256'],f'MEMBER_HASH:{name}')
            self.verified.append({'path':name,'bytes':length,'sha256':h.hexdigest()})
    def read(self,name: str) -> bytes:
        require(name in self.members or name=='MANIFEST.json','UNADMITTED_MEMBER')
        require(self.z.getinfo(name).file_size<100*1024**2,'SMALL_READER_SIZE_LIMIT')
        b=self.z.read(name)
        if name in self.members:require(sha_bytes(b)==self.members[name]['sha256'],'MEMBER_CHANGED')
        return b
    def csv(self,name: str) -> pd.DataFrame:
        return pd.read_csv(io.BytesIO(self.read(name)),keep_default_na=False,na_values=[''])
    def close(self):self.z.close()

@dataclass
class Model:
    X: np.ndarray
    y: np.ndarray
    M: np.ndarray
    Q: np.ndarray
    ey: np.ndarray
    E: np.ndarray
    enorm: np.ndarray
    rss0: float
    tss: float
    sy: float
    sm: np.ndarray
    names: list[str]
    condition: float

    @property
    def n(self):return len(self.y)
    @property
    def k(self):return self.X.shape[1]

    @classmethod
    def from_frame(cls,df: pd.DataFrame,target: str,controls: list[str],memories: list[str],floor=1e-12):
        require(len(df)>0,'EMPTY_CASE')
        require(len(set(controls))==len(controls) and len(set(memories))==len(memories),'DUPLICATE_COLUMNS')
        require(set([target]+controls+memories)<=set(df.columns),'MISSING_MODEL_COLUMN')
        vals=df[[target]+controls+memories].apply(pd.to_numeric,errors='coerce')
        require(bool(np.isfinite(vals.to_numpy(float)).all()),'NONFINITE_CASE_DATA')
        yr=vals[target].to_numpy(float);mr=vals[memories].to_numpy(float)
        sy=float(np.std(yr,ddof=0));sm=np.std(mr,axis=0,ddof=0)
        require(sy>0 and bool(np.all(sm>0)),'CONSTANT_TARGET_OR_MEMORY')
        y=(yr-yr.mean())/sy;M=(mr-mr.mean(axis=0))/sm
        parts=[np.ones(len(df))];names=['intercept']
        for c in controls:
            v=vals[c].to_numpy(float);sd=float(v.std(ddof=0))
            if sd>0:parts.append((v-v.mean())/sd);names.append(c)
        X=np.column_stack(parts)
        require(len(df)>X.shape[1]+1,'INSUFFICIENT_DOF')
        singular=np.linalg.svd(X,compute_uv=False)
        require(singular[-1]/singular[0]>floor,'RANK_DEFICIENT_CONTROLS')
        Q=np.linalg.qr(X,mode='reduced')[0]
        ey=y-Q@(Q.T@y);E=M-Q@(Q.T@M)
        enorm=np.einsum('ij,ij->j',E,E);rss0=float(ey@ey);tss=float((y-y.mean())@(y-y.mean()))
        require(rss0>floor*tss,'ZERO_CONTROL_RESIDUAL')
        require(bool(np.all(enorm>floor*len(df))),'DEGENERATE_HISTORY_AFTER_CONTROLS')
        return cls(X,y,M,Q,ey,E,enorm,rss0,tss,sy,sm,names,float(singular[0]/singular[-1]))

    def stats(self,score: np.ndarray,norm: np.ndarray) -> dict[str,np.ndarray]:
        require(bool(np.all(np.isfinite(score)) and np.all(np.isfinite(norm))),'NONFINITE_SCORE')
        require(bool(np.all(norm>1e-12*self.n)),'DEGENERATE_PERMUTED_HISTORY')
        reduction=score**2/norm
        require(bool(np.all(reduction>=0) and np.all(reduction<self.rss0)),'INVALID_RSS_REDUCTION')
        residual=self.rss0-reduction
        beta=score/norm
        se=np.sqrt(residual/(self.n-self.k-1)/norm)
        return {'delta_bic':self.n*np.log1p(-reduction/self.rss0)+np.log(self.n),
                'delta_r2':reduction/self.tss,'partial_r2':reduction/self.rss0,
                'A_standardized':beta,'SE_standardized':se,'t':beta/se,
                'b_native':beta*self.sy/self.sm,'SE_native':se*self.sy/self.sm,
                'r2_controls':np.full(len(score),1-self.rss0/self.tss),
                'residual_K_variance_fraction':norm/self.n}
    def observed(self):return self.stats(self.ey@self.E,self.enorm)
    def permuted(self,perm: np.ndarray):
        perm=np.asarray(perm)
        require(perm.shape==(self.n,) and np.issubdtype(perm.dtype,np.integer),'INVALID_PERM_SHAPE')
        require(np.array_equal(np.sort(perm),np.arange(self.n)),'NONBIJECTIVE_PERMUTATION')
        Z=self.E[perm,:]
        projected=self.Q.T@Z
        norm=self.enorm-np.einsum('ij,ij->j',projected,projected)
        return self.stats(self.ey@Z,norm)

def empirical_p(null,observed):
    a=np.asarray(null,dtype=float)
    require(a.ndim==1 and len(a)>0 and bool(np.isfinite(a).all()) and math.isfinite(float(observed)),'INVALID_NULL_STATISTICS')
    b=int(np.count_nonzero(a<=observed))
    return {'exceedances':b,'B':len(a),'p':(b+1)/(len(a)+1)}

def summarize_null(dbic: np.ndarray,observed: np.ndarray,grid,frozen_gamma,secondary_grid):
    grid=check_grid(grid);secondary=check_grid(secondary_grid)
    require(dbic.ndim==2 and dbic.shape[1]==len(grid) and len(observed)==len(grid),'NULL_GRID_SHAPE')
    require(bool(np.isfinite(dbic).all() and np.isfinite(observed).all()),'NONFINITE_NULL_MATRIX')
    f=np.flatnonzero(grid==frozen_gamma);require(len(f)==1,'FROZEN_GAMMA_ABSENT')
    require(set(secondary)<=set(grid),'SECONDARY_GRID_NOT_SUBSET')
    out={}
    for name,indices in [('full26',np.arange(len(grid))),('published6',np.array([int(np.where(grid==g)[0][0]) for g in secondary]))]:
        null=dbic[:,indices].min(axis=1);winner=int(indices[np.argmin(observed[indices])])
        out[name]={'observed_min_delta_bic':float(observed[winner]),'observed_argmin_gamma':float(grid[winner]),
          'historical_gamma_delta_bic':float(observed[f[0]]),
          'minimum_against_joint_null':empirical_p(null,observed[winner]),
          'historical_against_joint_null':empirical_p(null,observed[f[0]]),
          'null_min':float(null.min()),'null_q01':float(np.quantile(null,.01)),
          'null_median':float(np.median(null)),'null_q99':float(np.quantile(null,.99))}
    out['historical_pointwise']=empirical_p(dbic[:,f[0]],observed[f[0]])
    return out

def assert_close(a,b,field='value',atol=1e-8,rtol=1e-8):
    require(bool(np.allclose(a,b,atol=atol,rtol=rtol,equal_nan=False)),f'ORACLE_MISMATCH:{field};max_abs={np.max(np.abs(np.asarray(a)-np.asarray(b)))}')

def canonical_series(series: pd.Series,ns) -> pd.Series:
    out=series.map(ns['canonical_id'])
    require(out.notna().all() and not out.duplicated().any(),'DUPLICATE_OR_MISSING_ID')
    require(bool(out.map(lambda x:x.isdigit()).all()),'INVALID_OBJECT_ID')
    return out

def load_case_frames(archive: VerifiedArchive,sample: str,plan: dict,ns):
    raw=archive.csv(f'catalogues/{sample}/feature.csv')
    require('tree_status' in raw,'MISSING_TREE_STATUS')
    f=raw[raw.tree_status=='ok'].copy()
    require(len(f)==plan['expected_full_counts'][sample],'FEATURE_COUNT')
    f['_join_id']=canonical_series(f[ns['resolve_feature_id'](f)],ns)
    f,prov,controls=ns['add_yv_and_base_columns'](f,sample,8)
    require(prov['mass_bin_policy'].startswith('existing_column:'),'NO_FALLBACK_BINNING')
    formation=archive.csv(f'catalogues/{sample}/formation.csv')
    formation['_join_id']=canonical_series(formation['halo_id'],ns)
    require(set(f._join_id)==set(formation._join_id),'FORMATION_ID_SET')
    merged=f.merge(formation,on='_join_id',how='inner',validate='one_to_one',suffixes=('','_formation'),sort=False)
    target='target_yv_log_vmax_mass_scaled';c4=controls+['a10','a25','a50','a75']
    mem=[gamma_column(g) for g in plan['gamma_grid']]
    frozen=gamma_column(plan['historical_gamma'][sample])
    required=[target]+c4+[frozen]
    finite=np.isfinite(merged[required].apply(pd.to_numeric,errors='coerce').to_numpy(float)).all(axis=1)
    full=merged.loc[finite].copy()
    require(len(full)==plan['expected_complete_counts'][sample],'COMPLETE_CASE_COUNT')
    require(set(mem)<=set(full.columns),'MISSING_GRID_COLUMNS')
    require(np.isfinite(full[mem].to_numpy(float)).all(),'GAMMA_DEPENDENT_MISSINGNESS')
    pop=archive.csv(f'population_{sample}.csv');pop['_join_id']=canonical_series(pop.object_id,ns)
    require(set(pop._join_id)==set(merged._join_id),'POPULATION_ID_SET')
    pids=set(pop.loc[pop.formation_fit_eligible==1,'_join_id'])
    require(pids==set(full._join_id),'POPULATION_FIT_ID_SET')
    frames={'full_C4':(full,c4)}
    if sample.startswith('tng_'):
        flags=pd.to_numeric(full.primary_flag_api,errors='coerce')
        require(flags.isin([0,1]).all(),'UNKNOWN_CENTRAL_FLAG')
        flags_byid=pop.set_index('_join_id')['primary_flag_api'].astype(float)
        require(np.array_equal(flags.to_numpy(),flags_byid.loc[full._join_id].to_numpy()),'CENTRAL_FLAG_PROVENANCE')
        central=full.loc[flags==1].copy()
        require(len(central)==plan['expected_central_counts'][sample],'CENTRAL_COUNT')
        frames['centrals_C4']=(central,c4)
        ext=archive.csv(f'catalogues/{sample}/extended.csv');ext['_join_id']=canonical_series(ext.halo_id,ns)
        require(set(ext._join_id)==set(f._join_id),'EXTENDED_ID_SET')
        check=merged[['_join_id','a10','a25','a50','a75']].merge(ext[['_join_id','a10','a25','a50','a75']],on='_join_id',suffixes=('_old','_copy'),validate='one_to_one')
        for c in ['a10','a25','a50','a75']:
            a=check[c+'_old'].to_numpy(float);b=check[c+'_copy'].to_numpy(float)
            require(np.array_equal(np.isnan(a),np.isnan(b)),'COPIED_FORMATION_MISSINGNESS')
            require(np.allclose(a,b,atol=1e-10,rtol=0,equal_nan=True),'COPIED_FORMATION_VALUES')
        extended=full.merge(ext[['_join_id','a05','a90']],on='_join_id',validate='one_to_one',sort=False)
        keep=np.isfinite(extended[['a05','a90']].to_numpy(float)).all(axis=1)
        extended=extended.loc[keep].copy()
        require(len(extended)==plan['expected_extended_counts'][sample],'EXTENDED_COUNT')
        frames['extended_C6']=(extended,c4+['a05','a90'])
        frames['extended_matched_C4']=(extended,c4)
    return frames,prov,merged
