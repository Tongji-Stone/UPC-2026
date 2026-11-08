"""Re-evaluate the teammate's corrected-start penalty inputs; no drawing."""
import json
from pathlib import Path
from dataclasses import replace
import numpy as np
from football.physics import PhysicsConfig, simulate
from football.inference.four_model_fit import fit_early
root=Path(__file__).resolve().parents[1]
data=json.loads((root/'data/corrected_penalties_from_teammate.json').read_text(encoding='utf8'))
out=[]
for case in data['cases']:
 t=np.array(case['fit_times_s']);p=np.array(case['fit_positions_m']);target=np.array(case['goal']['local_position'])
 for model in ('M1','M2','M3','M4'):
  cfg=PhysicsConfig.for_model(model);fit=fit_early(t,p,cfg,model)
  cfg=replace(cfg,drag_scale=fit['drag_scale'],lift_scale=fit['lift_scale'])
  if model=='M3':cfg=replace(cfg,constant_acceleration=tuple(fit['constant_acceleration']))
  state=fit['initial_state'];f=simulate(p[0],state[:3],state[3:],cfg,plane_x=11.,t_span=(0,5),rtol=1e-10,atol=1e-12,max_step=.005)
  e=f.event; reached=e['type']=='plane' and e['time']>=t[-1] and fit['success']
  out.append(dict(case=case['case'],model=model,fit=fit,event=e,goal_error_m=float(np.linalg.norm(e['position'][1:]-target[1:])) if reached else None,actual_cd=cfg.drag_coefficient*cfg.drag_scale if model=='M4' else None,alpha=cfg.lift_coefficient*cfg.lift_scale if model=='M4' else None))
  print(case['case'],model,e['type'],out[-1]['goal_error_m'],flush=True)
path=root/'results/structure_linear_spin/corrected_penalties.json';path.parent.mkdir(parents=True,exist_ok=True)
path.write_text(json.dumps({'input_commit':'b6b71d7','records':out},indent=2,default=lambda x:x.tolist()),encoding='utf8')
