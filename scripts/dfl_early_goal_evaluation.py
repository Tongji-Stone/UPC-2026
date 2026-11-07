"""Predict real goal-plane positions from early frames; later frames score only."""
import csv, json
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import least_squares
from football.inference.physical_fit import fit_velocity
from football.physics import PhysicsConfig, forces, linthorne_patel_coefficients, simulate

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/dfl_early_goal_evaluation'; OUT.mkdir(parents=True,exist_ok=True)

def polynomial_goal(t,p,plane):
    if len(t)<3: return 'insufficient_observations',None
    h=np.column_stack((t, .5*t*t))
    params=np.linalg.lstsq(h[1:],(p-p[0])[1:],rcond=None)[0]
    vx,ax=params[:,0]; vz,az=params[:,2]
    def roots(a,b,c):
        coeff=np.trim_zeros(np.array([a,b,c]),'f')
        return np.roots(coeff) if len(coeff)>1 else []
    valid=[r.real for r in roots(.5*ax,vx,p[0,0]-plane)
           if abs(r.imag)<1e-8 and r.real>=t[-1] and vx+ax*r.real>0 and r.real<=3]
    if not valid:return 'no_plane_crossing',None
    arrival=min(valid)
    ground=[r.real for r in roots(.5*az,vz,p[0,2]-.11)
            if abs(r.imag)<1e-8 and 1e-9<r.real<arrival and vz+az*r.real<0]
    if ground:return 'ground',None
    return 'plane',(p[0]+arrival*params[0]+.5*arrival**2*params[1])[1:]

def map_six(t,p):
    """Initial velocity + spin MAP; same stated prior at both cutoffs."""
    cfg=PhysicsConfig.for_model('M5',coefficients=linthorne_patel_coefficients(cd0=.18))
    prior_mean=np.array([25.,0.,5.,0.,0.,0.]);prior_sd=np.array([15.,15.,15.,30.,30.,30.])
    sigma=.01
    def rhs(_,s):return np.r_[s[3:6],sum(forces(s[3:6],s[6:9],cfg).values())/cfg.mass,[0.,0.,0.]]
    def residual(q):
        sol=solve_ivp(rhs,(0,t[-1]),np.r_[p[0],q],t_eval=t,rtol=2e-7,atol=1e-9)
        if not sol.success:raise RuntimeError(sol.message)
        return np.r_[((sol.y[:3].T[1:]-p[1:])/sigma).ravel(),(q-prior_mean)/prior_sd]
    v=(p[1]-p[0])/(t[1]-t[0]);q=np.r_[v,0.,0.,0.]
    q=np.clip(q,[.01,-59.,-39.,-149.,-149.,-149.],[79.,59.,59.,149.,149.,149.])
    fit=least_squares(residual,q,bounds=([0.,-60.,-40.,-150.,-150.,-150.],[80.,60.,60.,150.,150.,150.]),max_nfev=200)
    return fit.x,cfg

def physical_goal(model,t,p,plane):
    if model=='M5_6_prior':
        q,cfg=map_six(t,p);v=q[:3];spin=q[3:]
    else:
        spin=(0.,0.,30.) if model in ('M4','M5') else (0.,0.,0.)
        cfg=PhysicsConfig.for_model(model,**({'coefficients':linthorne_patel_coefficients(cd0=.18)} if model=='M5' else {}))
        v=fit_velocity(t,p,cfg,sigma=.01,spin=spin)['velocity']
    result=simulate(p[0],v,spin=spin,config=cfg,t_span=(0.,3.),plane_x=plane)
    typ=result.event['type']
    if typ!='plane':return typ,None
    if result.event['time']<t[-1]-1e-9:return 'plane_before_last_observation',None
    return 'plane',result.event['position'][1:]

def early_inputs(times,positions,cutoff=.10):
    """Select measured frames only; no interpolation or future observations."""
    times=np.asarray(times,float);positions=np.asarray(positions,float)
    mask=times<=times[0]+cutoff+1e-10
    return times[mask]-times[0],positions[mask].copy()

