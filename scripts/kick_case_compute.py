"""Illustrative kick simulations and three-point predictions; no random inputs."""
import csv,json
from pathlib import Path
import numpy as np
from football.physics import PhysicsConfig,simulate
from football.inference.coupled_fit import observed_trajectory
from football.inference.physical_fit import fit_velocity

cases=[('Power',27,8,(0,0,0)),('Placement',20,11,(0,0,0)),('Curved',24,10,(0,0,35)),('Topspin',24,12,(0,35,0)),('Backspin',24,10,(0,-35,0)),('Chip',14,20,(0,-15,0))]
t=np.array([0.,.05,.10]);p0=np.array([0.,0.,.11]);out=Path('results/kick_cases');out.mkdir(parents=True,exist_ok=True);rows=[];traces=[]
for name,speed,angle,spin in cases:
    a=np.deg2rad(angle);v=np.array([speed*np.cos(a),0,speed*np.sin(a)]);config=PhysicsConfig.for_model('M4')
    truth=simulate(p0,v,spin,config=config,plane_x=11,t_span=(0,3),max_step=.01); early=observed_trajectory(t,p0,np.r_[v,spin],config)[:,:3]
    traces.extend({'case':name,'kind':'truth','x':xyz[0],'y':xyz[1],'z':xyz[2]} for xyz in truth.position)
    traces.extend({'case':name,'kind':'observation','x':xyz[0],'y':xyz[1],'z':xyz[2]} for xyz in early)
    row={'case':name,'speed_m_s':speed,'angle_deg':angle,'spin_x':spin[0],'spin_y':spin[1],'spin_z':spin[2],'early_positions_m':early.tolist(),'truth_status':truth.event['type']}
    true=truth.event['position'][1:] if truth.event['type']=='plane' else None
    row.update({'true_y':true[0] if true is not None else None,'true_z':true[1] if true is not None else None})
    for key,model,w in [('M1','M1',(0,0,0)),('M4_zero','M4',(0,0,0)),('M4_known','M4',spin)]:
        c=PhysicsConfig.for_model(model);fit=fit_velocity(t,early,c,spin=w);f=simulate(p0,fit['velocity'],w,config=c,plane_x=11,t_span=(0,3),max_step=.01)
        if key=='M4_zero':traces.extend({'case':name,'kind':'zero_spin','x':xyz[0],'y':xyz[1],'z':xyz[2]} for xyz in f.position)
        hit=f.event['position'][1:] if f.event['type']=='plane' else None
        row[key+'_status']=f.event['type'];row[key+'_error_m']=float(np.linalg.norm(hit-true)) if true is not None and hit is not None else None
    rows.append(row)
with (out/'cases.csv').open('w',newline='',encoding='utf8') as f:
    w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
with (out/'trajectories.csv').open('w',newline='',encoding='utf8') as f:
    w=csv.DictWriter(f,fieldnames=traces[0]);w.writeheader();w.writerows(traces)
(out/'cases.json').write_text(json.dumps({'description':'illustrative synthetic single examples, not empirical distributions; M4_known uses true simulated spin','times_s':t.tolist(),'cases':rows},indent=2),encoding='utf8')
print(json.dumps(rows,indent=2))
