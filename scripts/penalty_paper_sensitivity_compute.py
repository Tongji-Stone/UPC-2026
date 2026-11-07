"""Perturb the fitted real penalty state and save plane positions."""
import csv, json
from dataclasses import replace
from pathlib import Path
import numpy as np
from football.physics import PhysicsConfig, simulate, linthorne_patel_coefficients
from football.inference.physical_fit import fit_velocity

times=np.array([0.,.05,.10]);obs=np.array([[0,0,.11],[1.50,.45,.44],[2.96,.86,.74]])
pos=obs[0];spin=np.array([0.,0.,30.]);cd=.18;raw={'goal_plane_x_m':11.}
reference=replace(PhysicsConfig.for_model('M5'),coefficients=linthorne_patel_coefficients(cd0=cd))
v=fit_velocity(times,obs,reference,spin=spin)['velocity']
records=[]
for factor in ('speed','azimuth_deg','spin_scale','cd0'):
    values={'speed':np.linspace(.7,1.3,31),'azimuth_deg':np.linspace(-10,10,41),'spin_scale':np.linspace(0,4,41),'cd0':np.linspace(.05,.40,36)}[factor]
    for val in values:
        vv=v.copy(); ww=spin.copy(); cc=cd
        if factor=='speed':vv*=val
        if factor=='azimuth_deg':
            a=np.deg2rad(val); vv[:2]=np.array([[np.cos(a),-np.sin(a)],[np.sin(a),np.cos(a)]])@vv[:2]
        if factor=='spin_scale':ww*=val
        if factor=='cd0':cc=val
        cfg=replace(PhysicsConfig.for_model('M5'),coefficients=linthorne_patel_coefficients(cd0=cc))
        flight=simulate(pos,vv,spin=ww,config=cfg,plane_x=raw['goal_plane_x_m'],t_span=(0,2))
        p=flight.event['position']
        records.append({'factor':factor,'value':val,'event':flight.event['type'],'y_m':p[1] if p is not None else '', 'z_m_assumed':p[2] if p is not None else ''})
out=Path('results/penalty_paper_sensitivity');out.mkdir(exist_ok=True,parents=True)
with (out/'scan.csv').open('w',encoding='utf8',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=records[0]);writer.writeheader();writer.writerows(records)
print(json.dumps(records,indent=2))
