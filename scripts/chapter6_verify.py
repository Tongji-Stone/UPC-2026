"""Audit numerical records and bilingual source; do not re-fit Chapters 4 or 5."""
import hashlib
import re
import subprocess
import numpy as np
from football.reporting import ROOT,read_json,read_csv,save_json
from latex_blocks import read_block


def main():
    out=ROOT/'results/chapter6';tor=read_json(out/'torque/summary.json');fit=read_json(out/'torque/fit.json')
    wind=read_json(out/'wind/summary.json');f=fit['fit']
    checks={}
    def ck(k,v):checks[k]=bool(v)
    ck('six_deterministic_starts',len(f['starts'])==6)
    ck('seven_parameters',fit['active_parameters']==f['active_parameters']==7)
    ck('minimum_position_RSS',abs(f['minimum_search_rss_m2']-min(r['rss_m2'] for r in f['starts'] if 'rss_m2' in r))<1e-15)
    ck('selected_fit_converged',f['success'])
    ck('angular_fixed_at_default',fit['Cangular']==tor['configuration']['angular_drag_coefficient']==1.5)
    ck('spin_reference_30',abs(np.linalg.norm(f['initial_state'][3:])-30)<1e-10)
    ck('same_three_inputs',tor['reference_input']==read_json(ROOT/'results/current_report/problem/problem_b_M4.json')['input'])
    ck('both_models_reach_goal',all(tor[k]['event']['type']=='plane' for k in ['baseline','damped']))
    ck('analytic_and_physical_checks',read_json(out/'verification.json')['all_passed'])
    ck('wind_criterion_5cm',wind['criterion_m']==.05)
    ck('wind_validation_within_limit',wind['max_displacement_at_and_below_bound_m']<=.05)
    ck('wind_rounded_down',wind['reported_bound_m_s']==np.floor(wind['worst']['threshold_m_s']*100)/100)
    ck('wind_just_above_limit',wind['above_bound_worst_displacement_m']>.05)
    ck('72_coarse_directions',all(any(abs(r['azimuth_deg']-a)<1e-8 for r in wind['directions']) for a in range(0,360,5)))
    ck('wind_heading_based',set(r['direction'] for r in wind['cardinal'])=={'tailwind','headwind','left_crosswind','right_crosswind'})
    for name in ['constant_spin','default_damping']:
        rows=read_csv(out/f'torque/{name}.csv');spin=np.array([float(r['omega_rad_s']) for r in rows])
        ck(name+'_monotone',np.max(np.diff(spin))<1e-10)
        ck(name+'_finite_trace',all(np.isfinite([float(v) for v in row.values()]).all() for row in rows))
    protected=['src/football/physics/model.py','src/football/physics/integration.py','src/football/inference/four_model_fit.py',
        'data/current_report','configs/current_report.json','results/current_report/inverse','results/current_report/problem',
        'results/sensitivity_linear','results/monte_carlo_linear','results/chapter5_review']
    ck('original_models_inputs_results_unchanged',subprocess.check_output(['git','diff','HEAD','--',*protected],cwd=ROOT)==b'')
    sources={}
    for folder in ['paper','_中文版']:
        path=ROOT/folder/'main.tex';s=path.read_text(encoding='utf-8');sources[folder]=s
        head=subprocess.check_output(['git','show','HEAD:'+folder+'/main.tex'],cwd=ROOT).decode('utf-8').replace('\r\n','\n')
        for block in ['MODEL_SOLVING','SENSITIVITY_BODY','SENSITIVITY_RESULTS']:
            ck(folder+'_'+block+'_unchanged',read_block(s,block)==read_block(head,block))
        ck(folder+'_single_tex',not re.search(r'\\(?:input|include|lstinputlisting)\b',s))
        ck(folder+'_old_torque_wind_removed',all(x not in s for x in ['torque_comparison.pdf','TorqueResults','WindResultsTable','TorqueDisplacement','WindThreshold']))
        for label in ['fig:torque','tab:torque-goals','tab:wind','eq:rotation-torque','eq:rotation-motion','eq:wind-pressure-bound']:
            ck(folder+'_ref_'+label,('\\ref{'+label+'}' in s or '\\eqref{'+label+'}' in s))
        labels=set(re.findall(r'\\label\{([^}]+)\}',s))|{'LastPage'}
        refs=set(re.findall(r'\\(?:eqref|ref|pageref)\{([^}]+)\}',s))
        ck(folder+'_references_exist',refs<=labels)
        ck(folder+'_torque_table_once',s.count(r'\ChSixTorqueTable')==2)
    equations=lambda s:[re.sub(r'\s+','',x) for x in re.findall(r'\\begin\{equation\}(.*?)\\end\{equation\}',s,re.S)]
    ck('bilingual_equations_equal',equations(sources['paper'])==equations(sources['_中文版']))
    nums=lambda s:re.findall(r'(?<![A-Za-z])[-+]?\d+(?:\.\d+)?',s)
    blocks=lambda s:re.findall(r'\\begin\{tabular\}.*?\\end\{tabular\}',read_block(s,'CHAPTER6_RESULTS'),re.S)
    ck('bilingual_table_numbers_equal',[nums(x) for x in blocks(sources['paper'])]==[nums(x) for x in blocks(sources['_中文版'])])
    sourcepaths=['src/football/physics/model.py','src/football/physics/integration.py','src/football/inference/four_model_fit.py',
        'scripts/chapter6_compute.py','results/current_report/problem/problem_b_M4.json']
    save_json(out/'input.json',dict(observations=tor['reference_input'],reference_state=read_json(ROOT/sourcepaths[-1])['record'],
        torque=dict(Cangular_fixed=1.5,active_parameters=7,spin_direction_starts=6,spin_rad_s=30,max_nfev=240),
        wind=dict(criterion_m=.05,coarse_step_deg=5,fine_step_deg=.5,reported_precision_m_s=.01,constant_horizontal=True),
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sourcepaths}))
    result=dict(all_passed=all(checks.values()),checks=checks,source_sha256={p:hashlib.sha256((ROOT/p/'main.tex').read_bytes()).hexdigest() for p in sources})
    save_json(out/'integration_verification.json',result)
    print(dict(all_passed=result['all_passed'],checks=len(checks),failed=[k for k,v in checks.items() if not v]))
    if not result['all_passed']:raise SystemExit(1)


if __name__=='__main__':main()
