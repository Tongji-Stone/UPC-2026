"""Generate the complete comparison CSV and summaries, without plotting."""
import csv
import json
import math
from pathlib import Path
import numpy as np
from aerodynamic_formulas import *

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/sources/aerodynamic_parameters'
OUT=ROOT/'data/processed/aerodynamic_parameters'
R=.11; NU=1.5e-5; RHO=1.2
MODELS={
 'G10_CD_v':('CD','Goff2010','Eq3','speed_only',lambda v,s,n:cd_g10_v(v)),
 'G10_CD_piecewise':('CD','Goff2010','Eq3+4','v_Sp_piecewise',lambda v,s,n:cd_g10(v,s)),
 'KL18_CD_v':('CD','Kiratidis2018','Eq5 Table1','speed_only',lambda v,s,n:cd_kl18_v(v)),
 'KL18_CD_ReSp':('CD','Kiratidis2018','Eq5+7','Re_Sp',lambda v,s,n:cd_kl18(v,s)),
 'KL18_CL_Sp':('CL','Kiratidis2018','Eq8','intermediate_reference_curve',lambda v,s,n:cl_kl18_sp(s)),
 'KL18_CL_ReSp':('CL','Kiratidis2018','Eq9','Re_Sp',lambda v,s,n:cl_kl18(v,s,nu=n)),
 'Repo_CD_constant':('CD','UPC_snapshot','PhysicsConfig','existing_default',lambda v,s,n:.25),
 'Repo_CL_constant':('CL','UPC_snapshot','PhysicsConfig','existing_default',lambda v,s,n:.2),
}
FIELDS=['case','coefficient','model','ball','source','equation','formula_class','v_m_s','Re','Sp','omega_rad_s','spin_rev_s','nu_m2_s','model_value','reference_value','difference','absolute_error','reference_read_bound','reference_point_ids','acquisition','validity','note']


def write_csv(path,rows,fields=None):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)


def read_points():
    with (SRC/'asai2007_digitized.csv').open(encoding='utf-8-sig') as f: p=list(csv.DictReader(f))
    for row in p:
        for k in ['Re','Sp','value','coefficient_read_bound']:row[k]=float(row[k])
    return [x for x in p if x['ball']=='Teamgeist']


def reference_at(points,coef,re,sp):
    """Piecewise linear in Sp, then Re; only within both bracketing rows."""
    p=[p for p in points if p['coefficient']==coef and p['figure']!='fig4']
    rr=sorted(set(p['Re'] for p in p))
    if not rr[0]<=re<=rr[-1]: return None,[],None,'Re_outside_measured_range'
    bracket=sorted(set([max(x for x in rr if x<=re),min(x for x in rr if x>=re)]))
    values=[];ids=[];bounds=[]
    for level in bracket:
        q=sorted([x for x in p if x['Re']==level],key=lambda x:x['Sp'])
        if not q[0]['Sp']<=sp<=q[-1]['Sp']:return None,[],None,'Sp_outside_bracketing_rows'
        low=max((x for x in q if x['Sp']<=sp),key=lambda x:x['Sp'])
        high=min((x for x in q if x['Sp']>=sp),key=lambda x:x['Sp'])
        values.append(float(np.interp(sp,[x['Sp'] for x in q],[x['value'] for x in q])))
        ids.extend([low['point_id'],high['point_id']]);bounds +=[low['coefficient_read_bound'],high['coefficient_read_bound']]
    # Bound on coefficient coordinate only; source CSV also supplies x-coordinate bounds.
    return float(np.interp(re,bracket,values)),sorted(set(ids)),max(bounds),'interpolated_from_digitized_points'


