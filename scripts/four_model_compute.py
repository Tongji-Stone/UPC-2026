"""Current paper: 24 prescribed flights, 12 real inversions and a curved-shot torque comparison."""
import argparse
from dataclasses import replace
import numpy as np
from football.physics import PhysicsConfig,simulate,config_record,state_derivative
from football.physics.integration import observed_trajectory
from football.inference.four_model_fit import fit_early,InverseBounds
from football.reporting import (ROOT,DATA,OUT,MODELS,read_json,save_json,save_csv,
                                trace_rows,prepare_inputs,fingerprint)

def inputs():return read_json(DATA/'inputs.json')
def config(model):return PhysicsConfig.for_model(model,**inputs()['config']['physics'])
def flight(position,state,cfg,**tolerances):
    return simulate(position,state[:3],state[3:],cfg,plane_x=11,t_span=(0,5),
                    rtol=tolerances.get('rtol',1e-10),atol=tolerances.get('atol',1e-12),
                    max_step=tolerances.get('max_step',.005))

def forward():
    dataset=inputs();records=[]
    for case in dataset['config']['forward']:
        a=np.deg2rad(case['elevation_deg']);v=case['speed_m_s']*np.array([np.cos(a),0,np.sin(a)])
        state=np.r_[v,case['spin_rad_s']]
        for model in MODELS:
            cfg=config(model)
            if model == 'M3':
                reference=config('M4')
                acceleration=state_derivative(0,np.r_[dataset['config']['position0_m'],state],reference)[3:6]
                cfg=replace(cfg,constant_acceleration=tuple(acceleration))
            f=flight(dataset['config']['position0_m'],state,cfg)
            record=dict(case=case['case'],model=model,initial_state=state,event=f.event,
                configuration=config_record(cfg),settings=case,coverage=f.diagnostics)
            save_csv(OUT/f"forward/{case['case']}_{model}.csv",trace_rows(f,cfg));records.append(record)
    save_json(OUT/'forward/summary.json',dict(records=records,source_fingerprint=fingerprint()))
    print('saved 24 forward flights',flush=True)

def inverse(only=None):
    signature=fingerprint()
    for case in inputs()['cases']:
        if only and case['case']!=only:continue
        t=np.array(case['fit_times_s']);p=np.array(case['fit_positions_m'])
        for model in MODELS:
            path=OUT/f"inverse/{case['case']}_{model}.json"
            if path.exists() and read_json(path).get('source_fingerprint')==signature:
                print(f"cached {case['case']} {model}",flush=True);continue
            cfg=config(model)
            # A stale candidate must not leave a curve or validation file behind.
            for suffix in ['.csv','_validation.csv']:
                (OUT/f"inverse/{case['case']}_{model}{suffix}").unlink(missing_ok=True)
            try:
                fit=fit_early(t,p,cfg,model,max_nfev=inputs()['config']['fit']['max_nfev'],bounds=InverseBounds())
                cfg=replace(cfg,drag_scale=fit['drag_scale'],lift_scale=fit['lift_scale'])
                if model == 'M3':
                    cfg=replace(cfg,constant_acceleration=tuple(fit['constant_acceleration']))
                state=np.array(fit['initial_state']);f=flight(p[0],state,cfg)
                event=dict(f.event);end=float(f.t[-1]);fit_physical=end>=t[-1]-1e-9
                status=('early_contact' if not fit_physical else 'fit_limit' if not fit['success'] else event['type'])
                goal=case['goal'];target=np.array(goal['local_position'])
                endpoint_error=float(np.linalg.norm(event['position'][1:]-target[1:])) if event['type']=='plane' else None
                future=[r for r in case['samples'] if r['time_s']>t[-1]+1e-10 and
                        r['time_s']<=min(goal['time_s'],end)+1e-10 and r['X_m']<=52.5+1e-10]
                errors=[]
                if future:
                    times=np.r_[0,[r['time_s'] for r in future]]
                    pred=observed_trajectory(times,p[0],state,cfg,rtol=1e-10,atol=1e-12)[1:,:3]
                    truth=np.array([[r[k] for k in ['x_m','y_m','z_m']] for r in future])
                    errors=np.linalg.norm(pred-truth,axis=1)
                    save_csv(OUT/f"inverse/{case['case']}_{model}_validation.csv",[
                        dict(time_s=r['time_s'],frame=r['frame'],error_3d_m=float(e)) for r,e in zip(future,errors)])
                record=dict(case=case['case'],model=model,status=status,fit_converged=fit['success'],
                    physical_fit_interval=fit_physical,event=event,early_max_residual_m=fit['max_residual_m'],
                    early_rss_m2=fit['rss_m2'],initial_state=state,drag_scale=cfg.drag_scale,lift_scale=cfg.lift_scale,
                    future_sample_count=len(future),future_rmse_3d_m=float(np.sqrt(np.mean(np.asarray(errors)**2))) if len(errors) else None,
                    goal_error_m=endpoint_error,goal_time_error_s=event['time']-goal['time_s'] if event['type']=='plane' else None,
                    scored_goal_error_m=endpoint_error if fit['success'] and fit_physical else None,
                    at_parameter_bound=fit['at_parameter_bound'],
                    constant_acceleration=fit.get('constant_acceleration'),
                    fitted_cd=cfg.drag_coefficient*cfg.drag_scale if model=='M4' else None,
                    fitted_alpha=cfg.lift_coefficient*cfg.lift_scale if model=='M4' else None)
                save_csv(OUT/f"inverse/{case['case']}_{model}.csv",trace_rows(f,cfg))
                save_json(path,dict(source_fingerprint=signature,record=record,fit=fit,
                    fit_input=dict(times_s=t,positions_m=p,frames=case['fit_frames'],
                        sample_ordinals=case['fit_sample_ordinals'],time_origin_source_s=case['time_origin_source_s']),
                    configuration=config_record(cfg),validation_target=goal))
            except (ValueError,RuntimeError,FloatingPointError) as e:
                record=dict(case=case['case'],model=model,status='fit_failure',message=str(e),
                    goal_error_m=None,future_rmse_3d_m=None,future_sample_count=0)
                save_json(path,dict(source_fingerprint=signature,record=record))
            print(f"{case['case']} {model}: {record['status']}",flush=True)

