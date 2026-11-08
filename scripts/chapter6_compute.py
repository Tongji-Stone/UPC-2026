"""Chapter 6 fixed-default torque inversion and horizontal-wind bounds.

No paper generation or plotting; Chapters 4 and 5 inputs/results are read only.
"""
import argparse
from dataclasses import replace
import hashlib
import numpy as np
from scipy.optimize import brentq
from football.physics import PhysicsConfig,simulate,config_record,rotational_torque,forces
from football.inference.four_model_fit import fit_early,InverseBounds
from football.reporting import ROOT,read_json,save_json,save_csv,trace_rows

OUT=ROOT/'results/chapter6'
REFERENCE=ROOT/'results/current_report/problem/problem_b_M4.json'
FORCE=False


def reference():
    ref=read_json(REFERENCE);r=ref['record']
    cfg=PhysicsConfig.for_model('M4',mass=.43,radius=.11,air_density=1.2,kinematic_viscosity=1.5e-5,gravity=9.81)
    cfg=replace(cfg,drag_scale=r['fitted_cd']/cfg.drag_coefficient,lift_scale=r['fitted_alpha']/cfg.lift_coefficient)
    return ref,np.array(ref['input']['positions_m'][0]),np.array(r['initial_state']),cfg


def flight(pos,state,cfg,rtol=1e-10,atol=1e-12,max_step=.005):
    return simulate(pos,state[:3],state[3:],cfg,plane_x=11,t_span=(0,5),rtol=rtol,atol=atol,max_step=max_step)


def event_record(f):
    return dict(event=f.event,final_spin_rad_s=float(np.linalg.norm(f.spin[-1])),
        Re_range=f.diagnostics['Re_range'])


def damping_record(cfg):
    record=config_record(cfg)
    record['sources']['angular_drag']='Cangular fixed at the MuJoCo default 1.5; not an inverse parameter'
    return record


def torque():
    ref,pos,state,baseline=reference();base=flight(pos,state,baseline)
    save_csv(OUT/'torque/constant_spin.csv',trace_rows(base,baseline))
    inputs=read_json(ROOT/'configs/current_report.json')
    # Unit force scales are the identical reference starting point used in Chapter 4.
    cfg=replace(baseline,drag_scale=1.,lift_scale=1.,use_rotational_drag=True,
        use_viscous_torque=False,angular_drag_coefficient=1.5)
    fitpath=OUT/'torque/fit.json'
    old=read_json(fitpath) if fitpath.exists() else {}
    if old.get('mode')=='fixed_Cangular_1.5' and not FORCE:fit=old
    else:
        fitted_state=fit_early(ref['input']['times_s'],ref['input']['positions_m'],cfg,'M4',
            bounds=InverseBounds(**inputs['inverse_bounds']),max_nfev=240)
        fit=dict(mode='fixed_Cangular_1.5',Cangular=1.5,active_parameters=7,fit=fitted_state)
    save_json(fitpath,fit)
    best=fit['fit'];sc=np.array(best['initial_state'])
    fitted=replace(cfg,drag_scale=best['drag_scale'],lift_scale=best['lift_scale'],
        angular_drag_coefficient=1.5,use_rotational_drag=True,use_viscous_torque=False)
    damped=flight(pos,sc,fitted)
    save_csv(OUT/'torque/default_damping.csv',trace_rows(damped,fitted))
    visc=flight(pos,sc,replace(fitted,use_viscous_torque=True))
    save_csv(OUT/'torque/with_viscosity.csv',trace_rows(visc,replace(fitted,use_viscous_torque=True)))
    result=dict(reference_input=ref['input'],baseline=event_record(base),damped=event_record(damped),
        fitted_initial_state=sc,configuration=damping_record(fitted),fit=best,
        fitted_CD=fitted.drag_coefficient*fitted.drag_scale,fitted_alpha=fitted.lift_coefficient*fitted.lift_scale,
        goal_displacement_m=float(np.linalg.norm(damped.position[-1,1:]-base.position[-1,1:])),
        spin_loss_pct=100*(1-np.linalg.norm(damped.spin[-1])/30),
        arrival_difference_s=float(damped.t[-1]-base.t[-1]),
        viscous_goal_difference_m=float(np.linalg.norm(visc.position[-1,1:]-damped.position[-1,1:])),
        viscous_to_quadratic_reference=15*fitted.kinematic_viscosity/(1.5*fitted.radius**2*30),
        viscous_to_quadratic_fitted=15*fitted.kinematic_viscosity/(1.5*fitted.radius**2*np.linalg.norm(damped.spin[-1])))
    save_json(OUT/'torque/summary.json',result)
    print('torque summary',result['goal_displacement_m'],result['spin_loss_pct'],flush=True)


