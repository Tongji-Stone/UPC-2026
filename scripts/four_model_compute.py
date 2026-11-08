"""Compute the restructured report from frozen inputs; never draws figures."""
import argparse,csv,json,shutil,hashlib
from pathlib import Path
from dataclasses import replace, asdict
import numpy as np
from scipy.integrate import solve_ivp
from football.physics import PhysicsConfig,simulate,coefficients,config_record,state_derivative
from football.inference.four_model_fit import fit_early, InverseBounds
from coupled_compute import save_json,save_csv,trace_rows

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/structure_v2'
DATA=ROOT/'data/report_v2'
MODELS=('M1','M2','M3','M4')

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def compatible_inverse_cache(path):
    cached=read(path)
    if cached.get('fit',{}).get('fit_bounds',cached.get('fit_bounds')) != asdict(InverseBounds()):
        raise RuntimeError(f'Inverse cache {path} lacks the current bounds; use --output-dir for new results')
    return cached
def csvread(path):
    with path.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))

def prepare():
    """Extract vector marker centres, with axis calibration kept beside the data."""
    import pymupdf
    DATA.mkdir(parents=True,exist_ok=True)
    src=DATA/'Goff_Carre_2009.pdf'
    if not src.exists():shutil.copy2(ROOT.parent/'Trajectory_analysis_of_a_soccer_ball.pdf',src)
    doc=pymupdf.open(src)
    # PDF coordinates in points. Full frame corresponds to x=-.1..1.3 m.
    panels=[dict(case='zero_spin',page=5,figure='11b',frame=[334.933,126.426,429.506,193.012],zlim=[.8,1.4]),
        dict(case='topspin_a',page=7,figure='14a',frame=[72.225,36.330,167.879,103.677],zlim=[.8,1.4],Re=260000,Sp=.49),
        dict(case='topspin_b',page=7,figure='14b',frame=[196.583,36.330,292.236,103.677],zlim=[.8,1.4],Re=275000,Sp=.25),
        dict(case='topspin_c',page=7,figure='14c',frame=[72.225,123.906,167.879,191.252],zlim=[.8,1.4],Re=272000,Sp=.71),
        dict(case='topspin_d',page=7,figure='14d',frame=[196.583,123.906,292.236,191.252],zlim=[.8,1.6],Re=307000,Sp=.24)]
    cases=[]
    for panel in panels:
        x0,y0,x1,y1=panel['frame']; points=[]
        for a in doc[panel['page']-1].get_drawings():
            c=a['fill']; r=a['rect'];cx=(r.x0+r.x1)/2;cy=(r.y0+r.y1)/2
            if (c and c[0]>.8 and c[1]<.2 and c[2]<.2 and 0<r.width<2 and 0<r.height<2
                and x0<cx<x1 and y0<cy<y1):
                if panel['case']=='zero_spin' and 381<cx<384 and 178<cy<181:continue # legend symbol
                x=-.1+(cx-x0)/(x1-x0)*1.4
                z=panel['zlim'][0]+(y1-cy)/(y1-y0)*(panel['zlim'][1]-panel['zlim'][0])
                points.append(dict(x_m=x,y_m=0.,z_m=z,pdf_x_pt=cx,pdf_y_pt=cy))
        points.sort(key=lambda r:r['x_m'])
        assert 10<=len(points)<=20,(panel,len(points))
        for i,p in enumerate(points):p.update(index=i,time_s=.005*i)
        save_csv(DATA/f"{panel['case']}.csv",points)
        physics=dict(mass=.424,radius=.109,air_density=1.2,kinematic_viscosity=1.54e-5)
        if panel['case']=='zero_spin':
            speed=18.;angle=np.deg2rad(22.);spin=[0.,0.,0.]
            launch_basis='published approximate 18 m/s and 22 degrees, Fig.3; first digitized height'
        else:
            speed=panel['Re']*physics['kinematic_viscosity']/(2*physics['radius'])
            # Launch direction from the local spatial tangent of first three measured markers.
            xx=np.array([p['x_m'] for p in points[:3]])
            zz=np.array([p['z_m'] for p in points[:3]])
            poly=np.polyfit(xx-xx[0],zz,2);angle=np.arctan(poly[1])
            spin=[0.,panel['Sp']*speed/physics['radius'],0.] # +y gives downward Magnus
            launch_basis='published initial Re and Sp, Fig.14; tangent of first three digitized markers'
        cases.append(dict(case=panel['case'],physics=physics,
            position=[points[0]['x_m'],0.,points[0]['z_m']],
            velocity=[speed*np.cos(angle),0.,speed*np.sin(angle)],spin=spin,
            launch_basis=launch_basis,observations=f"{panel['case']}.csv",
            measured_range_m=21.9 if panel['case']=='zero_spin' else None,
            comparison='landing range and early trajectory' if panel['case']=='zero_spin' else 'spatial trajectory z(x)',
            time_basis='Fig.3 camera-1 marker spacing 0.005 s; rotating panels scored spatially'))
    save_json(DATA/'controlled_cases.json',cases)
    save_json(DATA/'digitization.json',dict(source='Goff & Carre, AJP 77 (2009) 1020--1027',
        doi='10.1119/1.3197187',source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),
        method='Vector red filled circular markers extracted from PDF, excluding legend; linear axis calibration',
        panels=panels,axis_x_limits_m=[-.1,1.3],
        source_conditions='32-panel ball, m=0.424 kg, diameter=0.218 m, rho=1.2 kg/m3, nu=1.54e-5 m2/s',
        landing_measurement='ground markers; paper estimates range error at most +/-0.05 m',
        timing='cameras unsynchronized; apex markers omitted from time-resolved scoring'))
    inp=read(ROOT/'configs/coupled_problem_b.json')
    inp.update(model='four-model-v2',force_scales=dict(drag=1.,lift=1.),
        fit=dict(max_nfev=240,rss_allowance_m2=6e-12,selection='positions / scales nearest one / smallest M4 spin'),
        parameter_prior=None,observation_noise_model=None)
    inp['physics'].update(use_rotational_drag=False,spin_decay=0.)
    save_json(ROOT/'configs/four_model_problem_b.json',inp)
    save_json(DATA/'problem_b.json',inp)
    # Freeze the previously fixed match selection, coordinate transforms and goal targets.
    cases=[]
    for match in ('J03WOH','J03WQQ'):
        folder=ROOT/f'results/dfl_{match.lower()}_fair'
        shutil.copy2(folder/'samples.csv',DATA/f'{match}_samples.csv')
        shutil.copy2(folder/'positions.csv',DATA/f'{match}_positions.csv')
        for s in csvread(folder/'samples.csv'):
            rows=[r for r in csvread(folder/'positions.csv') if r['event_id']==s['event_id']]
            t=np.array([float(r['time_s']) for r in rows]);t-=t[0]
            raw=np.array([[float(r[k]) for k in ('x_m','y_m','z_assumed_m')] for r in rows])
            side=1 if float(s['goal_x_m'])>0 else -1
            local=raw.copy();local[:,0]=side*(raw[:,0]-raw[0,0]);local[:,1]=side*(raw[:,1]-raw[0,1])
            cases.append(dict(case=f"{match}_{s['event_id']}",shot_type=s['type_of_shot'],
                times_s=t,positions_m=local,plane_x_m=52.5-side*raw[0,0],
                target_yz_m=[side*(float(s['tracking_goal_y_m'])-raw[0,1]),float(s['tracking_goal_z_assumed_m'])],
                source='Sportec Open DFL; fixed existing selection; height treated as metres',physics={}))
    meta=read(ROOT/'results/b_real_penalty/event_and_crossing.json')
    shutil.copy2(ROOT/'results/b_real_penalty/trajectory.csv',DATA/'penalty.csv')
    shutil.copy2(ROOT/'results/b_real_penalty/event_and_crossing.json',DATA/'penalty_metadata.json')
    rows=csvread(DATA/'penalty.csv');raw=np.array([[float(r[k]) for k in ('x_m','y_m','z_raw')] for r in rows])
    local=raw.copy();local[:,:2]-=raw[0,:2]
    cases.append(dict(case='penalty_18232100000995',shot_type='penalty',
        times_s=[float(r['elapsed_s']) for r in rows],positions_m=local,
        plane_x_m=52.5-raw[0,0],target_yz_m=[meta['crossing_y_m']-raw[0,1],meta['crossing_z_raw']],
        source=meta,physics={}))
    save_json(DATA/'match_cases.json',cases)
    print('frozen inputs and five controlled cases prepared',flush=True)

