"""Compare two published drag descriptions at identical nonspinning conditions.

Maponi & Piombin (2025), Table A1: CFD drag for a soccer-ball model.
Paudel & Yan (2026), Eq. (26): smooth-sphere drag relation.
The two sources use different computational settings; this is a coefficient-law
sensitivity experiment, not a matched CFD simulation or ball identification.
"""
import csv, json
from dataclasses import replace
from pathlib import Path
import numpy as np
from football.physics import PhysicsConfig, simulate
from football.inference.physical_fit import fit_velocity

out=Path('results/surface_sensitivity');out.mkdir(parents=True,exist_ok=True)
obs=np.array([[0,0,.11],[1.50,.45,.44],[2.96,.86,.74]]);position=obs[0]
velocity=fit_velocity([0,.05,.10],obs,PhysicsConfig.for_model('M3'))['velocity']
base=PhysicsConfig.for_model('M3'); speeds=np.arange(5,51,5,dtype=float)
cd_values=np.array([.1992,.1969,.1949,.1938,.1930,.1924,.1921,.1917,.1915,.1913])
def soccer(re,sp):
    speed=re*base.kinematic_viscosity/(2*base.radius)
    if not speeds[0]<=speed<=speeds[-1]:raise ValueError('speed outside published 5-50 m/s table')
    return float(np.interp(speed,speeds,cd_values)),0.
def smooth(re,sp):
    if re<=0: return 0.,0.
    cd=24/re+2.6*(re/5)/(1+(re/5)**1.52)+.411*(re/2.63e5)**(-7.94)/(1+(re/2.63e5)**(-8))+re**.8/4.61e5
    return cd,0.
records=[]; traces=[]
for name,callback in [('smooth_sphere_drag',smooth),('soccer_ball_drag',soccer)]:
    cfg=replace(base,coefficients=callback)
    run=simulate(position,velocity,spin=(0,0,0),config=cfg,t_span=(0,2),plane_x=11.,max_step=.005)
    event=run.event; initial_speed=float(np.linalg.norm(velocity)); final_speed=float(np.linalg.norm(run.velocity[-1]))
    p=event['position']
    records.append({'law':name,'event':event['type'],'time_s':event['time'],'goal_y_m':float(p[1]) if p is not None else None,
      'goal_z_assumed_m':float(p[2]) if p is not None else None,'initial_speed_m_s':initial_speed,'final_speed_m_s':final_speed,
      'initial_cd':callback(initial_speed*2*cfg.radius/cfg.kinematic_viscosity,0)[0]})
    traces.extend({'law':name,'time_s':float(t),'x_m':float(x[0]),'y_m':float(x[1]),'z_assumed_m':float(x[2])} for t,x in zip(run.t,run.position))
with (out/'trajectories.csv').open('w',encoding='utf8',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=traces[0]);writer.writeheader();writer.writerows(traces)
result={'comparison':'nonspinning, equal initial velocity and physical parameters, changing drag coefficient laws only',
 'goal_plane_x_m':11.,'kinematic_viscosity_m2_s':base.kinematic_viscosity,'initial_position_m':position.tolist(),
 'initial_velocity_m_s':velocity.tolist(),'sources':{'soccer_ball_drag':'Maponi & Piombin (2025), Table A1, https://doi.org/10.1155/jama/7425581',
 'smooth_sphere_drag':'Paudel & Yan (2026), Eq. 26, https://doi.org/10.1007/s00466-025-02705-2'},'cases':records}
(out/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result,indent=2))
