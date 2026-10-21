"""Combined, offline reproduction in a fresh output directory; never installs packages."""
from pathlib import Path
import argparse,datetime,json,os,subprocess,sys,traceback
from verify_integrity import ROOT,verify
from verify_release_coverage import verify as coverage
from verify_legacy_import import verify as imported

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--output',type=Path,required=True)
 parser.add_argument('--full-nulls',action='store_true')
 args=parser.parse_args();out=args.output.resolve()
 if out.exists():raise RuntimeError('Output exists; refusing overwrite')
 if out.is_relative_to(ROOT.resolve()) and not out.is_relative_to((ROOT/'outputs').resolve()):raise RuntimeError('In-repository outputs must be under outputs/')
 before=verify();coverage();imported()
 out.mkdir(parents=True,exist_ok=False)
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
 jobs=[('tests',['-B','-m','unittest','discover','-s','tests','-v']),
       ('main',['-B','tools/reproduce.py','--output',str(out/'main')]),
       ('legacy',['-B','tools/replay_legacy.py','--output',str(out/'legacy')])]
 if args.full_nulls:
  jobs[1][1].append('--full-nulls');jobs[2][1].append('--full-nulls')
 try:
  for name,arguments in jobs:
   print('RUNNING='+name,flush=True)
   with (out/(name+'.log')).open('x') as log:
    p=subprocess.run([sys.executable,*arguments],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
   if p.returncode:raise RuntimeError(name+' failed; inspect its retained log')
  primary=json.loads((out/'main/COMPLETION.json').read_text())
  legacy=json.loads((out/'legacy/COMPLETION.json').read_text())
  if primary['status']!='REPRODUCTION_VERIFIED' or legacy['status']!='PRESERVED_LEGACY_RESULTS_REPRODUCED':raise RuntimeError('Child did not produce successful completion')
  if verify()!=before:raise RuntimeError('Input manifest changed')
  coverage();imported()
  report=dict(status='COMBINED_REPRODUCTION_VERIFIED',full_saved_null_replay=args.full_nulls,
   main=primary,legacy={k:v for k,v in legacy.items() if not isinstance(v,list)},
   legacy_counts=dict(formation_models=len(legacy['formation']),threshold_models=len(legacy['threshold']),mass_loss_models=len(legacy['mass_loss']),crosscheck_models=len(legacy['spline_crosscheck']),
    candidate_nulls_replayed=sum(x['null_candidates_replayed'] for x in legacy['formation']+legacy['threshold']),
    joint_minima_replayed=sum(x['minima_recomputed'] for x in legacy['spline_crosscheck'])),
   new_random_streams=0,scientific_findings_closed=[],input_payload_unchanged=True,
   completed_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
  with (out/'COMPLETION.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
  print('COMBINED_REPRODUCTION_VERIFIED');print('OUTPUT_DIRECTORY='+str(out))
 except BaseException as exc:
  with (out/'FAILURE.json').open('x') as f:json.dump(dict(status='HOLD',error=type(exc).__name__,message=str(exc),traceback=traceback.format_exc(),success_logbook_written=False),f,indent=2)
  raise
if __name__=='__main__':main()
