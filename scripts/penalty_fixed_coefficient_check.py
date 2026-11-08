"""Single-penalty diagnostic: fixed force multipliers or fixed actual Cd/Cl."""
import json
from pathlib import Path
from dataclasses import replace
import numpy as np
from scipy.optimize import least_squares
from football.inference.coupled_fit import observed_trajectory
from football.physics import PhysicsConfig,simulate,kiratidis_leinweber_coefficients

root=Path(__file__).resolve().parents[1]
case=next(x for x in json.loads((root/'data/report_v2/match_cases.json').read_text(encoding='utf8')) if x['case']=='penalty_18232100000995')
t=np.asarray(case['times_s'][:3]);p=np.asarray(case['positions_m'][:3]);target=np.asarray(case['target_yz_m']);plane=case['plane_x_m']
reference=PhysicsConfig.for_model('M4');cd,cl=kiratidis_leinweber_coefficients(333793,.19,reference.radius,reference.kinematic_viscosity)
configs={'fixed_scales_variable_coefficients':reference,'fixed_actual_coefficients':replace(reference,coefficient_mode='constant',drag_coefficient=cd,lift_coefficient=cl)}
v=np.linalg.lstsq(np.c_[t[1:],.5*t[1:]**2],p[1:]-p[0],rcond=None)[0][0]; v[0]=max(v[0],.01)
starts=[np.r_[v,[0.,0.,0.]]]+[np.r_[v,sign*30*axis] for axis in np.eye(3) for sign in (-1,1)]
out={}; lower=np.array([0,-35,-35,-20*np.pi,-20*np.pi,-20*np.pi]);upper=np.array([35,35,35,20*np.pi,20*np.pi,20*np.pi])
for mode,cfg in configs.items():
 def fun(q):return ((observed_trajectory(t,p[0],q,cfg,rtol=3e-10,atol=2e-12)[1:,:3]-p[1:])/cfg.radius).ravel()
 candidates=[]
 for index,q0 in enumerate(starts):
  opt=least_squares(fun,np.clip(q0,lower+1e-8,upper-1e-8),bounds=(lower,upper),x_scale=np.array([30,30,30,60,60,60]),ftol=2e-11,xtol=2e-11,gtol=2e-11,max_nfev=240)
  candidates.append({'start':index,'success':bool(opt.success),'nfev':opt.nfev,'message':opt.message,'rss_m2':float(np.sum(fun(opt.x)**2)*cfg.radius**2),'state':opt.x.tolist()})
  print(mode,index,'success',opt.success,'rss',candidates[-1]['rss_m2'],flush=True)
 best=min(candidates,key=lambda x:x['rss_m2']);q=np.array(best['state']);f=simulate(p[0],q[:3],q[3:],cfg,t_span=(0,5),plane_x=plane,rtol=1e-10,atol=1e-12,max_step=.01)
 points=observed_trajectory(t,p[0],q,cfg,rtol=1e-11,atol=1e-13)[:,:3]
 hit=f.event['position'];err=float(np.linalg.norm(hit[1:]-target)) if f.event['type']=='plane' else None
 out[mode]={'candidates':candidates,'best':best,'fitted_positions':points.tolist(),'max_residual_m':float(np.max(np.abs(points-p))),
  'event':{'type':f.event['type'],'time':f.event['time'],'position':hit.tolist() if hit is not None else None},'candidate_goal_error_m':err,'fixed_cd':cd if mode=='fixed_actual_coefficients' else None,'fixed_cl':cl if mode=='fixed_actual_coefficients' else None}
result={'case':case['case'],'input_times_s':t.tolist(),'input_positions_m':p.tolist(),'plane_x_m':plane,'target_yz_m':target.tolist(),
 'bounds':'velocity components +/-35 m/s, vx >= 0; spin components +/-20pi rad/s','fixed_force_scales':[1,1],
 'note':'goal target is used only after fitting; 7 starts per mode; optimization stopping success is distinct from observation fit and predictive validity','results':out}
folder=root/'results/penalty_fixed_coefficients';folder.mkdir(parents=True,exist_ok=True)
(folder/'result.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps(result,indent=2,ensure_ascii=False),flush=True)
