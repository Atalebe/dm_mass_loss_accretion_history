"""Validate branch-specific reporting status and archive coverage; no fits or permutations."""
from pathlib import Path
import argparse,csv,gzip,hashlib,json,math,re
ROOT=Path(__file__).resolve().parents[1]

def need(value,message):
    if not bool(value): raise RuntimeError(message)

def validate_findings(record):
    need(record.get('baseline')=='ABA-0001-20261020','Wrong audit baseline')
    expected={'ABA26-001':'OPEN_NOT_JOINTLY_CALIBRATED','ABA26-002':'OPEN_FULL_POPULATION_ASSOCIATION_UNIDENTIFIED'}
    rows=record['findings']
    need(len(rows)==2 and {r['id'] for r in rows}==set(expected),'Wrong finding set')
    for r in rows:
        need(r['severity']=='MAJOR','Severity changed')
        need(r['scientific_acceptance_status']==expected[r['id']],'Scientific finding was closed or upgraded')
        need(r['reporting_action_status']=='VERIFIED_IN_V12','Reporting status changed')
    need(rows[0].get('joint_calibration_established') is False,'Unsupported calibration')
    need(rows[1].get('missing_epochs_recovered') is False,'Unsupported recovery')
    need(record['new_scientific_authorization'] is False and record['new_experiments']==0 and record['v176_started'] is False,'Execution scope changed')

def verify(root=ROOT):
    root=Path(root);count=0
    report=json.loads((root/'docs/audit_continuity/ABA0001_followup.json').read_text());validate_findings(report);count+=10
    mapping=json.loads((root/'docs/reproducibility_map.json').read_text());assets=mapping['assets']
    need(len(assets)==32 and len({r['id'] for r in assets})==32,'Asset set incomplete')
    need(mapping['manuscript_changed'] is False,'Unannounced manuscript revision')
    for doc in ['main','supplementary']:
        text=(root/'paper/manuscript'/f'{doc}.tex').read_text()
        for typ in ['table','figure']:
            blocks=re.findall(r'\\begin\{'+typ+r'\}.*?\\end\{'+typ+r'\}',text,re.S)
            matched=[a for a in assets if a['document']==doc and a['type']==typ]
            need(len(blocks)==len(matched),'Unmapped LaTeX asset')
            for i,(block,row) in enumerate(zip(blocks,matched),1):
                need(row['number']==i,'Display order changed')
                need(hashlib.sha256(block.encode()).hexdigest()==row['caption_and_block_sha256'],'Caption/block changed')
                need(row['latex_label']==re.search(r'\\label\{([^}]+)\}',block).group(1),'Label mismatch')
                need(row['coverage_status'] in ['EXECUTABLE_IN_CURRENT_REPOSITORY','RECOVERED_COMPANION_PENDING_IMPORT','PRESERVED_INPUTS_OR_SUMMARY_NOT_DEFAULT_END_TO_END'],'Unknown coverage status')
                for item in row['artifacts']:
                    p=root/item['path'];need(p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'],'Asset input identity:'+item['path']);count+=1
                count+=4
    # The inferential distinctions themselves must still be present in the original text.
    main=(root/'paper/manuscript/main.tex').read_text();sup=(root/'paper/manuscript/supplementary.tex').read_text()
    for phrase in ['not search-adjusted or spatially calibrated','not combine with the permutation comparisons','The 13,517 omitted crossings','Neither the missing epochs']:
        need(phrase in main,'Missing claim boundary:'+phrase);count+=1
    for phrase in ['fixed-parameter spatial comparison','not a jointly calibrated procedure','does not establish missing-at-random selection']:
        need(phrase in sup,'Missing supplementary boundary:'+phrase);count+=1
    summary=json.loads((root/'analysis_data/population_membership/SUMMARY.json').read_text());totals=[0,0,0]
    for case in summary['cases']:
        p=root/case['file'];need(hashlib.sha256(p.read_bytes()).hexdigest()==case['sha256'],'Membership checksum')
        with gzip.open(p,'rt') as f:rows=list(csv.DictReader(f))
        name=case['sample'];d=root/'analysis_data/catalogues'/name
        with gzip.open(d/'feature.csv.gz','rt') as f:features=list(csv.DictReader(f))
        with gzip.open(d/'formation.csv.gz','rt') as f:formation=list(csv.DictReader(f))
        byid={r['halo_id']:r for r in formation}
        need(len(byid)==len(formation)==len(features)==len(rows)==case['available'],'Denominator uniqueness')
        need([r['object_id'] for r in rows]==[r['tree_root_id'] for r in features],'Available identity order')
        observed=[];omitted=[]
        for row in rows:
            fid=row['object_id'];h=byid[fid]
            finite=all(h[k] not in ['', 'nan', 'NaN'] and math.isfinite(float(h[k])) for k in ['a10','a25','a50','a75'])
            need(int(row['formation_complete'])==int(finite),'Completeness predicate')
            need(int(row['omitted_from_four_epoch'])==1-int(finite) and row['available']=='1','Membership flags')
            if finite:observed.append((int(row['fit_row']),fid))
            else:
                need(row['fit_row']=='-1' and row['a10_status']=='left_censored','Omitted status')
                omitted.append(fid)
            count+=2
        need(len(observed)==case['complete'] and len(omitted)==case['omitted'],'Selected/omitted count')
        observed.sort();need([x[0] for x in observed]==list(range(case['complete'])),'Fit row positions')
        ordered=[x[1] for x in observed];need(hashlib.sha256(('\n'.join(ordered)+'\n').encode()).hexdigest()==case['ordered_fit_ids_sha256'],'Fit row identities')
        for j,k in enumerate(['available','complete','omitted']):totals[j]+=case[k]
        count+=6
    need(totals==[62073,48556,13517],'Total denominators')
    need(summary['scientific_population_identification_claimed'] is False,'Identity check relabelled as scientific identification')
    return {'status':'AUDIT_CONTINUITY_AND_RELEASE_MAP_VERIFIED','checks':count,'assets':32,'population_counts':totals,'reporting_actions_complete':2,'scientific_findings_open':['ABA26-001','ABA26-002'],'new_fits':0,'new_permutations':0,'raw_tree_scans':0,'manuscript_changed':False,'companion_transfer_status':mapping['companion_transfer_status']}

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--root',type=Path,default=ROOT);p=a.parse_args()
    print(json.dumps(verify(p.root),indent=2))