def cfg(model,physics=None):return PhysicsConfig.for_model(model,**(physics or {}))

def fly(position,state,config,plane=11.,span=4.):
    return simulate(position,state[:3],state[3:],config,plane_x=plane,t_span=(0,span),
        rtol=1e-10,atol=1e-12,max_step=.01)

def save_trace(path,f,config):
    rows=trace_rows(f,config)
    for i,r in enumerate(rows):
        r.update(drag_N=float(np.linalg.norm(f.forces['drag'][i])),
                 lift_N=float(np.linalg.norm(f.forces['magnus'][i])))
    save_csv(path,rows)

def controlled():
    records=[]
    for case in read(DATA/'controlled_cases.json'):
        obs=csvread(DATA/case['observations']);x=np.array([float(r['x_m']) for r in obs]);z=np.array([float(r['z_m']) for r in obs])
        for model in MODELS:
            config=cfg(model,case['physics']);state=np.r_[case['velocity'],case['spin']]
            f=fly(case['position'],state,config,plane=100.,span=6.)
            save_trace(OUT/f"forward/{case['case']}_{model}.csv",f,config)
            # Dense output at a spatial plane, avoiding interpolation of coarse solver steps.
            s=solve_ivp(lambda t,y:state_derivative(t,y,config),(0,.2),np.r_[case['position'],state],
                rtol=1e-11,atol=1e-13,max_step=.0005)
            zp=np.interp(x,s.y[0],s.y[2])
            record=dict(case=case['case'],model=model,spatial_rmse_m=float(np.sqrt(np.mean((zp-z)**2))),
                event=f.event,predicted_range_m=float(f.position[-1,0]),configuration=config_record(config),
                measured_range_m=case['measured_range_m'])
            if case['measured_range_m'] is not None:record['range_error_m']=float(f.position[-1,0]-case['measured_range_m'])
            records.append(record)
    save_json(OUT/'forward/summary.json',dict(cases=read(DATA/'controlled_cases.json'),records=records))
    print('forward comparisons saved',flush=True)