def main():
    all_records=[]; cases=[]
    for match in ['J03WOH','J03WQQ']:
        root=ROOT/f'results/dfl_{match.lower()}_fair'
        with (root/'samples.csv').open(encoding='utf8',newline='') as f: samples=list(csv.DictReader(f))
        with (root/'positions.csv').open(encoding='utf8',newline='') as f: positions=list(csv.DictReader(f))
        for sample in samples:
            sid=sample['event_id']; rows=[r for r in positions if r['event_id']==sid]
            t=np.array([float(r['time_s']) for r in rows]); raw=np.array([[float(r[k]) for k in ('x_m','y_m','z_assumed_m')] for r in rows])
            side=1 if float(sample['goal_x_m'])>0 else -1
            p=raw.copy();p[:,0]=side*(raw[:,0]-raw[0,0]);p[:,1]=side*(raw[:,1]-raw[0,1])
            plane=52.5-side*raw[0,0]
            truth=np.array([side*(float(sample['tracking_goal_y_m'])-raw[0,1]),float(sample['tracking_goal_z_assumed_m'])])
            cases.append({'match':match,'event_id':sid,'outcome':sample['event_outcome'],
                          'shot_type':sample['type_of_shot'],'truth_y_m':float(sample['tracking_goal_y_m']),
                          'truth_z_assumed_m':float(truth[1])})
            for window in [.10]:
                ot,op=early_inputs(t,p,window)
                if len(ot)<2 or t[-1]<=ot[-1]:raise ValueError('sample does not support early prediction')
                for model in ['M0','M1','M2','M3','M4','M5','M5_6_prior']:
                    try:
                        status,hit=polynomial_goal(ot,op,plane) if model=='M2' else physical_goal(model,ot,op,plane)
                    except (ValueError,RuntimeError,np.linalg.LinAlgError,FloatingPointError) as exc:
                        status,hit='error:'+type(exc).__name__,None
                    record={'match':match,'event_id':sid,'outcome':sample['event_outcome'],'shot_type':sample['type_of_shot'],
                      'window_s':window,'input_times_s':','.join(f'{x:.2f}' for x in ot), 'model':model,'status':status,
                      'truth_y_m':float(sample['tracking_goal_y_m']),'truth_z_assumed_m':float(truth[1]),
                      'predicted_y_m':float(side*hit[0]+raw[0,1]) if hit is not None else None,
                      'predicted_z_assumed_m':float(hit[1]) if hit is not None else None,
                      'error_m':float(np.linalg.norm(hit-truth)) if hit is not None else None}
                    all_records.append(record)
    with (OUT/'records.csv').open('w',encoding='utf8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=all_records[0]);writer.writeheader();writer.writerows(all_records)
    summary={'interpretation':'early-frame prediction; later observed positions are retained solely to determine the real goal-plane crossing',
        'selection':'previously fixed DFL event selection; two matches of one dataset',
        'window_rule':'25 Hz: observations at 0, 0.04, 0.08 s only (within 0.10 s)',
        'height_unit':'assumed metres; DFL paper does not confirm unit',
        'M5_6_prior':{'observation_sigma_m':.01,'velocity_prior_mean_m_s':[25,0,5],
           'velocity_prior_sd_m_s':[15,15,15],'spin_prior_mean_rad_s':[0,0,0],
           'spin_prior_sd_rad_s':[30,30,30],'cd0':.18},'cases':cases,'groups':{}}
    for w in [.10]:
        models=['M0','M1','M2','M3','M4','M5','M5_6_prior']
        for m in models:
            group=[r for r in all_records if r['window_s']==w and r['model']==m]
            valid=[r['error_m'] for r in group if r['error_m'] is not None]
            summary['groups'][f'{w}_{m}']={'n':len(group),'status':dict(Counter(r['status'] for r in group)),
              'valid_n':len(valid),'mean_error_m':float(np.mean(valid)) if valid else None,
              'median_error_m':float(np.median(valid)) if valid else None}
        comp=['M0','M1','M3','M4','M5','M5_6_prior'] if w==.05 else models
        ids=[(c['match'],c['event_id']) for c in cases if all(any(r['match']==c['match'] and r['event_id']==c['event_id']
           and r['window_s']==w and r['model']==m and r['status']=='plane' for r in all_records) for m in comp)]
        summary.setdefault('common',{})[str(w)]={'models':comp,'cases':ids,'n':len(ids),
          'mean_error_m':{m:float(np.mean([r['error_m'] for r in all_records if r['window_s']==w and r['model']==m and (r['match'],r['event_id']) in ids])) if ids else None for m in comp}}
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
