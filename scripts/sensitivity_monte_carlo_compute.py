"""Seeded Monte Carlo of joint perturbations, with fixed ball mass and radius.

This extends the previous one-factor launch experiments. It does not refit
the early positions. Equations are the paper's constant-spin M4 model.
"""
import csv
import gzip
import hashlib
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.special import expit

ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'results/monte_carlo_linear'
DATA=HERE
INPUT=json.loads((ROOT/'configs/sensitivity_v2.json').read_text(encoding='utf-8'))
from sensitivity_v2_compute import BASE,CFG,P0,V0,W0,angles,vector,flight,hashes

SEED=INPUT['monte_carlo']['seed']
COUNT=INPUT['monte_carlo']['samples']
STEP=INPUT['monte_carlo']['dt_s']
KEYS=['speed','yaw','pitch','spin','spin_yaw','spin_pitch','ad','al','rho']
HALF=np.array([INPUT['one_factor_half_widths'][k] for k in KEYS])
LABELS=['初速度大小','初速度水平角','初速度仰角','自旋大小','旋转轴方位角','旋转轴仰角','阻力修正系数','升力修正系数','空气密度']


def write_json(name,data):
    (DATA/name).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')


def draw(count,seed):
    # One row per sample, in a fixed nine-column order. Prefixes are reproducible.
    delta=np.random.default_rng(seed).uniform(-1.,1.,size=(count,9))*HALF
    va,ve=angles(BASE[:3]);wa,we=angles(BASE[3:])
    def vectors(norm,a,e):
        return np.column_stack([norm*np.cos(e)*np.cos(a),norm*np.cos(e)*np.sin(a),norm*np.sin(e)])
    velocity=vectors(V0*(1+delta[:,0]),va+np.radians(delta[:,1]),ve+np.radians(delta[:,2]))
    spin=vectors(W0*(1+delta[:,3]),wa+np.radians(delta[:,4]),we+np.radians(delta[:,5]))
    return dict(delta=delta,velocity=velocity,spin=spin,
                ad=CFG['ad']*(1+delta[:,6]),al=CFG['al']*(1+delta[:,7]),rho=CFG['rho']*(1+delta[:,8]))


def drag0(v):
    return (.4927-.144)*expit(-(v-12.58)/1.071)+.144+(v-23.17)*expit((v-23.17)/1.071)*(.154-.144)/(35-23.17)


def propagate(inputs,step=STEP,progress=False):
    """Vectorized RK4 with cubic-Hermite interpolation of each crossing event."""
    n=len(inputs['ad'])
    state=np.column_stack([np.tile(P0,(n,1)),inputs['velocity']])
    event=np.full(n,2,dtype=np.int8)  # plane=0, ground=1, no event=2
    end=np.full((n,3),np.nan);times=np.full(n,np.nan)
    active=np.ones(n,dtype=bool)
    wn=np.linalg.norm(inputs['spin'],axis=1)
    from football.physics import PhysicsConfig
    reference=PhysicsConfig.for_model('M4',radius=CFG['radius'],kinematic_viscosity=CFG['nu'])
    pref=.5*math.pi*CFG['radius']**2/CFG['mass']
    def rhs(s,ids):
        vel=s[:,3:]; speed=np.linalg.norm(vel,axis=1)
        d=pref*inputs['rho'][ids]*inputs['ad'][ids]*reference.drag_coefficient*speed
        l=pref*inputs['rho'][ids]*inputs['al'][ids]*reference.lift_coefficient*CFG['radius']
        acc=-d[:,None]*vel+l[:,None]*np.cross(inputs['spin'][ids],vel)
        acc[:,2]-=9.81
        return np.column_stack([vel,acc])
    def hermite(a,b,fa,fb,u):
        u=u[:,None]
        return (2*u**3-3*u**2+1)*a+(u**3-2*u**2+u)*step*fa+(-2*u**3+3*u**2)*b+(u**3-u**2)*step*fb
    def event_point(a,b,fa,fb,coordinate,target):
        u=np.clip((target-a[:,coordinate])/(b[:,coordinate]-a[:,coordinate]),0,1)
        for _ in range(5):
            point=hermite(a[:,:3],b[:,:3],fa[:,:3],fb[:,:3],u)
            derivative=((6*u*u-6*u)*a[:,coordinate]+(3*u*u-4*u+1)*step*fa[:,coordinate]
                        +(-6*u*u+6*u)*b[:,coordinate]+(3*u*u-2*u)*step*fb[:,coordinate])
            u=np.clip(u-(point[:,coordinate]-target)/derivative,0,1)
        return u,hermite(a[:,:3],b[:,:3],fa[:,:3],fb[:,:3],u)
    for k in range(math.ceil(3/step)):
        ids=np.flatnonzero(active)
        if not len(ids):break
        a=state[ids]
        k1=rhs(a,ids); k2=rhs(a+step*.5*k1,ids); k3=rhs(a+step*.5*k2,ids); k4=rhs(a+step*k3,ids)
        b=a+step*(k1+2*k2+2*k3+k4)/6
        plane=(a[:,0]<11)&(b[:,0]>=11)
        ground=(a[:,2]>CFG['radius'])&(b[:,2]<=CFG['radius'])&(b[:,5]<0)
        hit=plane|ground
        if hit.any():
            h=np.flatnonzero(hit); hid=ids[h]
            fb=rhs(b[h],hid)
            ug=np.full(len(h),np.inf);up=np.full(len(h),np.inf)
            pg=np.full((len(h),3),np.nan);pp=pg.copy()
            for mask,coord,target,us,points in [(plane[h],0,11.,up,pp),(ground[h],2,CFG['radius'],ug,pg)]:
                if mask.any():
                    us[mask],points[mask]=event_point(a[h][mask],b[h][mask],k1[h][mask],fb[mask],coord,target)
            first_plane=up<=ug
            times[hid]=k*step+np.minimum(up,ug)*step
            end[hid]=np.where(first_plane[:,None],pp,pg)
            event[hid]=np.where(first_plane,0,1)
            active[hid]=False
        state[ids]=b
        if progress and (k+1)%50==0:print(f't={step*(k+1):.3f}s; remaining={active.sum()}',flush=True)
    if active.any():end[active]=state[active,:3]
    clear=(event==0)&(abs(end[:,1])<=3.66-CFG['radius'])&(end[:,2]>=CFG['radius'])&(end[:,2]<=2.44-CFG['radius'])
    return dict(event=event,point=end,time=times,clear=clear)