def inverse(group,only_case=None):
    if group=='problem':
        a=read(DATA/'problem_b.json');cases=[dict(case='problem_b',times_s=a['times_s'],positions_m=a['positions_m'],
            physics=a['physics'],plane_x_m=a['plane_x_m'],target_yz_m=None)]
    else:cases=read(DATA/'match_cases.json')
    if only_case is not None:cases=[c for c in cases if c['case']==only_case]
    records=[]
    for case in cases:
        t=np.array(case['times_s'][:3]);p=np.array(case['positions_m'][:3])
        for model in MODELS:
            path=OUT/f"{group}/{case['case']}_{model}.json"
            if path.exists():
                records.append(compatible_inverse_cache(path)['record']);continue
            config=cfg(model,case['physics'])
            try:
                fit=fit_early(t,p,config,model)
                config=replace(config,drag_scale=fit['drag_scale'],lift_scale=fit['lift_scale'])
                f=fly(p[0],fit['initial_state'],config,case['plane_x_m'],span=5.)
                save_trace(OUT/f"{group}/{case['case']}_{model}.csv",f,config)
                e=dict(f.event)
                if e['time'] is not None and e['time']<t[-1]:e['type']='terminated_before_last_observation'
                error=float(np.linalg.norm(e['position'][1:]-case['target_yz_m'])) if e['type']=='plane' and case['target_yz_m'] is not None else None
                record=dict(case=case['case'],model=model,status=e['type'] if fit['success'] else 'fit_failure',
                    event=e,error_m=error if fit['success'] else None,fit_converged=fit['success'],
                    candidate_plane_error_m=error,
                    rss_m2=fit['rss_m2'],max_residual_m=fit['max_residual_m'],
                    initial_state=fit['initial_state'],drag_scale=fit['drag_scale'],lift_scale=fit['lift_scale'],
                    active_parameters=fit['active_parameters'],coverage=f.diagnostics,
                    shot_type=case.get('shot_type','competition'),target_yz_m=case['target_yz_m'])
                save_json(path,dict(record=record,fit=fit,input=dict(times_s=t,positions_m=p),
                    source_case=case,configuration=config_record(config),
                    validation_rule='Only first three positions supplied to fit_early; subsequent data used for scoring'))
            except (ValueError,RuntimeError,FloatingPointError) as exc:
                record=dict(case=case['case'],model=model,status='fit_failure',error_m=None,error=str(exc))
                save_json(path,dict(record=record,fit_bounds=asdict(InverseBounds())))
            records.append(record);print(json.dumps(record,default=lambda x:x.tolist(),ensure_ascii=True),flush=True)
        if only_case is None:save_json(OUT/f'{group}/summary.json',dict(records=records))

