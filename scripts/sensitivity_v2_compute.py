"""Standalone sensitivity experiments for the paper's saved M4 representative.

Uses the paper's equations, not the subsequently introduced inverse bounds.
Writes reproducible outputs to results/sensitivity_v2; does not change paper or model sources.
"""
import csv
import hashlib
import json
import math
import sys
import time
from collections import Counter
from dataclasses import replace
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import least_squares
from scipy.special import expit

REPO = Path(__file__).resolve().parents[1]
HERE = REPO / 'results/sensitivity_linear'
DATA = HERE
INPUT = json.loads((REPO / 'configs/sensitivity_v2.json').read_text(encoding='utf-8'))
sys.path.insert(0, str(REPO / 'src'))
from football.physics.model import PhysicsConfig, simulate, state_derivative

SOURCE = REPO / 'results/structure_linear_spin/problem/problem_b_M4.json'
SAVED = json.loads(SOURCE.read_text(encoding='utf-8'))
BASE = np.array(SAVED['record']['initial_state'])
P0 = np.array(INPUT['positions_m'][0], dtype=float)
OBS = np.array(INPUT['positions_m'][1:], dtype=float)
CFG = {key: INPUT['physics'][key] for key in ('mass','radius','rho','nu')}
CFG.update(ad=SAVED['record']['drag_scale'], al=SAVED['record']['lift_scale'])
V0 = np.linalg.norm(BASE[:3])
W0 = np.linalg.norm(BASE[3:])
SCALE = np.array([30., 30., 30., 120., 120., 120.])
PROTECTED = ['_中文版/main.tex', '_中文版/main.pdf', 'paper/main.tex',
             'paper/main.pdf', '_中文版/report_results.tex', 'paper/report_results.tex',
             'src/football/physics/model.py', 'src/football/inference/four_model_fit.py',
             'data/sensitivity_v2/representative_state.json', '探索树.html']


def save_json(name, value):
    (DATA / name).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                      allow_nan=False), encoding='utf-8')


def save_csv(name, rows):
    if not rows:
        return
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with (DATA / name).open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def hashes():
    return {p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in PROTECTED}


def drag0(v):
    return ((.4927-.144)*expit(-(v-12.58)/1.071)+.144
            +(v-23.17)*expit((v-23.17)/1.071)*(.154-.144)/(35.-23.17))


def rhs_factory(spin, cfg):
    m, r, rho, nu, ad, al = [cfg[k] for k in ('mass', 'radius', 'rho', 'nu', 'ad', 'al')]
    wx, wy, wz = spin
    wn = math.sqrt(wx*wx+wy*wy+wz*wz)
    reference=PhysicsConfig.for_model('M4',radius=r,kinematic_viscosity=nu)
    prefactor = .5*rho*math.pi*r*r/m
    def rhs(t, s):
        vx, vy, vz = s[3:]
        speed = math.sqrt(vx*vx+vy*vy+vz*vz)
        drag = prefactor*ad*reference.drag_coefficient*speed
        lift = prefactor*al*reference.lift_coefficient*r
        return [vx, vy, vz,
                -drag*vx+lift*(wy*vz-wz*vy),
                -drag*vy+lift*(wz*vx-wx*vz),
                -9.81-drag*vz+lift*(wx*vy-wy*vx)]
    return rhs


def observed(state, cfg=CFG, tight=False):
    sol = solve_ivp(rhs_factory(state[3:], cfg), (0., .1), np.r_[P0, state[:3]],
                    method='DOP853', t_eval=[.05, .1],
                    rtol=2e-12 if tight else 1e-10,
                    atol=2e-14 if tight else 1e-12, max_step=.025)
    if not sol.success:
        raise RuntimeError(sol.message)
    return sol.y[:3].T


