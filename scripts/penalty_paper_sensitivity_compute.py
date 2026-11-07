"""Perturb the fitted real penalty state and save plane positions."""
import csv, json
from dataclasses import replace
from pathlib import Path
import numpy as np
from football.physics import PhysicsConfig, simulate, linthorne_patel_coefficients

result=json.loads(Path('results/real_penalty_fit/summary.json').read_text(encoding='utf8'))
model=result['models']['M5_fitted']; raw=result['source_metadata']
with Path('results/b_real_penalty/trajectory.csv').open(encoding='utf8',newline='') as f: first=next(csv.DictReader(f))
pos=np.array([float(first['x_m']),float(first['y_m']),float(first['z_raw'])]); v=np.array(model['velocity_m_s']); spin=np.array(model['spin_rad_s']); cd=model['cd0']
records=[]
for factor in ('speed','azimuth_deg','spin_scale','cd0'):
    values={'speed':[.95,1,1.05],'azimuth_deg':[-2,0,2],'spin_scale':[.5,1,1.5],'cd0':[.10,.15,.20]}[factor]
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
