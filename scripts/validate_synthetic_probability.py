# HISTORICAL pipeline; not used by the current paper. Use scripts/coupled_compute.py.
"""Check coverage on simulated shots sampled from the stated physical prior."""
import argparse, json, time
from dataclasses import replace
from pathlib import Path
import numpy as np
from football.physics import PhysicsConfig, linthorne_patel_coefficients, simulate
from football.inference.physical_probability import infer_physical, summarize_physical
from football.evaluation.metrics import energy_score

ap = argparse.ArgumentParser()
ap.add_argument('--cases',type=int,default=20); ap.add_argument('--samples',type=int,default=500)
ap.add_argument('--seed',type=int,default=7231); args=ap.parse_args()
rng = np.random.default_rng(args.seed); times=np.array([0.,.05,.10]); p0=np.array([0.,0.,.11])
rows=[]; candidates=0
while len(rows)<args.cases:
    candidates+=1
    v=rng.normal([30.,8.,6.],[10.,10.,10.]); spin=rng.normal(0,30,3); cd=rng.uniform(.1,.2)
    config=replace(PhysicsConfig.for_model('M5'),coefficients=linthorne_patel_coefficients(cd0=cd))
    flight=simulate(p0,v,spin,config,t_span=(0.,2.),max_step=.002)
    if flight.event['type'] != 'plane' or flight.event['time'] <= .1: continue
    p=np.column_stack([np.interp(times,flight.t,flight.position[:,j]) for j in range(3)])
    p[1:] += rng.normal(0,.01,(2,3)); truth=flight.event['position'][1:3]
    case={'index':len(rows),'truth_yz':truth.tolist(),'windows':{}}
    for label,k in [('005',2),('010',3)]:
        start=time.perf_counter()
        posterior=infer_physical(times[:k],p[:k],n=args.samples,seed=args.seed+len(rows)*2+k)
        summary=summarize_physical(posterior,seed=args.seed+len(rows)+k,draws=500)
        points=summary.pop('points'); delta=truth-summary['mean']
        d=float(delta @ np.linalg.pinv(summary['covariance']) @ delta)
        case['windows'][label]={'error_m':float(np.linalg.norm(summary['mean']-truth)),
            'covered68':bool(d<=summary['ellipse_mahalanobis2'][0]),'covered95':bool(d<=summary['ellipse_mahalanobis2'][1]),
            'energy_score_m':energy_score(points,truth),'ess':summary['effective_sample_size'],
            'seconds':time.perf_counter()-start}
    rows.append(case); print(f'case {len(rows)}/{args.cases}',flush=True)
summary={}
for label in ('005','010'):
    a=[r['windows'][label] for r in rows]
    summary[label]={key:float(np.mean([x[key] for x in a])) for key in ('error_m','covered68','covered95','energy_score_m','ess','seconds')}
out=Path('results/synthetic_calibration'); out.mkdir(parents=True,exist_ok=True)
(out/'results.json').write_text(json.dumps({'seed':args.seed,'samples':args.samples,'cases':args.cases,
 'candidate_draws':candidates,'measurement_sigma_m':.01,'selection':'first prior draws reaching plane after 0.1 s',
 'summary':summary,'details':rows},indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