def flight(state, cfg=CFG, p0=P0, method='DOP853', step=.02, tight=False):
    def goal(t, s): return s[0]-11.
    goal.direction = 1
    goal.terminal = True
    def ground(t, s): return s[2]-cfg['radius']
    ground.direction = -1
    ground.terminal = True
    sol = solve_ivp(rhs_factory(state[3:], cfg), (0., 3.), np.r_[p0, state[:3]],
                    method=method, events=[goal, ground],
                    rtol=2e-12 if tight else 1e-10,
                    atol=2e-14 if tight else 1e-12, max_step=step)
    if not sol.success:
        raise RuntimeError(sol.message)
    event = 'plane' if len(sol.t_events[0]) else 'ground' if len(sol.t_events[1]) else 'none'
    point = sol.y[:3, -1]
    return dict(event=event, y=float(point[1]) if event=='plane' else None,
                z=float(point[2]) if event=='plane' else None,
                t=float(sol.t[-1]), end_x=float(point[0]),
                clear=bool(event=='plane' and abs(point[1])<=3.66-cfg['radius']
                           and cfg['radius']<=point[2]<=2.44-cfg['radius']))


def angles(vector):
    return math.atan2(vector[1], vector[0]), math.atan2(vector[2], np.linalg.norm(vector[:2]))


def vector(norm, az, el):
    return norm*np.array([math.cos(el)*math.cos(az), math.cos(el)*math.sin(az), math.sin(el)])


PARAMETERS = [
    ('speed', '初速度大小', 'relative', .05),
    ('yaw', '初速度水平角', 'degree', 1.),
    ('pitch', '初速度仰角', 'degree', 1.),
    ('spin', '自旋大小', 'relative', .05),
    ('spin_yaw', '旋转轴方位角', 'degree', 1.),
    ('spin_pitch', '旋转轴仰角', 'degree', 1.),
    ('ad', '阻力修正系数', 'relative', .05),
    ('al', '升力修正系数', 'relative', .05),
    ('rho', '空气密度', 'relative', .05),
]


def perturb(key, delta):
    state, cfg, p0 = BASE.copy(), CFG.copy(), P0.copy()
    az, el = angles(BASE[:3]); waz, wel = angles(BASE[3:])
    if key=='speed': state[:3] *= 1+delta
    elif key=='yaw': state[:3] = vector(V0, az+math.radians(delta), el)
    elif key=='pitch': state[:3] = vector(V0, az, el+math.radians(delta))
    elif key=='spin': state[3:] *= 1+delta
    elif key=='spin_yaw': state[3:] = vector(W0, waz+math.radians(delta), wel)
    elif key=='spin_pitch': state[3:] = vector(W0, waz, wel+math.radians(delta))
    elif key in ('ad','al','rho'):
        cfg[key] *= 1+delta
    else:
        raise ValueError(f'Unsupported perturbation: {key}; ball mass and radius are fixed')
    return state, cfg, p0