def describe(result):
    mask=result['event']==0;points=result['point'][mask,1:3];t=result['time'][mask]
    origin=np.array([2.682644507905514,1.9592312099350713])
    covariance=np.cov(points,rowvar=False);center=points.mean(axis=0)
    d=points-center
    d2=np.einsum('ni,ij,nj->n',d,np.linalg.inv(covariance),d)
    q=float(np.quantile(d2,.95))
    out=dict(count=len(mask),plane=int(mask.sum()),ground=int((result['event']==1).sum()),
             none=int((result['event']==2).sum()),clear=int(result['clear'].sum()),
             nonclear_at_plane=int((mask&~result['clear']).sum()),
             y_range=[float(points[:,0].min()),float(points[:,0].max())],
             z_range=[float(points[:,1].min()),float(points[:,1].max())],
             t_range=[float(t.min()),float(t.max())],
             y_central_95=np.quantile(points[:,0],[.025,.975]).tolist(),
             z_central_95=np.quantile(points[:,1],[.025,.975]).tolist(),
             t_central_95=np.quantile(t,[.025,.975]).tolist(),
             mean=center.tolist(),median=np.median(points,axis=0).tolist(),
             std=points.std(axis=0,ddof=1).tolist(),correlation=float(np.corrcoef(points,rowvar=False)[0,1]),
             max_displacement=float(np.linalg.norm(points-origin,axis=1).max()),
             ellipse_95=dict(center=center.tolist(),covariance=covariance.tolist(),
                             empirical_d2_threshold=q,empirical_coverage=float((d2<=q).mean())),
             clear_fraction=float(result['clear'].mean()))
    out['outside_top_count']=int((mask&(result['point'][:,2]>2.44-CFG['radius'])).sum())
    out['outside_side_count']=int((mask&(abs(result['point'][:,1])>3.66-CFG['radius'])).sum())
    return out


def save_samples(inputs,result):
    np.savez_compressed(DATA/'samples.npz',**inputs,**result)
    with gzip.open(DATA/'samples.csv.gz','wt',encoding='utf-8-sig',newline='') as stream:
        writer=csv.writer(stream)
        writer.writerow(['id','mass_kg','radius_m']+['delta_'+k for k in KEYS]+
                        ['y_m','z_m','time_s','event','clear'])
        for i in range(len(result['event'])):
            writer.writerow([i,CFG['mass'],CFG['radius'],*inputs['delta'][i],
                             *result['point'][i,1:3],result['time'][i],
                             ['plane','ground','none'][result['event'][i]],bool(result['clear'][i])])


