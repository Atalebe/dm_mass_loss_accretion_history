"""Validate the additive import and bind its successful replay to exact files."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
ARCHIVE_SHA='52c99eb9ecc821cecc6009f8886f13fda2d75425733b47d6abc1624b3c4f9dac'
EXPECTED=dict(formation_models=15,formation_candidates=390,formation_null_candidates=312000,
 threshold_models=9,threshold_candidates=234,threshold_null_candidates=156000,
 mass_loss_models=27,crosscheck_models=36,crosscheck_minima=360000)
def need(ok,message):
 if not bool(ok):raise RuntimeError(message)
def validate_record(r):
 need(r['archive_sha256']==ARCHIVE_SHA,'Wrong imported archive')
 need(r['status']=='ADDITIVE_IMPORT_AND_FULL_SAVED_REPLAY_VERIFIED','Import not qualified')
 need(r['counts']==EXPECTED,'Full replay coverage changed')
 need(r['archive_files']==239 and r['archive_manifest_payloads']==238,'Archive membership changed')
 need(r['overwritten_existing_paths']==0 and r['all_companion_bytes_preserved'] is True,'Non-additive import')
 need(r['full_saved_null_replay'] is True and r['new_random_streams']==0 and r['raw_tree_scans']==0,'Replay relabelled as a new experiment')
 need(r['scientific_findings_closed']==[] and r['manuscript_modified'] is False,'Claim or manuscript changed')
def verify(root=ROOT):
 root=Path(root);r=json.loads((root/'provenance/legacy_import_verification.json').read_text());validate_record(r)
 entries=json.loads((root/'provenance/legacy_payload_manifest.json').read_text())['files']
 need(len(entries)==238 and len({e['path'] for e in entries})==238,'Companion membership')
 for e in entries:
  p=root/e['path'];need(p.resolve().is_relative_to(root.resolve()) and not p.is_symlink(),'Unsafe import path')
  need(p.is_file() and p.stat().st_size==e['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==e['sha256'],'Imported bytes differ: '+e['path'])
 result=json.loads((root/'provenance/legacy_pc_full_replay.json').read_text())
 need(result['status']=='PRESERVED_LEGACY_RESULTS_REPRODUCED' and result['full_saved_null_replay'] is True,'Replay receipt missing')
 counts=dict(formation_models=len(result['formation']),formation_candidates=sum(x['observed_candidates'] for x in result['formation']),
  formation_null_candidates=sum(x['null_candidates_replayed'] for x in result['formation']),threshold_models=len(result['threshold']),
  threshold_candidates=sum(x['observed_candidates'] for x in result['threshold']),threshold_null_candidates=sum(x['null_candidates_replayed'] for x in result['threshold']),
  mass_loss_models=len(result['mass_loss']),crosscheck_models=len(result['spline_crosscheck']),crosscheck_minima=sum(x['minima_recomputed'] for x in result['spline_crosscheck']))
 need(counts==EXPECTED,'Replay receipt coverage differs')
 recovery=json.loads((root/'docs/legacy_recovery_status.json').read_text());mapping=json.loads((root/'docs/reproducibility_map.json').read_text())
 need(recovery['imported_into_repository'] is True and recovery['sha256']==ARCHIVE_SHA,'Recovery status mismatch')
 need(mapping['companion_transfer_status']=='IMPORTED_AND_FULL_REPLAY_VERIFIED','Map not updated')
 need(all(a['coverage_status']!='RECOVERED_COMPANION_PENDING_IMPORT' for a in mapping['assets']),'Stale pending asset')
 return dict(status='LEGACY_IMPORT_BOUND_TO_FULL_REPLAY',companion_files=239,counts=counts,new_random_streams=0,scientific_findings_closed=[])
if __name__=='__main__':print(json.dumps(verify(),indent=2))