def one_factor(baseline):
    rows, ranks, derivatives = [], [], []
    target = np.array([baseline['y'], baseline['z'], baseline['t']])
    for key, label, unit, comparison in PARAMETERS:
        # Keep the launch-speed sweep inside the paper's <=35 m/s empirical range.
        half = INPUT['one_factor_half_widths'][key]
        values = np.linspace(-half, half, 41)
        for delta in values:
            state, cfg, p0 = perturb(key, delta)
            result = flight(state, cfg, p0)
            row = dict(parameter=key, label=label, unit=unit, delta=float(delta), **result)
            if result['event']=='plane':
                row.update(dy=result['y']-target[0], dz=result['z']-target[1],
                           dt=result['t']-target[2],
                           displacement=math.hypot(result['y']-target[0],result['z']-target[1]))
            rows.append(row)
        pair=[]
        for sign in (-1,1):
            st, cc, pp=perturb(key, sign*comparison)
            pair.append(flight(st,cc,pp))
        ranks.append(dict(parameter=key,label=label,unit=unit,comparison_delta=comparison,
                          minus_y=pair[0]['y'],minus_z=pair[0]['z'],minus_t=pair[0]['t'],
                          plus_y=pair[1]['y'],plus_z=pair[1]['z'],plus_t=pair[1]['t'],
                          max_displacement=max(math.hypot(x['y']-target[0],x['z']-target[1]) for x in pair),
                          max_time_ms=1000*max(abs(x['t']-target[2]) for x in pair)))
        for h in ([.05,.025,.0125] if unit=='degree' else [.002,.001,.0005]):
            outcomes=[]
            for sign in (-1,1):
                st,cc,pp=perturb(key,sign*h); ff=flight(st,cc,pp,tight=True)
                outcomes.append(np.array([ff['y'],ff['z'],ff['t']]))
            derivative=(outcomes[1]-outcomes[0])/(2*h)
            derivatives.append(dict(parameter=key,h=h,dy=derivative[0],dz=derivative[1],dt=derivative[2]))
    save_csv('one_factor.csv',rows); save_csv('comparison.csv',ranks)
    save_csv('local_derivatives.csv',derivatives)
    return rows, ranks, derivatives


def interaction(baseline):
    rows=[]
    for spin_delta in np.linspace(-.15,.15,25):
        for lift_delta in np.linspace(-.15,.15,25):
            state=BASE.copy(); state[3:]*=1+spin_delta
            cfg={**CFG,'al':CFG['al']*(1+lift_delta)}
            f=flight(state,cfg)
            rows.append(dict(spin_delta=float(spin_delta),lift_delta=float(lift_delta),**f,
                displacement=math.hypot(f['y']-baseline['y'],f['z']-baseline['z'])))
    save_csv('interaction.csv',rows)
    return rows


def profile():
    """Continuation in two force scales, six exact early coordinates as constraints."""
    rows=[]; fits=[]; solutions={}; values=np.linspace(1.2,1.8,17)
    order=sorted([(i,j) for i in range(17) for j in range(17)],key=lambda ij:abs(ij[0]-8)+abs(ij[1]-8))
    previous=BASE.copy()
    for count,(i,j) in enumerate(order):
        ad,al=float(values[i]),float(values[j]); cfg={**CFG,'ad':ad,'al':al}
        nearest=min(solutions, key=lambda ij:abs(ij[0]-i)+abs(ij[1]-j)) if solutions else None
        start=solutions[nearest] if nearest is not None else BASE
        def residual(q): return (observed(q*SCALE,cfg)-OBS).ravel()/.11
        candidates=[]
        seeds=[start]
        if i in (0,8,16) and j in (0,8,16):
            seeds += [BASE, np.r_[BASE[:3],-BASE[3:]], np.r_[BASE[:3],BASE[3:]*.55]]
        for seed_id,seed in enumerate(seeds):
            opt=least_squares(residual, np.clip(seed/SCALE,[-0.,-1.4,-1.4,-.5,-.5,-.5],
                         [1.4,1.4,1.4,.5,.5,.5]),
                         bounds=([0.,-1.4,-1.4,-.5,-.5,-.5],[1.4,1.4,1.4,.5,.5,.5]),
                         ftol=2e-11,xtol=2e-11,gtol=2e-11,max_nfev=160)
            state=opt.x*SCALE
            err=float(np.max(abs(observed(state,cfg,tight=True)-OBS)))
            speed=float(np.linalg.norm(state[:3])); spin=float(np.linalg.norm(state[3:]))
            # Wide component limits only keep the search finite; accept a stated total-magnitude scenario.
            accepted=bool(err<=.002 and speed<=35 and spin<=200)
            fits.append(dict(i=i,j=j,seed_id=seed_id,ad=ad,al=al,residual_m=err,
                             speed=speed,spin=spin,success=bool(opt.success),nfev=opt.nfev,
                             accepted=accepted,**{f's{k}':float(v) for k,v in enumerate(state)}))
            if accepted: candidates.append((state,err))
        if candidates:
            solutions[(i,j)]=candidates[0][0]
            for branch,(state,err) in enumerate(candidates):
                if any(np.linalg.norm(state-old[0])<1e-3 for old in candidates[:branch]):continue
                f=flight(state,cfg)
                rows.append(dict(i=i,j=j,branch=branch,ad=ad,al=al,residual_m=err,
                                 speed=float(np.linalg.norm(state[:3])),spin=float(np.linalg.norm(state[3:])),
                                 inner=bool(1.35-1e-9<=ad<=1.65+1e-9 and 1.35-1e-9<=al<=1.65+1e-9),
                                 **{f's{k}':float(v) for k,v in enumerate(state)},**f))
        if (count+1)%25==0: print(f'profile {count+1}/289; feasible nodes {len(solutions)}',flush=True)
    save_csv('profile.csv',rows);save_csv('profile_attempts.csv',fits)
    result={}
    for label,group in [('wide',rows),('inner',[r for r in rows if r['inner']])]:
        plane=[r for r in group if r['event']=='plane']
        result[label]=dict(nodes=len({(r['i'],r['j']) for r in group}),states=len(group),
                           events=dict(Counter(r['event'] for r in group)),
                           y_range=[min(r['y'] for r in plane),max(r['y'] for r in plane)],
                           z_range=[min(r['z'] for r in plane),max(r['z'] for r in plane)],
                           t_range=[min(r['t'] for r in plane),max(r['t'] for r in plane)],
                           spin_range=[min(r['spin'] for r in group),max(r['spin'] for r in group)],
                           max_residual_m=max(r['residual_m'] for r in group),
                           clear=sum(r['clear'] for r in group),
                           max_displacement=max(math.hypot(r['y']-BASELINE['y'],r['z']-BASELINE['z']) for r in plane))
    save_json('profile_summary.json',result)
    return rows,result