def main():
    OUT.mkdir(parents=True,exist_ok=True);points=read_points();rows=[]
    positions=np.array([[0,0,.11],[1.50,.45,.44],[2.96,.86,.74]])
    h=.05;a=(positions[2]-2*positions[1]+positions[0])/h**2
    v0=(positions[1]-positions[0])/h-a*h/2
    cases=[]
    for t in [0,.05,.1]:
        v=float(np.linalg.norm(v0+a*t))
        for nu in [NU,1.54e-5]:cases.append(dict(t_s=t,v_m_s=v,Re=2*R*v/nu,nu_m2_s=nu))
    vrep=float(np.linalg.norm((positions[2]-positions[0])/(2*h)))
    def add(case,model,v,sp,nu=NU,re=None,reference=None,ids=(),bound=None,acquisition='formula',validity='',note=''):
        c,s,e,kind,fn=MODELS[model];value=float(fn(v,sp,nu));re=2*R*v/nu if re is None else re
        d=value-reference if reference is not None else None
        rows.append(dict(case=case,coefficient=c,model=model,ball='Teamgeist',source=s,equation=e,formula_class=kind,v_m_s=v,Re=re,Sp=sp,omega_rad_s=sp*v/R,spin_rev_s=sp*v/R/(2*math.pi),nu_m2_s=nu,model_value=value,reference_value=reference,difference=d,absolute_error=abs(d) if d is not None else None,reference_read_bound=bound,reference_point_ids=';'.join(ids),acquisition=acquisition,validity=validity,note=note))
    # Original experimental conditions: legend implies v=22,24,26,28,30 m/s,
    # r=.11 and nu ~= 1.45e-5. Preserve Re labels exactly, and retain this nu.
    for p in points:
        re,sp,coef=p['Re'],p['Sp'],p['coefficient'];nu=1.45e-5
        v=re*nu/(2*R)
        models=(['G10_CD_v','KL18_CD_v','Repo_CD_constant'] if p['figure']=='fig4' else
                ['G10_CD_piecewise','KL18_CD_ReSp','Repo_CD_constant'] if coef=='CD' else
                ['KL18_CL_Sp','KL18_CL_ReSp','Repo_CL_constant'])
        for m in models:
            add('experimental_'+p['figure'],m,v,sp,nu,re,p['value'],[p['point_id']],p['coefficient_read_bound'],'PDF_vector_marker_center','at_published_experimental_condition','nu reconstructed from 22-30 m/s and legend Re; marker reading is not lab raw data')
    for v in np.linspace(5,35,301):
        for m in ['G10_CD_v','KL18_CD_v']:add('nonspin_curve',m,float(v),0,validity='published_speed_fit')
    for case,nu in [('problem_main',NU),('problem_nu154',1.54e-5)]:
        re=2*R*vrep/nu
        for sp in np.round(np.arange(0,1.0001,.005),6):
            for m in ['G10_CD_piecewise','KL18_CD_ReSp','KL18_CL_Sp','KL18_CL_ReSp','Repo_CD_constant','Repo_CL_constant']:
                coef=MODELS[m][0];ref,ids,bound,valid=reference_at(points,coef,re,float(sp))
                note='main_scan' if sp<=.35 else 'extended_Sp_scan'
                if sp>.35:note+='; high_spin_extrapolation'
                if m=='G10_CD_piecewise' and sp>.3:note+='; beyond_G10_reported_spin_fit_range'
                if m.startswith('KL18') and sp>.315:note+='; beyond_Asai_spin_fit_data_range'
                if m=='KL18_CL_Sp':note+='; Eq8 intermediate, not independent CL(v) law'
                if m=='G10_CD_piecewise' and sp<=.05:note+='; Eq3 low_spin branch'
                add(case,m,vrep,float(sp),nu,re,ref,ids,bound,'formula_vs_interpolated_reference' if ref is not None else 'formula',valid,note)
    for sp in np.round(np.arange(0,1.0001,.005),6):
        for visc in [False,True]:
            cv,cw,q,w=cq_and_torque(vrep,float(sp),viscous=visc)
            for coefficient,val in [('CQ_v',cv),('CQ_omega',cw),('Q_Nm',q)]:
                rows.append(dict(case='torque',coefficient=coefficient,model='MuJoCo381_total' if visc else 'MuJoCo381_highRe',ball='sphere',source='MuJoCo3.8.1+Grad2026',equation='sphere reduction of angular drag',formula_class='derived_normalization',v_m_s=vrep,Re=2*R*vrep/NU,Sp=float(sp),omega_rad_s=w,spin_rev_s=w/(2*math.pi),nu_m2_s=NU,model_value=val,reference_value=None,difference=None,absolute_error=None,reference_read_bound=None,reference_point_ids='',acquisition='source_code_derivation',validity='normalization_undefined_at_zero_spin' if coefficient=='CQ_omega' and sp==0 else 'phenomenological_unvalidated_for_football_torque',note='c_ang=1.5 software default; no torque observations in Asai2007'))
    for src,c,note in [('Goff2010','CL','reports trajectory-derived CL points; no closed CL formula'),('Goff2012','CL','summary of experimental CL; no new closed formula'),('Goff2012','CD','reports CD approximately .17 for a nonspinning 32-panel ball; Fig5 fit refers to Goff2011, not a new formula'),('Asai2007','CQ','no spin-down torque measurements')]:
        row={k:None for k in FIELDS};row.update(case='evidence_inventory',coefficient=c,model=src+'_not_provided',source=src,validity='not_provided',note=note);rows.append(row)
    write_csv(OUT/'参数对照.csv',rows,FIELDS)
    metrics=[]
    exp=[r for r in rows if r['case'].startswith('experimental_')]
    for scope,selected in [('all_measured',exp),('high_Re_ge394482',[r for r in exp if r['Re']>=394482])]:
        for case in sorted(set(r['case'] for r in selected)):
            for model in sorted(set(r['model'] for r in selected if r['case']==case)):
                q=[r for r in selected if r['case']==case and r['model']==model];e=np.array([r['difference'] for r in q])
                metrics.append(dict(scope=scope,case=case,model=model,n=len(q),MAE=float(np.mean(abs(e))),RMSE=float(np.sqrt(np.mean(e*e))),max_abs=float(np.max(abs(e))),bias=float(np.mean(e))))
    write_csv(OUT/'error_summary.csv',metrics)
    write_csv(OUT/'problem_conditions.csv',cases)
    decay=[]
    inertia=2/3*.43*R**2;omega0=.2*vrep/R
    for ca in [.75,1.5,3.]:
        k=8*math.pi/15*RHO*ca*R**5/inertia
        for t in np.linspace(0,.45,200):
            decay.append(dict(t_s=float(t),Cangular=ca,omega_initial_rad_s=omega0,inertia_kg_m2=inertia,omega_fraction=1/(1+k*omega0*t),assumption='thin_shell_quadratic_torque_only'))
    write_csv(OUT/'spin_decay_sensitivity.csv',decay)
    selected=[]
    for sp in [.05,.1,.2,.3,.35,.5,1.]:
        selected.append(dict(Sp=sp,CD_G10=cd_g10(vrep,sp),CD_KL18=cd_kl18(vrep,sp),CL_KL18=cl_kl18(vrep,sp),CL_reference_power=cl_kl18_sp(sp),CQ_v=cq_and_torque(vrep,sp)[0],Q_Nm=cq_and_torque(vrep,sp)[2]))
    summary=dict(v0=v0.tolist(),acceleration=a.tolist(),representative_speed=vrep,representative_Re=2*R*vrep/NU,Re_max_experiment=455172,Re_excess_percent=100*(2*R*vrep/NU/455172-1),rows=len(rows),experimental_points=len(points),selected=selected,metrics=metrics,conditions=cases)
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
