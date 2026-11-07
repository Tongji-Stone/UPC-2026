"""Sample explicitly bounded spin, wind and drag and record all event outcomes."""
import csv,json
from dataclasses import replace
from pathlib import Path
import numpy as np
from football.physics import PhysicsConfig,simulate,linthorne_patel_coefficients
from football.inference.physical_fit import fit_velocity
rng=np.random.default_rng(20261107); n=600
t=np.array([0.,.05,.10]); obs=np.array([[0,0,.11],[1.50,.45,.44],[2.96,.86,.74]]);p=obs[0]
out=Path('results/bounded_uncertainty');out.mkdir(parents=True,exist_ok=True);rows=[]
for i in range(n):
    spin=rng.uniform(-50,50,3);wind=rng.uniform(-3,3,3);rho=rng.uniform(1.1,1.3);cd=rng.uniform(.1,.2)
    cfg=replace(PhysicsConfig.for_model('M5'),air_density=rho,wind=tuple(wind),coefficients=linthorne_patel_coefficients(cd0=cd))
    fit=fit_velocity(t,obs,cfg,sigma=.01,spin=spin);v=fit['velocity'];misfit=float(np.max(np.abs(fit['residuals'][1:])))
    if misfit>.02:
        rows.append({'i':i,'spin_x':spin[0],'spin_y':spin[1],'spin_z':spin[2],'wind_x':wind[0],'wind_y':wind[1],'wind_z':wind[2],'rho':rho,'cd0':cd,'event':'incompatible','y':'','z':''});continue
    f=simulate(p,v,spin=spin,config=cfg,t_span=(0,2),plane_x=11.)
    point=f.event['position'] if f.event['type']=='plane' else None
    rows.append({'i':i,'spin_x':spin[0],'spin_y':spin[1],'spin_z':spin[2],'wind_x':wind[0],'wind_y':wind[1],'wind_z':wind[2],'rho':rho,'cd0':cd,'event':f.event['type'],'y':point[1] if point is not None else '', 'z':point[2] if point is not None else ''})
with (out/'samples.csv').open('w',encoding='utf8',newline='') as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
valid=[r for r in rows if r['event']=='plane']
stats={'seed':20261107,'samples':n,'input_times_s':t.tolist(),'positions_m':obs.tolist(),'max_component_fit_tolerance_m':.02,'spin_bounds_rad_s':[-50,50],'wind_component_bounds_m_s':[-3,3],'rho_kg_m3':[1.1,1.3],'cd0':[.1,.2], 'plane':len(valid),'ground':sum(r['event']=='ground' for r in rows),'none':sum(r['event']=='none' for r in rows),'incompatible':sum(r['event']=='incompatible' for r in rows),'y_range':[min(r['y'] for r in valid),max(r['y'] for r in valid)],'z_range':[min(r['z'] for r in valid),max(r['z'] for r in valid)]}
(out/'summary.json').write_text(json.dumps(stats,indent=2),encoding='utf8');print(json.dumps(stats,indent=2))