def compensation():
    rows=[]
    for key in ('rho',):
        for delta in (-.1,-.05,.05,.1):
            cfg=CFG.copy();cfg[key]*=1+delta
            factor=CFG['rho']/cfg['rho']
            cfg['ad']*=factor;cfg['al']*=factor
            f=flight(BASE,cfg)
            rows.append(dict(parameter=key,delta=delta,ad=cfg['ad'],al=cfg['al'],**f,
                             early_residual_m=float(np.max(abs(observed(BASE,cfg)-OBS))),
                             displacement=math.hypot(f['y']-BASELINE['y'],f['z']-BASELINE['z'])))
    save_csv('compensation.csv',rows)
    return rows


def verification(profile_rows, scan_rows, derivatives, before):
    original=PhysicsConfig.for_model('M4',drag_scale=CFG['ad'],lift_scale=CFG['al'])
    original_flight=simulate(P0,BASE[:3],BASE[3:],original,t_span=(0,3),rtol=2e-12,atol=2e-14,max_step=.005)
    e=original_flight.event
    integration=[]
    representative=[('baseline',BASE,CFG,P0)]
    for key,delta in [('spin',.1),('rho',.1),('al',-.1),('pitch',2.)]:
        state,cfg,p0=perturb(key,delta);representative.append((key,state,cfg,p0))
    planes=[r for r in profile_rows if r['event']=='plane']
    for key in ('y','z'):
        for op in (min,max):
            r=op(planes,key=lambda r:r[key]);state=np.array([r[f's{i}'] for i in range(6)])
            representative.append((f'profile_{key}_{op.__name__}',state,{**CFG,'ad':r['ad'],'al':r['al']},P0))
    for name,state,cfg,p0 in representative:
        f=flight(state,cfg,p0,tight=True,step=.01)
        check=flight(state,cfg,p0,method='RK45',step=.0025,tight=True)
        integration.append(dict(case=name,event=f['event'],other_event=check['event'],
            position_difference_m=math.hypot(f['y']-check['y'],f['z']-check['z']),
            time_difference_s=abs(f['t']-check['t'])))
    # Test independent fast RHS against repository RHS at actual trajectory states and altered parameters.
    rhs_errors=[]
    for name,state,cfg,p0 in representative:
        c=PhysicsConfig.for_model('M4',mass=cfg['mass'],radius=cfg['radius'],
                                  air_density=cfg['rho'],kinematic_viscosity=cfg['nu'],
                                  drag_scale=cfg['ad'],lift_scale=cfg['al'])
        for vscale in (.8,1.,1.05):
            s=np.r_[p0,state[:3]*vscale]
            a=np.array(rhs_factory(state[3:],cfg)(0,s))
            b=state_derivative(0,np.r_[s,state[3:]],c)[:6]
            rhs_errors.append(float(np.max(abs(a-b))))
    finite=[]
    for key,*_ in PARAMETERS:
        d=[r for r in derivatives if r['parameter']==key]
        diff=np.linalg.norm(np.array([d[-1][k]-d[-2][k] for k in ('dy','dz')]))
        norm=np.linalg.norm([d[-1]['dy'],d[-1]['dz']])
        finite.append(dict(parameter=key,relative_change=float(diff/max(norm,1e-12))))
    after=hashes()
    v=dict(baseline_vs_saved_m=math.hypot(BASELINE['y']-SAVED['record']['event']['position'][1],
                                        BASELINE['z']-SAVED['record']['event']['position'][2]),
           baseline_early_residual_m=float(np.max(abs(observed(BASE,tight=True)-OBS))),
           fast_vs_repository_m=math.hypot(BASELINE['y']-e['position'][1],BASELINE['z']-e['position'][2]),
           max_rhs_difference=max(rhs_errors),integrator_comparison=integration,
           finite_difference_refinement=finite,protected_before=before,protected_after=after,
           protected_unchanged=before==after,scan_events=dict(Counter(r['event'] for r in scan_rows)),
           profile_all_early_residual_le_002=all(r['residual_m']<=.002 for r in profile_rows))
    assert v['baseline_vs_saved_m']<1e-7 and v['fast_vs_repository_m']<1e-7
    assert v['max_rhs_difference']<1e-10 and before==after
    assert all(r['position_difference_m']<1e-7 for r in integration)
    save_json('verification.json',v)
    return v