def wind():
    _,pos,state,cfg=reference();base=flight(pos,state,cfg);target=base.position[-1,1:]
    checkpoint=OUT/'wind/checkpoint.json'
    saved=read_json(checkpoint) if checkpoint.exists() and not FORCE else dict(samples=[],directions=[],unbracketed=[])
    samples=saved['samples'];directions=saved['directions'];unbracketed=set(saved['unbracketed'])
    cache={(round(r['wind_m_s'],11),round(r['azimuth_deg']%360,8)):r['displacement_m'] for r in samples}

    def displacement(w,angle):
        key=(round(float(w),11),round(float(angle)%360,8))
        if key in cache:return cache[key]
        a=np.deg2rad(angle);cc=replace(cfg,wind=(w*np.cos(a),w*np.sin(a),0.))
        f=flight(pos,state,cc)
        d=float(np.linalg.norm(f.position[-1,1:]-target)) if f.event['type']=='plane' else float('inf')
        cache[key]=d
        samples.append(dict(wind_m_s=float(w),azimuth_deg=float(angle)%360,displacement_m=d,
            event_type=f.event['type'],y_m=float(f.position[-1,1]),z_m=float(f.position[-1,2]),time_s=float(f.t[-1])))
        return d

    def threshold(angle):
        prev=0.
        for w in np.arange(.1,10.001,.1):
            if displacement(w,angle)>=.05:
                return float(brentq(lambda z:displacement(z,angle)-.05,prev,w,xtol=1e-6))
            prev=w
        # A lower bound above the search cap cannot control the weak-wind minimum.
        unbracketed.add(float(angle)%360)
        return 10.

    for angle in np.arange(0,360,5):
        if not any(r['azimuth_deg']==angle for r in directions):
            directions.append(dict(azimuth_deg=float(angle),threshold_m_s=threshold(angle),
                threshold_is_lower_bound=bool(float(angle)%360 in unbracketed)))
            save_json(checkpoint,dict(samples=samples,directions=directions,unbracketed=sorted(unbracketed)))
        if angle%30==0:print('wind direction',angle,flush=True)
    coarse=min(directions,key=lambda r:r['threshold_m_s'])
    for angle in np.arange(coarse['azimuth_deg']-5,coarse['azimuth_deg']+5.001,.5):
        if angle%5 and not any(abs(r['azimuth_deg']-float(angle)%360)<1e-8 for r in directions):directions.append(dict(azimuth_deg=float(angle)%360,threshold_m_s=threshold(angle),
            threshold_is_lower_bound=bool(float(angle)%360 in unbracketed)))
    worst=min(directions,key=lambda r:r['threshold_m_s'])
    bound=float(np.floor(worst['threshold_m_s']*100)/100)
    validated=[]
    for angle in sorted(set([r['azimuth_deg'] for r in directions])):
        for factor in [.25,.5,.75,1.]:
            validated.append(displacement(bound*factor,angle))
    assert max(validated)<=.05+1e-9
    heading=float(np.rad2deg(np.arctan2(state[1],state[0])))
    cards=[]
    for name,relative in [('tailwind',0.),('headwind',180.),('left_crosswind',90.),('right_crosswind',270.)]:
        a=(heading+relative)%360;limit=threshold(a)
        cards.append(dict(direction=name,azimuth_deg=a,threshold_m_s=limit,
            reported_bound_m_s=float(np.floor(limit*100)/100),threshold_is_lower_bound=a in unbracketed))
    above=displacement(bound+.01,worst['azimuth_deg'])
    save_csv(OUT/'wind/evaluations.csv',samples)
    save_json(OUT/'wind/summary.json',dict(fixed_initial_state=state,configuration=config_record(cfg),
        reference_crossing=base.event,directions=directions,cardinal=cards,worst=worst,
        reported_bound_m_s=bound,max_displacement_at_and_below_bound_m=max(validated),
        above_bound_worst_displacement_m=above,
        criterion_m=.05,coarse_step_deg=5,fine_step_deg=.5))
    save_json(checkpoint,dict(samples=samples,directions=directions,unbracketed=sorted(unbracketed)))
    print('wind bound',bound,'m/s',flush=True)


def verify():
    ref,pos,state,cfg=reference();tor=read_json(OUT/'torque/summary.json');p=tor['configuration']
    cc=replace(cfg,use_rotational_drag=True,use_viscous_torque=False,angular_drag_coefficient=p['angular_drag_coefficient'],
        drag_scale=p['drag_scale'],lift_scale=p['lift_scale'])
    sc=np.array(tor['fitted_initial_state']);f=flight(pos,sc,cc)
    analytic_errors=[]
    for c in [0.,1.5,3.]:
        ctest=replace(cc,angular_drag_coefficient=c);test=flight(pos,sc,ctest)
        k=8*np.pi*cc.air_density*c*cc.radius**5/(15*cc.moment_of_inertia)
        analytic=30/(1+k*30*test.t)
        analytic_errors.append(float(np.max(abs(np.linalg.norm(test.spin,axis=1)-analytic))))
    fine=flight(pos,sc,cc,rtol=2e-12,atol=2e-14,max_step=.0025)
    checks=dict(spin_analytic_max_error_rad_s=max(analytic_errors),
        endpoint_tolerance_difference_m=float(np.linalg.norm(fine.position[-1]-f.position[-1])),
        zero_spin_torque=bool(np.all(rotational_torque([0,0,0],cc)==0)),
        damping_power_negative=bool(rotational_torque(sc[3:],cc)@sc[3:]<=0),
        torque_normalization_error=float(abs(np.linalg.norm(rotational_torque(sc[3:],cc))-8*np.pi/15*cc.air_density*cc.angular_drag_coefficient*cc.radius**5*30**2)),
        baseline_endpoint_difference_m=float(np.linalg.norm(flight(pos,state,cfg).position[-1]-np.array(ref['record']['event']['position']))))
    checks['all_passed']=(checks['spin_analytic_max_error_rad_s']<1e-7 and checks['endpoint_tolerance_difference_m']<1e-7
        and checks['zero_spin_torque'] and checks['damping_power_negative'] and checks['torque_normalization_error']<1e-12
        and checks['baseline_endpoint_difference_m']<1e-7)
    save_json(OUT/'verification.json',checks);assert checks['all_passed'];print(checks,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('task',choices=['torque','wind','verify']);parser.add_argument('--force',action='store_true')
    args=parser.parse_args();FORCE=args.force;globals()[args.task]()
