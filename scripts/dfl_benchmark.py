"""Fixed sequential, non-overlapping DFL trajectory demonstration benchmark."""
import argparse
import csv
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
from time import perf_counter
import numpy as np
from football.data.validation import align_forward, crossing, early_observations
from football.evaluation.metrics import summarize_errors
from football.models.baseline import predict
from football.inference.physical_fit import fit_velocity
from football.physics import PhysicsConfig, linthorne_patel_coefficients, simulate


def candidate(rows):
    try:
        if any(r['section'] != rows[0]['section'] or r['status'] != '1' for r in rows):
            return 'section_or_inactive', None
        t0 = datetime.fromisoformat(rows[0]['timestamp'])
        t = np.array([(datetime.fromisoformat(r['timestamp'])-t0).total_seconds() for r in rows])
        p = np.array([[float(r[k]) for k in ('x_m','y_m','z_raw')] for r in rows])
        if not np.isfinite(p).all() or not np.allclose(np.diff(t),.04,atol=1e-6):
            return 'missing_or_irregular', None
        if not np.all((p[:,2] > .3) & (p[:,2] < 15)):
            return 'height', None
        speed = np.linalg.norm(np.diff(p,axis=0),axis=1)/.04
        if np.any((speed < 2) | (speed > 45)):
            return 'speed', None
        direction = p[1,:2]-p[0,:2]
        if np.linalg.norm(direction) < .2:
            return 'initial_direction', None
        q = align_forward(p,direction)
        hit = crossing(t,q,11,.10)
        if hit is None:
            return 'no_heldout_crossing', None
        return 'selected', (t,q,hit)
    except (ValueError, TypeError):
        return 'missing_or_irregular', None


def predict_model(model,t,p):
    if model == 'M2':
        if len(t) < 3:
            return 'insufficient_observations', None
        q = predict(t,p,model='M2')
        if q is None:
            return 'no_plane_crossing', None
        coef = np.linalg.solve(np.column_stack((np.ones(3),t[-3:],t[-3:]**2)),p[-3:])
        roots = np.roots([coef[2,0],coef[1,0],coef[0,0]-11])
        arrival = min(r.real for r in roots if abs(r.imag)<1e-9 and r.real>=t[-1])
        ground = np.roots([coef[2,2],coef[1,2],coef[0,2]-.11])
        if any(abs(r.imag)<1e-9 and t[-1] <= r.real < arrival and coef[1,2]+2*coef[2,2]*r.real < 0 for r in ground):
            return 'ground', None
        return 'plane', q[1:]
    spin = (0.,0.,30.) if model in ('M4','M5') else (0.,0.,0.)
    kwargs = {'coefficients':linthorne_patel_coefficients()} if model == 'M5' else {}
    config = PhysicsConfig.for_model(model,**kwargs)
    fitted = fit_velocity(t,p,config,spin=spin)
    event = simulate(p[0],fitted['velocity'],spin=spin,config=config,t_span=(0.,2.)).event
    return event['type'], event['position'][1:] if event['type']=='plane' else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csv')
    ap.add_argument('--count',type=int,default=30)
    ap.add_argument('--out',default='results/dfl_benchmark')
    args = ap.parse_args()
    if args.count <= 0: raise ValueError('count must be positive')
    with open(args.csv,encoding='utf-8',newline='') as f:
        rows = list(csv.DictReader(f))
    selected = []
    counts = Counter()
    start = 0
    while start+21 <= len(rows) and len(selected)<args.count:
        w = rows[start:start+21]
        reason, value = candidate(w)
        counts[reason] += 1
        if value is not None:
            selected.append((w,*value))
            start += 21
        else:
            start += 1
    out = Path(args.out); out.mkdir(parents=True,exist_ok=True)
    records = []
    for index,(w,t,p,hit) in enumerate(selected):
        for duration in (.05,.10):
            ot,op=early_observations(t,p,duration)
            for model in ('M0','M1','M2','M3','M4','M5'):
                start_time = perf_counter()
                try:
                    event, yz = predict_model(model,ot,op)
                except (ValueError,RuntimeError,FloatingPointError,np.linalg.LinAlgError) as exc:
                    event,yz = 'error:'+type(exc).__name__,None
                elapsed = perf_counter()-start_time
                records.append({'sample':index+1,'section':w[0]['section'],'start_frame':w[0]['frame'],
                    'start_timestamp':w[0]['timestamp'],'duration_s':duration,'last_observed_s':float(ot[-1]),
                    'model':model,'event':event,'truth_y_m':float(hit[1][1]),'truth_z_assumed_m':float(hit[1][2]),
                    'prediction_y_m':float(yz[0]) if yz is not None else '',
                    'prediction_z_assumed_m':float(yz[1]) if yz is not None else '',
                    'error_assumed_m':float(np.linalg.norm(yz-hit[1][1:])) if yz is not None else '',
                    'runtime_s':elapsed})
    if not records: raise SystemExit('no selected samples')
    with (out/'samples_and_predictions.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=records[0]);writer.writeheader();writer.writerows(records)
    summary={'selection':{'requested':args.count,'selected':len(selected),'examined_start_windows':sum(counts.values()),
              'first_failure_reasons':dict(counts),'overlap_policy':'after selection advance 21 frames',
              'z_unit':'assumed metres; original published description has not been verified'},'groups':{}}
    for duration in (.05,.10):
        for model in ('M0','M1','M2','M3','M4','M5'):
            group=[r for r in records if r['duration_s']==duration and r['model']==model]
            valid=[r for r in group if r['event']=='plane']
            info={'cases':len(group),'events':dict(Counter(r['event'] for r in group)),
                  'mean_runtime_s':float(np.mean([r['runtime_s'] for r in group]))}
            if valid:
                info['error']=summarize_errors([[r['truth_y_m'],r['truth_z_assumed_m']] for r in valid],
                                               [[r['prediction_y_m'],r['prediction_z_assumed_m']] for r in valid])
            summary['groups'][f'{duration}_{model}']=info
        comparable = ('M0','M1','M3','M4','M5') if duration == .05 else ('M0','M1','M2','M3','M4','M5')
        eligible = [r['sample'] for r in records if r['duration_s']==duration and r['model']==comparable[0]]
        shared = [i for i in eligible if all(any(r['sample']==i and r['duration_s']==duration and
                    r['model']==model and r['event']=='plane' for r in records) for model in comparable)]
        common = {}
        for model in comparable:
            valid=[r for r in records if r['duration_s']==duration and r['model']==model and r['sample'] in shared]
            if valid:
                common[model]=summarize_errors([[r['truth_y_m'],r['truth_z_assumed_m']] for r in valid],
                                               [[r['prediction_y_m'],r['prediction_z_assumed_m']] for r in valid])
        summary.setdefault('common_cases',{})[str(duration)]={'n':len(shared),'models':common}
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