if __name__=='__main__':
    started=time.monotonic();DATA.mkdir(parents=True,exist_ok=True)
    before=hashes()
    BASELINE=flight(BASE,tight=True)
    save_json('baseline.json',dict(state=BASE.tolist(),config=CFG,position=P0.tolist(),
        times=[.05,.1],observations=OBS.tolist(),event=BASELINE,
        source=str(SOURCE.relative_to(REPO)),source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        parameters=[dict(key=k,label=l,unit=u,comparison=d) for k,l,u,d in PARAMETERS],
        choices=dict(profile_scales=[1.2,1.8],profile_grid=17,total_spin_max=200,total_speed_max=35,
                     residual_tolerance_m=.002,position_coordinates_exact=False,random_sampling=False,
                     mass_radius_fixed=True)))
    print('baseline',BASELINE,flush=True)
    scan,ranks,derivatives=one_factor(BASELINE);print('one factor complete',flush=True)
    interaction(BASELINE);print('interaction complete',flush=True)
    profile_rows,summary=profile();print('profile',summary,flush=True)
    compensation()
    verification(profile_rows,scan,derivatives,before)
    save_json('run.json',dict(elapsed_seconds=time.monotonic()-started,
        python=sys.version,numpy=np.__version__,scipy=__import__('scipy').__version__,
        equation_source='paper main.tex Eqs drag, lift, constant-spin motion',
        no_existing_file_writes=True))
    print('verified; elapsed',time.monotonic()-started,flush=True)