def main():
    DATA.mkdir(parents=True,exist_ok=True); started=time.monotonic();before=hashes()
    inputs=draw(COUNT,SEED);print('inputs ready',flush=True)
    result=propagate(inputs,progress=True);save_samples(inputs,result)
    summary=describe(result);write_json('summary.json',summary)
    prefixes=[]
    for n in [1000,5000,10000,25000,50000,100000]:
        prefixes.append(dict(n=n,**describe({k:v[:n] for k,v in result.items()})))
    write_json('convergence.json',prefixes)
    replicas=[]
    for seed in [20261109,20261110]:
        r=propagate(draw(10000,seed));replicas.append(dict(seed=seed,**describe(r)))
        print('replicate',seed,'complete',flush=True)
    write_json('independent_seeds.json',replicas)
    # Adaptive DOP853 uses a separately written scalar RHS from the prior report.
    selected=set(np.random.default_rng(20261111).choice(COUNT,size=64,replace=False).tolist())
    for column in (1,2):selected.update([int(result['point'][:,column].argmin()),int(result['point'][:,column].argmax())])
    selected.update([int(result['time'].argmin()),int(result['time'].argmax())])
    comparisons=[]
    for i in sorted(selected):
        state=np.r_[inputs['velocity'][i],inputs['spin'][i]]
        cfg={**CFG,'rho':inputs['rho'][i],'ad':inputs['ad'][i],'al':inputs['al'][i]}
        ref=flight(state,cfg,tight=True,step=.005)
        distance=float(np.hypot(ref['y']-result['point'][i,1],ref['z']-result['point'][i,2]))
        comparisons.append(dict(id=i,difference_m=distance,time_difference_s=abs(ref['t']-result['time'][i]),
                                same_event=ref['event']==['plane','ground','none'][result['event'][i]]))
    half_inputs={k:v[:2000] for k,v in inputs.items()}
    half=propagate(half_inputs,step=STEP/2)
    step_error=float(np.linalg.norm(half['point'][:,1:3]-result['point'][:2000,1:3],axis=1).max())
    base_inputs=dict(velocity=BASE[:3][None,:],spin=BASE[3:][None,:],
                     ad=np.array([CFG['ad']]),al=np.array([CFG['al']]),rho=np.array([CFG['rho']]))
    baseline=propagate(base_inputs);ref=flight(BASE,tight=True)
    rng_repeat=np.array_equal(draw(1000,SEED)['delta'],inputs['delta'][:1000])
    checks=dict(seed=SEED,count=COUNT,dt=STEP,mass_kg=CFG['mass'],radius_m=CFG['radius'],
        ball_parameters_fixed=True,random_prefix_reproduced=rng_repeat,
        parameters_within_bounds=bool((abs(inputs['delta'])<=HALF).all()),
        maximum_sampled_speed_m_s=float(np.linalg.norm(inputs['velocity'],axis=1).max()),
        adaptive_integrator_comparisons=comparisons,
        maximum_adaptive_difference_m=max(r['difference_m'] for r in comparisons),
        half_step_check_count=2000,maximum_half_step_difference_m=step_error,
        baseline_difference_m=float(np.hypot(baseline['point'][0,1]-ref['y'],baseline['point'][0,2]-ref['z'])),
        protected_unchanged=before==hashes(),elapsed_seconds=time.monotonic()-started,
        python=sys.version,numpy=np.__version__,sampling='Independent uniform in each declared perturbation range',
        definition='First forward crossing of x=11 m, or descending first ground contact',
        observation_handling='Joint perturbation of the launch conditions; no refit of early observed positions',
        parameters=[dict(key=k,label=l,half_width=float(h),unit='degrees' if k in ('yaw','pitch','spin_yaw','spin_pitch') else 'relative')
                    for k,l,h in zip(KEYS,LABELS,HALF)])
    assert checks['protected_unchanged'] and rng_repeat and checks['parameters_within_bounds']
    assert checks['maximum_sampled_speed_m_s']<35
    assert checks['maximum_adaptive_difference_m']<1e-6 and step_error<1e-6
    assert all(r['same_event'] for r in comparisons)
    write_json('verification.json',checks)
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
    print('verified; seconds',time.monotonic()-started,flush=True)


if __name__=='__main__':main()
