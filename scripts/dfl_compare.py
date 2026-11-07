"""Single real-trajectory integration example; not a population benchmark."""
import csv
import json
from pathlib import Path
import numpy as np
from football.data.validation import early_observations, crossing
from football.inference.physical_fit import fit_velocity
from football.physics import PhysicsConfig, simulate
from football.models.baseline import predict

path = Path('results/dfl_example')
with (path/'sample.csv').open(encoding='utf-8',newline='') as f:
    rows = list(csv.DictReader(f))
t = np.array([float(r['t_s']) for r in rows])
p = np.array([[float(r[k]) for k in ('x_m','y_m','z_m')] for r in rows])
truth = crossing(t,p,11,.1)[1][1:]
result = {}
for duration in (.05,.10):
    ot, op = early_observations(t,p,duration)
    values = {}
    for model in ('M0','M1','M3','M4'):
        config = PhysicsConfig.for_model(model)
        spin = (0.,0.,30.) if model == 'M4' else (0.,0.,0.)
        fit = fit_velocity(ot,op,config,spin=spin)
        sol = simulate(op[0],fit['velocity'],spin=spin,config=config,t_span=(0.,2.))
        event = sol.event
        values[model] = {'event':event['type'], 'spin_rad_s':spin}
        if event['type'] == 'plane':
            yz = event['position'][1:]
            values[model].update(yz_m=yz.tolist(),error_m=float(np.linalg.norm(yz-truth)))
    if len(ot) < 3:
        values['M2'] = {'event':'insufficient_observations'}
    else:
        q = predict(ot,op,model='M2')
        if q is None:
            values['M2'] = {'event':'no_plane_crossing'}
        else:
            coef = np.linalg.solve(np.column_stack((np.ones(3), ot[-3:], ot[-3:]**2)), op[-3:])
            plane_roots = np.roots([coef[2,0],coef[1,0],coef[0,0]-11])
            plane_time = min(r.real for r in plane_roots if abs(r.imag)<1e-9 and r.real>=ot[-1])
            ground_roots = np.roots([coef[2,2],coef[1,2],coef[0,2]-.11])
            ground = [r.real for r in ground_roots if abs(r.imag)<1e-9 and ot[-1] <= r.real < plane_time
                      and coef[1,2]+2*coef[2,2]*r.real < 0]
            if ground:
                values['M2'] = {'event':'ground', 'time_s':min(ground)}
            else:
                values['M2'] = {'event':'plane', 'yz_m':q[1:].tolist(),
                                'error_m':float(np.linalg.norm(q[1:]-truth))}
    result[str(duration)] = values
(path/'model_comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