def other():
    case=next(c for c in inputs()['config']['forward'] if c['case']=='curved')
    a=np.deg2rad(case['elevation_deg']);state=np.r_[case['speed_m_s']*np.array([np.cos(a),0,np.sin(a)]),case['spin_rad_s']]
    cfg=config('M4');records=[]
    for label,cc in [('constant_spin',cfg),('inertial_torque',replace(cfg,use_rotational_drag=True,use_viscous_torque=False)),
                     ('inertial_and_viscous',replace(cfg,use_rotational_drag=True,use_viscous_torque=True))]:
        f=flight([0,0,.11],state,cc);save_csv(OUT/f'other/{label}.csv',trace_rows(f,cc))
        records.append(dict(case=label,event=f.event,initial_spin=float(np.linalg.norm(state[3:])),
            final_spin=float(np.linalg.norm(f.spin[-1])),configuration=config_record(cc)))
    e,h,b=[r['event'] for r in records];omega=np.linalg.norm(state[3:]);v=case['speed_m_s']
    result=dict(reference_case='curved',initial_position=[0,0,.11],initial_state=state,records=records,
        goal_displacement_m=float(np.linalg.norm(h['position']-e['position'])),
        displacement_pct_of_11m=100*float(np.linalg.norm(h['position']-e['position']))/11,
        spin_loss_pct=100*(1-records[1]['final_spin']/omega),time_change_pct=100*(h['time']/e['time']-1),
        viscous_to_inertial_ratio=15*cfg.kinematic_viscosity/(cfg.angular_drag_coefficient*cfg.radius**2*omega),
        viscous_goal_difference_m=float(np.linalg.norm(b['position']-h['position'])),
        wind_threshold_m_s=v*(np.sqrt(1.05)-1),wind=[dict(wind_m_s=w,
            head_pct=100*((1+w/v)**2-1),tail_pct=100*((1-w/v)**2-1),cross_pct=100*(w/v)**2,
            angle_deg=float(np.rad2deg(np.arctan(w/v)))) for w in [1,3,5]])
    save_json(OUT/'other/summary.json',result);print('curved-shot torque and wind comparisons saved',flush=True)

def collect():
    records=[]
    for case in inputs()['cases']:
        for model in MODELS:
            a=read_json(OUT/f"inverse/{case['case']}_{model}.json")
            if a['source_fingerprint']!=fingerprint():raise ValueError('stale inverse cache')
            records.append(a['record'])
    save_json(OUT/'inverse/summary.json',dict(records=records,source_fingerprint=fingerprint()))
    print('collected all 12 inverse outcomes',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('task',choices=['prepare','forward','inverse','other','collect']);p.add_argument('--case')
    args=p.parse_args();{'prepare':prepare_inputs,'forward':forward,'inverse':lambda:inverse(args.case),'other':other,'collect':collect}[args.task]()
