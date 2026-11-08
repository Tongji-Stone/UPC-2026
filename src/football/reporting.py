"""Current report inputs, provenance and result serialization (no plotting)."""
from pathlib import Path
from dataclasses import asdict
import csv,json,hashlib,shutil
import numpy as np
from football.physics import PhysicsConfig,coefficients,config_record
from football.inference.four_model_fit import InverseBounds

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'data/current_report';OUT=ROOT/'results/current_report'
MODELS=('M1','M2','M3','M4')
FIT_SAMPLE_ORDINALS={'J03WMX':[3,4,6],'J03WOH':[2,3,4],'J03WR9':[3,4,5]}
FORWARD=[dict(case=c,speed_m_s=v,elevation_deg=a,spin_rad_s=w) for c,v,a,w in [
    ('power',27,8,[0,0,0]),('placement',20,11,[0,0,0]),('curved',24,10,[0,0,35]),
    ('topspin',24,12,[0,35,0]),('backspin',24,12,[0,-35,0]),('chip',14,20,[0,-15,0])]]

def native(x):
    if isinstance(x,np.ndarray):return x.tolist()
    if isinstance(x,np.generic):return x.item()
    raise TypeError(type(x).__name__)

def save_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False,default=native,allow_nan=False)+'\n',encoding='utf-8')

def read_json(path):return json.loads(path.read_text(encoding='utf-8'))
def read_csv(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def save_csv(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    if not rows:raise ValueError('empty table')
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def goal_crossing(rows,plane=52.5):
    for i,r in enumerate(rows):
        if r['X_m']>=plane-1e-10:
            if abs(r['X_m']-plane)<1e-10:return dict(time_s=r['time_s'],position=[plane,r['Y_m'],r['Z_original']],source='measured',frames=[r['frame']])
            if i==0:raise ValueError('no crossing bracket')
            a=rows[i-1];f=(plane-a['X_m'])/(r['X_m']-a['X_m'])
            return dict(time_s=a['time_s']+f*(r['time_s']-a['time_s']),
                position=[plane,a['Y_m']+f*(r['Y_m']-a['Y_m']),a['Z_original']+f*(r['Z_original']-a['Z_original'])],
                source='linear interpolation',frames=[a['frame'],r['frame']])
    raise ValueError('goal crossing absent')

def prepare_inputs(source=None):
    DATA.mkdir(parents=True,exist_ok=True)
    source=Path(source) if source else ROOT.parent/'真实点球数据_CSV与来源_20261108'
    names=['点球信息汇总.csv','完整位置采样.csv','数据来源与必要说明.md']
    for name in names:
        if not (DATA/name).exists():shutil.copy2(source/name,DATA/name)
        elif (source/name).exists() and (source/name).read_bytes()!=(DATA/name).read_bytes():
            raise ValueError('source changed; explicitly refresh the frozen input before recomputing')
    summaries=read_csv(DATA/names[0]);allrows=read_csv(DATA/names[1]);cases=[]
    assert len(summaries)==3 and len(allrows)==39
    for s in summaries:
        raw=[r for r in allrows if r['样本ID']==s['样本ID']]
        rows=[dict(frame=r['源帧号_N'],timestamp=r['源时间戳_T'],time_s=float(r['相对起始时间_s']),
            X_m=float(r['X_m']),Y_m=float(r['Y_m']),Z_original=float(r['Z_原值']),
            x_m=float(r['X_m'])-41.5,y_m=float(r['Y_m']),z_m=float(r['Z_原值']),
            repeated=int(r['是否与上一帧位置重复']),section=r['位置区段']) for r in raw]
        crossing=goal_crossing(rows)
        assert np.allclose(crossing['position'],[52.5,float(s['球门穿越Y_m']),float(s['球门穿越Z_原值'])],atol=1e-10)
        assert abs(crossing['time_s']-float(s['球门穿越相对时间_s']))<1e-10
        ordinals=FIT_SAMPLE_ORDINALS[s['比赛ID']]
        origin=rows[ordinals[0]-1]['time_s']
        for i,r in enumerate(rows,1):
            r['source_time_s']=r['time_s'];r['source_sample_ordinal']=i
            r['time_s']=round(r['source_time_s']-origin,10)
            r['selected_for_current_fit']=i in ordinals
        fitrows=[rows[i-1] for i in ordinals];times=[r['time_s'] for r in fitrows]
        crossing['source_time_s']=crossing['time_s'];crossing['time_s']-=origin
        cases.append(dict(case=s['比赛ID'],sample_id=s['样本ID'],player=s['主罚者'],foot=s['TypeOfShot_原标签'],
            fit_times_s=times,fit_positions_m=[[r[k] for k in ['x_m','y_m','z_m']] for r in fitrows],
            fit_frames=[r['frame'] for r in fitrows],fit_sample_ordinals=ordinals,
            time_origin_source_s=origin,time_origin_frame=fitrows[0]['frame'],samples=rows,source_summary=s,
            actual_mass_kg=None,actual_radius_m=None,goal=dict(crossing,local_position=[11.,*crossing['position'][1:]])))
    cfg=dict(version='current-report-three-penalties-v4-wmx-last-wr9-shift',fit_sample_ordinals=FIT_SAMPLE_ORDINALS,
        position0_m=[0,0,.11],models=list(MODELS),
        forward=FORWARD,physics=dict(mass=.43,radius=.11,air_density=1.2,kinematic_viscosity=1.5e-5,gravity=9.81),
        inverse_bounds=asdict(InverseBounds()),fit=dict(max_nfev=240,rss_allowance_m2=6e-12,coefficient_allowance=1e-8),
        integration=dict(method='DOP853',rtol=1e-10,atol=1e-12,max_step_s=.005,horizon_s=5),
        coordinates=dict(x='X-41.5',y='Y',z='Z_original interpreted as metres and centre height',goal_x_m=11),
        parameter_role='ball and air values are model reference settings, not per-ball measurements',
        original_file_sha256={n:hashlib.sha256((DATA/n).read_bytes()).hexdigest() for n in names})
    save_json(ROOT/'configs/current_report.json',cfg);save_json(DATA/'inputs.json',dict(config=cfg,cases=cases))
    print('prepared 3 penalties, 39 original frames, explicit selected times',flush=True)
    return dict(config=cfg,cases=cases)

def fingerprint():
    files=[ROOT/'src/football/physics/model.py',ROOT/'src/football/physics/integration.py',
        ROOT/'src/football/inference/four_model_fit.py',ROOT/'scripts/four_model_compute.py',DATA/'inputs.json']
    h=hashlib.sha256()
    for p in files:h.update(p.read_bytes().replace(b'\r\n',b'\n'))
    return h.hexdigest()

def trace_rows(f,c):
    rows=[]
    for i,t in enumerate(f.t):
        v,w=f.velocity[i],f.spin[i];cd,cl,re,sp,speed=coefficients(v,w,c)
        rows.append(dict(time_s=t,x_m=f.position[i,0],y_m=f.position[i,1],z_m=f.position[i,2],
            vx=v[0],vy=v[1],vz=v[2],wx=w[0],wy=w[1],wz=w[2],speed_m_s=speed,omega_rad_s=np.linalg.norm(w),
            CD=cd,CL=cl,Re=re,Sp=sp,drag_N=np.linalg.norm(f.forces['drag'][i]),
            lift_N=np.linalg.norm(f.forces['magnus'][i]),torque_Nm=np.linalg.norm(f.torque[i])))
    return rows