def other():
    a=compatible_inverse_cache(OUT/'problem/problem_b_M4.json');r=a['record'];state=np.array(r['initial_state']);p=a['input']['positions_m'][0]
    base=cfg('M4',read(DATA/'problem_b.json')['physics'])
    base=replace(base,drag_scale=r['drag_scale'],lift_scale=r['lift_scale'])
    records=[]
    for label,c in [('constant_spin',base),('inertial_torque',replace(base,use_rotational_drag=True,use_viscous_torque=False)),
                    ('inertial_and_viscous',replace(base,use_rotational_drag=True,use_viscous_torque=True))]:
        f=fly(p,state,c)
        save_trace(OUT/f'other/{label}.csv',f,c)
        records.append(dict(case=label,event=f.event,configuration=config_record(c),
            final_spin=float(np.linalg.norm(f.spin[-1])),initial_spin=float(np.linalg.norm(state[3:]))))
    ref=records[0]['event'];high=records[1]['event'];both=records[2]['event']
    delta=float(np.linalg.norm(high['position']-ref['position'])) if high['type']==ref['type']=='plane' else None
    omega=np.linalg.norm(state[3:]);ratio=15*base.kinematic_viscosity/(base.angular_drag_coefficient*base.radius**2*omega) if omega else None
    speed=np.linalg.norm(state[:3]);wind=[]
    for w in (1.,3.,5.):
        wind.append(dict(wind_m_s=w,speed_ratio=w/speed,headwind_q_change_pct=100*((1+w/speed)**2-1),
            tailwind_q_change_pct=100*((1-w/speed)**2-1),crosswind_q_change_pct=100*(w/speed)**2,
            crosswind_airflow_angle_deg=float(np.rad2deg(np.arctan(w/speed)))))
    save_json(OUT/'other/summary.json',dict(records=records,goal_displacement_m=delta,
        displacement_pct_of_11m=None if delta is None else 100*delta/11,
        time_change_pct=100*(high['time']/ref['time']-1) if high['time'] and ref['time'] else None,
        spin_loss_pct=100*(1-records[1]['final_spin']/omega) if omega else 0.,
        viscous_to_inertial_torque_ratio_at_launch=ratio,
        viscous_goal_difference_m=float(np.linalg.norm(both['position']-high['position'])) if both['type']==high['type'] else None,
        wind_estimates=wind,five_percent_dynamic_pressure_wind_threshold_m_s=speed*(np.sqrt(1.05)-1)))
    print('other-factor comparisons saved',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('task',choices=['prepare','forward','problem','matches','other'])
    parser.add_argument('--case',help='optional single inverse case; aggregate is refreshed separately')
    parser.add_argument('--output-dir',help='separate result directory; existing results are preserved')
    args=parser.parse_args();task=args.task
    if args.output_dir: OUT=Path(args.output_dir).resolve()
    {'prepare':prepare,'forward':controlled,'problem':lambda:inverse('problem'),
     'matches':lambda:inverse('matches',args.case),'other':other}[task]()
