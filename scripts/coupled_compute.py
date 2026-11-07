"""Compute all paper results with one coupled nine-state model; plotting is separate."""
import argparse
import csv
import json
from collections import Counter
from dataclasses import replace
from pathlib import Path
import numpy as np
from football.physics import PhysicsConfig,simulate,coefficients,config_record
from football.inference.coupled_fit import fit_initial_state,observed_trajectory

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/coupled_model'
INPUT=json.loads((ROOT/'configs/coupled_problem_b.json').read_text(encoding='utf-8'))


def native(value):
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,np.generic):return value.item()
    raise TypeError(type(value).__name__)


def save_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False,default=native,allow_nan=False),encoding='utf-8')


def save_csv(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def configuration():
    return PhysicsConfig.for_model('M5',**INPUT['physics'])


def predict(position,state,config,plane=11.,max_step=.005,rtol=1e-9,atol=1e-11):
    return simulate(position,state[:3],state[3:],config,plane_x=plane,
                    t_span=(0,3),max_step=max_step,rtol=rtol,atol=atol)


def crossing(flight,last_observation_time):
    event=dict(flight.event)
    if event['time'] is not None and event['time']<last_observation_time-1e-8:
        event['type']='terminated_before_last_observation'
    return dict(event=event,coverage=flight.diagnostics)


def trace_rows(flight,config):
    rows=[]
    for i,t in enumerate(flight.t):
        p,v,w=flight.position[i],flight.velocity[i],flight.spin[i]
        cd,cl,re,sp,speed=coefficients(v,w,config)
        qnorm=float(np.linalg.norm(flight.torque[i]));cq=qnorm/(.5*config.air_density*speed**2*np.pi*config.radius**3) if speed>0 else None
        row=dict(time_s=t,x_m=p[0],y_m=p[1],z_m=p[2],vx=v[0],vy=v[1],vz=v[2],
                 wx=w[0],wy=w[1],wz=w[2],omega_rad_s=np.linalg.norm(w),speed_m_s=speed,
                 Re=re,Sp=sp,CD=cd,CL=cl,CQ_v=cq,torque_Nm=qnorm,
                 Qx=flight.torque[i,0],Qy=flight.torque[i,1],Qz=flight.torque[i,2],
                 alphax=flight.angular_acceleration[i,0],alphay=flight.angular_acceleration[i,1],alphaz=flight.angular_acceleration[i,2],
                 energy_J=.5*config.mass*(v@v)+config.mass*config.gravity*p[2]+.5*config.moment_of_inertia*(w@w))
        rows.append(row)
    return rows


def problem():
    cfg=configuration();t=np.array(INPUT['times_s']);p=np.array(INPUT['positions_m'])
    fit=fit_initial_state(t,p,cfg,max_nfev=INPUT['fit']['max_nfev'])
    candidates=[]
    for index,candidate in enumerate(fit['candidates']):
        flight=predict(p[0],candidate['initial_state'],cfg)
        candidates.append(dict(candidate=index,fit_start=candidate['start'],rss_m2=candidate['rss_m2'],
                               initial_state=candidate['initial_state'],**crossing(flight,t[-1])))
        save_csv(OUT/f'problem/trajectory_candidate_{index}.csv',trace_rows(flight,cfg))
    state=fit['best']['initial_state'];flight=predict(p[0],state,cfg)
    tight=predict(p[0],state,cfg,max_step=.0025,rtol=1e-11,atol=1e-13)
    convergence=float(np.linalg.norm(flight.event['position']-tight.event['position'])) if flight.event['position'] is not None and tight.event['position'] is not None else None
    fitted_positions=observed_trajectory(t,p[0],state,cfg)[:,:3]
    save_csv(OUT/'problem/observations.csv',[dict(time_s=ti,x_m=xyz[0],y_m=xyz[1],z_m=xyz[2],
        fit_x_m=pr[0],fit_y_m=pr[1],fit_z_m=pr[2]) for ti,xyz,pr in zip(t,p,fitted_positions)])
    result=dict(input=INPUT,configuration=config_record(cfg),fit=fit,candidate_predictions=candidates,
        best_prediction=crossing(flight,t[-1]),initial_spin_norm=float(np.linalg.norm(state[3:])),
        final_spin_norm=float(np.linalg.norm(flight.spin[-1])),convergence_position_difference_m=convergence,
        meaning='conditional unweighted best fit; no probability or confidence interval')
    save_json(OUT/'problem/summary.json',result)
    print(json.dumps(dict(case='problem',rss=fit['best']['rss_m2'],state=state,
        candidate_count=len(candidates),event=flight.event,condition=fit['best']['condition_number']),default=native),flush=True)


def real():
    cfg=configuration();records=[]
    for match in ('J03WOH','J03WQQ'):
        source=ROOT/f'results/dfl_{match.lower()}_fair'
        with (source/'samples.csv').open(encoding='utf-8') as f:samples=list(csv.DictReader(f))
        with (source/'positions.csv').open(encoding='utf-8') as f:positions=list(csv.DictReader(f))
        for sample in samples:
            sid=sample['event_id'];rows=[r for r in positions if r['event_id']==sid]
            all_t=np.array([float(r['time_s']) for r in rows]);all_t-=all_t[0]
            raw=np.array([[float(r[k]) for k in ('x_m','y_m','z_assumed_m')] for r in rows])
            side=1 if float(sample['goal_x_m'])>0 else -1
            local=raw.copy();local[:,0]=side*(raw[:,0]-raw[0,0]);local[:,1]=side*(raw[:,1]-raw[0,1])
            mask=all_t<=.10+1e-10;t=all_t[mask];p=local[mask]
            assert len(t)==3 and np.allclose(t,[0,.04,.08])
            plane=52.5-side*raw[0,0]
            truth=np.array([side*(float(sample['tracking_goal_y_m'])-raw[0,1]),float(sample['tracking_goal_z_assumed_m'])])
            label=f'{match}_{sid}'
            try:
                fit=fit_initial_state(t,p,cfg,max_nfev=INPUT['fit']['max_nfev'])
                candidates=[]
                for candidate in fit['candidates']:
                    f=predict(p[0],candidate['initial_state'],cfg,plane=plane)
                    prediction=crossing(f,t[-1]);event=prediction['event']
                    error=float(np.linalg.norm(event['position'][1:]-truth)) if event['type']=='plane' else None
                    candidates.append(dict(fit_start=candidate['start'],error_m=error,**prediction))
                best=candidates[0]
                record=dict(match=match,event_id=sid,shot_type=sample['type_of_shot'],
                    status=best['event']['type'],input_times_s=t.tolist(),fit_rss_m2=fit['best']['rss_m2'],
                    max_fit_residual_m=fit['best']['max_component_residual_m'],
                    fit_success=fit['best']['success'],near_best_candidates=len(candidates),
                    condition_number=fit['best']['condition_number'],error_m=best['error_m'],
                    predicted_local_y_m=best['event']['position'][1] if best['event']['type']=='plane' else None,
                    predicted_z_m=best['event']['position'][2] if best['event']['type']=='plane' else None,
                    actual_local_y_m=truth[0],actual_z_assumed_m=truth[1],
                    above_35_m_s=best['coverage']['above_35_m_s'],
                    above_A07_global_Sp=best['coverage']['above_A07_global_Sp'])
                save_json(OUT/f'real/{label}.json',dict(record=record,fit=fit,predictions=candidates,
                    input_times_s=t,input_positions_m=p,goal_plane_x_m=plane,
                    target_local_yz_m=truth,configuration=config_record(cfg),
                    selection='unchanged fixed event selection; later coordinates not used in fitting'))
            except (RuntimeError,ValueError,FloatingPointError) as exc:
                record=dict(match=match,event_id=sid,shot_type=sample['type_of_shot'],status='fit_failure',error=str(exc),error_m=None)
            records.append(record)
            print(json.dumps(record,default=native),flush=True)
    valid=[r['error_m'] for r in records if r.get('error_m') is not None]
    save_json(OUT/'real/summary.json',dict(records=records,n=len(records),status=dict(Counter(r['status'] for r in records)),
        successful_crossings=len(valid),mean_error_m=float(np.mean(valid)) if valid else None,
        median_error_m=float(np.median(valid)) if valid else None,
        height_unit='treated as metres as in the saved DFL extraction',
        configuration=config_record(cfg),input_rule='only 0,0.04,0.08 s; future coordinates reserved for the target'))
    keys=sorted(set(k for record in records for k in record));save_csv(OUT/'real/records.csv',[{k:r.get(k) for k in keys} for r in records])


def sensitivity():
    summary=json.loads((OUT/'problem/summary.json').read_text(encoding='utf-8'))
    state=np.array(summary['fit']['best']['initial_state']);cfg=configuration();p=INPUT['positions_m'][0]
    rows=[]
    sweeps=dict(speed_scale=np.linspace(.95,1.05,11),azimuth_deg=np.linspace(-2,2,9),
                spin_scale=np.linspace(0,2,11),angular_drag_scale=np.linspace(.5,2,7))
    for factor,values in sweeps.items():
        for value in values:
            q=state.copy();cc=cfg
            if factor=='speed_scale':q[:3]*=value
            elif factor=='azimuth_deg':
                a=np.deg2rad(value);q[:2]=np.array([[np.cos(a),-np.sin(a)],[np.sin(a),np.cos(a)]])@q[:2]
            elif factor=='spin_scale':q[3:]*=value
            else:cc=replace(cfg,angular_drag_coefficient=cfg.angular_drag_coefficient*value)
            flight=predict(p,q,cc);e=flight.event
            rows.append(dict(factor=factor,value=value,event=e['type'],
                y_m=e['position'][1] if e['type']=='plane' else None,z_m=e['position'][2] if e['type']=='plane' else None,
                time_s=e['time'],above_35_m_s=flight.diagnostics['above_35_m_s'],
                max_Sp=flight.diagnostics['Sp_range'][1],final_spin_norm=np.linalg.norm(flight.spin[-1])))
    save_csv(OUT/'sensitivity/scan.csv',rows)
    save_json(OUT/'sensitivity/summary.json',dict(reference_state=state,configuration=config_record(cfg),
        meaning='controlled deterministic perturbations, not parameter probabilities',
        sweeps={k:v.tolist() for k,v in sweeps.items()},groups={factor:dict(n=len(group),
            reached=sum(r['event']=='plane' for r in group),
            y_range=[min(r['y_m'] for r in group if r['y_m'] is not None),max(r['y_m'] for r in group if r['y_m'] is not None)],
            z_range=[min(r['z_m'] for r in group if r['z_m'] is not None),max(r['z_m'] for r in group if r['z_m'] is not None)])
            for factor in sweeps for group in [[r for r in rows if r['factor']==factor]]}))
    print('sensitivity complete',flush=True)


def surface():
    summary=json.loads((OUT/'problem/summary.json').read_text(encoding='utf-8'))
    velocity=np.array(summary['fit']['best']['initial_state'][:3]);p=INPUT['positions_m'][0]
    cfg=replace(configuration(),use_magnus=False)
    def smooth(re,sp):
        if re<=0:return 0.,0.
        return (24/re+2.6*(re/5)/(1+(re/5)**1.52)+.411*(re/2.63e5)**(-7.94)/(1+(re/2.63e5)**(-8))+re**.8/4.61e5),0.
    rows=[];cases=[]
    for name,config in [('Teamgeist KL18',cfg),('Smooth sphere',replace(cfg,coefficients=smooth))]:
        flight=predict(p,np.r_[velocity,np.zeros(3)],config)
        cases.append(dict(law=name,event=flight.event,initial_cd=coefficients(velocity,[0,0,0],config)[0],coverage=flight.diagnostics))
        rows.extend(dict(law=name,**row) for row in trace_rows(flight,config))
    save_csv(OUT/'surface/trajectories.csv',rows)
    save_json(OUT/'surface/summary.json',dict(cases=cases,initial_velocity=velocity,
        meaning='equal nonspinning initial states; coefficient-law comparison, not matched surface CFD',
        sources={'Teamgeist':'Kiratidis-Leinweber 2018 zero-spin complete drag','Smooth sphere':'Paudel-Yan 2026 Eq 26'}))
    print('surface complete',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--case',choices=['all','problem','real','sensitivity','surface'],default='all')
    args=parser.parse_args()
    for name,function in [('problem',problem),('real',real),('sensitivity',sensitivity),('surface',surface)]:
        if args.case in ('all',name):function()
