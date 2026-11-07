"""Refresh diagnostic force columns without fitting or integrating trajectories."""
from pathlib import Path
from dataclasses import replace
import csv,json
import numpy as np
from football.physics import PhysicsConfig,forces
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/structure_v2'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def update(path,cfg):
    with path.open(encoding='utf-8') as f:rows=list(csv.DictReader(f))
    for r in rows:
        ff=forces([float(r[k]) for k in ['vx','vy','vz']],[float(r[k]) for k in ['wx','wy','wz']],cfg)
        r.update(drag_N=np.linalg.norm(ff['drag']),lift_N=np.linalg.norm(ff['magnus']))
    with path.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
def main():
    configs={a['case']:a['physics'] for a in read(ROOT/'data/report_v2/controlled_cases.json')}
    for path in (OUT/'forward').glob('*.csv'):
        case,model=path.stem.rsplit('_',1);update(path,PhysicsConfig.for_model(model,**configs[case]))
    for group in ['problem','matches']:
        for path in (OUT/group).glob('*.csv'):
            source=path.with_suffix('.json')
            if not source.exists():continue
            record=read(source)
            if 'configuration' not in record:continue
            a=record['configuration'];allowed=set(PhysicsConfig.__dataclass_fields__)-{'coefficients'}
            update(path,PhysicsConfig(**{k:v for k,v in a.items() if k in allowed}))
        # Normalize convergence metadata in caches created before the final diagnostics.
        summary=[]
        for path in sorted((OUT/group).glob('*.json')):
            if path.name=='summary.json':continue
            result=read(path)
            if 'record' not in result:continue
            fit=result.get('fit');record=result['record']
            if fit:
                starts=[r for r in fit.get('starts',[]) if 'rss_m2' in r]
                converged=bool(min(starts,key=lambda r:r['rss_m2'])['success']) if starts else True
                fit['success']=converged;fit['position_stage_converged']=converged
                record['fit_converged']=converged
                if not converged:
                    event=record.get('event',{});target=record.get('target_yz_m')
                    if event.get('type')=='plane' and target is not None:
                        record['candidate_plane_error_m']=float(np.linalg.norm(np.asarray(event['position'][1:])-target))
                    record['error_m']=None;record['status']='fit_failure'
                path.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
            summary.append(record)
        (OUT/group/'summary.json').write_text(json.dumps(dict(records=summary),indent=2),encoding='utf-8')
    for path in (OUT/'other').glob('*.csv'):
        rec=next(r for r in read(OUT/'other/summary.json')['records'] if r['case']==path.stem)
        allowed=set(PhysicsConfig.__dataclass_fields__)-{'coefficients'}
        update(path,PhysicsConfig(**{k:v for k,v in rec['configuration'].items() if k in allowed}))
    print('force columns refreshed from saved states')
if __name__=='__main__':main()
