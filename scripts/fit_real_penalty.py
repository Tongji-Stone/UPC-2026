# HISTORICAL pipeline; not used by the current paper. Use scripts/coupled_compute.py.
"""Fit recorded complete penalty flight and compare with actual goal plane."""
import csv, json
from dataclasses import replace
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import least_squares
from football.physics import PhysicsConfig, forces, linthorne_patel_coefficients
from dfl_full_trajectory_fit import curve

root=Path('results/b_real_penalty')
with (root/'trajectory.csv').open(encoding='utf8',newline='') as f: rows=list(csv.DictReader(f))
meta=json.loads((root/'event_and_crossing.json').read_text(encoding='utf8'))
t=np.array([float(r['elapsed_s']) for r in rows]); raw=np.array([[float(r[k]) for k in ('x_m','y_m','z_raw')] for r in rows])
p=raw.copy(); p[:,:2]-=raw[0,:2]; plane=meta['goal_plane_x_m']-raw[0,0]
truth=np.array([meta['crossing_y_m']-raw[0,1],meta['crossing_z_raw']])
base=PhysicsConfig.for_model('M5')
def forward(q):
    spin=q[3:6]; cfg=replace(base,coefficients=linthorne_patel_coefficients(cd0=q[6]))
    def rhs(_,s): return np.r_[s[3:6],sum(forces(s[3:6],s[6:9],cfg).values())/cfg.mass,[0.,0.,0.]]
    def goal(_,s):return s[0]-plane
    goal.terminal=False;goal.direction=1
    def ground(_,s):return s[2]-cfg.radius
    ground.terminal=True;ground.direction=-1
    sol=solve_ivp(rhs,(0,t[-1]),np.r_[p[0],q[:3],spin],events=(goal,ground),dense_output=True,rtol=1e-7,atol=1e-9)
    return sol
def residual(q):
    sol=forward(q)
    if not sol.success or sol.t[-1] < t[-1]-1e-9:
        return np.full(p.size,1000.)
    return (sol.sol(t)[:3].T-p).ravel()
q0=np.r_[(p[-1]-p[0])/t[-1],[0,0,0],.18]
fit=least_squares(residual,q0,bounds=([0,-60,-20,-150,-150,-150,.1],[80,60,60,150,150,150,.2]),max_nfev=250)
sol=forward(fit.x); fitted=sol.sol(t)[:3].T
curves={'M5_fitted':fitted}; records={}
def record(name, track, hit):
    err=np.linalg.norm(track-p[:len(track)],axis=1)
    records[name]={'frames':len(track),'trajectory_rmse_m':float(np.sqrt(np.mean(err**2))),
      'trajectory_median_error_m':float(np.median(err)),
      'goal_plane_yz_m':[float(hit[0]+raw[0,1]),float(hit[1])] if hit is not None else None,
      'goal_plane_error_m':float(np.linalg.norm(hit-truth)) if hit is not None else None}
record('M5_fitted',fitted,sol.y_events[0][0,1:3] if len(sol.t_events[0]) else None)
records['M5_fitted']['velocity_m_s']=fit.x[:3].tolist(); records['M5_fitted']['spin_rad_s']=fit.x[3:6].tolist()
records['M5_fitted']['cd0']=float(fit.x[6]); records['M5_fitted']['converged']=bool(fit.success)
records['M5_fitted']['jacobian_singular_values']=np.linalg.svd(fit.jac,compute_uv=False).tolist()
for model in ('M0','M1','M2','M3','M4','M5'):
    predicted,hit,event=curve(model,t,p,plane_x=plane)
    curves[model]=predicted; record(model,predicted,hit); records[model]['event']=event
out=Path('results/real_penalty_fit');out.mkdir(exist_ok=True,parents=True)
with (out/'trajectory_fit.csv').open('w',encoding='utf8',newline='') as f:
    w=csv.writer(f); w.writerow(['time_s','model','x_m','y_m','z_assumed_m'])
    for name,values in [('observed',p),*curves.items()]:
        for tt,xyz in zip(t,values):w.writerow([tt,name,xyz[0]+raw[0,0],xyz[1]+raw[0,1],xyz[2]])
result={'interpretation':'fit all 12 frames, including the first frame beyond the line; in-sample trajectory reconstruction',
 'source_metadata':meta,'height_unit':'assumed metres','goal_plane_distance_from_first_frame_m':plane,
 'm5_fitted_note':'velocity, spin and Cd0 fitted with bounds using same trajectory; spin not measured',
 'models':records}
(out/'summary.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps(records,indent=2))
