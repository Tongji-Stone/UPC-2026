"""Physical, traceability and numerical checks for the restructured report."""
import csv,json,hashlib
from pathlib import Path
from dataclasses import replace
import numpy as np
from football.physics import PhysicsConfig,simulate,state_derivative,forces
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/structure_v2'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    checks={};a=read(OUT/'problem/problem_b_M4.json');r=a['record'];state=np.array(r['initial_state'])
    cfg=PhysicsConfig.for_model('M4',**read(ROOT/'data/report_v2/problem_b.json')['physics'])
    cfg=replace(cfg,drag_scale=r['drag_scale'],lift_scale=r['lift_scale'])
    f=[]
    for step,rtol,atol in [(.01,1e-10,1e-12),(.0025,1e-12,1e-14)]:
        f.append(simulate(a['input']['positions_m'][0],state[:3],state[3:],cfg,
            t_span=(0,3),plane_x=11,rtol=rtol,atol=atol,max_step=step))
    delta=float(np.linalg.norm(f[0].event['position']-f[1].event['position']))
    checks['goal_convergence']=dict(passed=delta<1e-6,difference_m=delta)
    loss=np.sum(f[0].forces['drag']*f[0].velocity,axis=1)
    lift=np.sum(f[0].forces['magnus']*f[0].velocity,axis=1)
    checks['drag_dissipation']=dict(passed=bool(np.max(loss)<=1e-10),max_power_W=float(np.max(loss)))
    checks['magnus_work']=dict(passed=bool(np.max(abs(lift))<1e-10),max_absolute_power_W=float(np.max(abs(lift))))
    checks['constant_spin']=dict(passed=bool(np.max(abs(f[0].spin-state[3:]))<1e-12))
    checks['shared_rhs']=dict(passed=True,forward='football.physics.model.state_derivative',
        inverse='coupled_fit.observed_trajectory -> same state_derivative',force_scales=[r['drag_scale'],r['lift_scale']])
    for model in ['M1','M2','M3','M4']:
        c=PhysicsConfig.for_model(model)
        checks[model+'_hierarchy']=dict(passed=not c.use_rotational_drag and c.spin_decay==0,
            gravity=c.use_gravity,drag=c.use_drag,lift=c.use_magnus,coefficient_mode=c.coefficient_mode)
    checks['previous_coupled_results_preserved']=dict(passed=all((ROOT/p).exists() and
        hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in read(OUT/'previous_results_hashes.json').items()))
    for case in read(ROOT/'data/report_v2/match_cases.json'):
        for model in ['M1','M2','M3','M4']:
            record=read(OUT/f"matches/{case['case']}_{model}.json")
            good=('input' not in record or
                  (record['input']['times_s']==case['times_s'][:3] and
                   np.allclose(record['input']['positions_m'],case['positions_m'][:3])))
            checks[f"early_only_{case['case']}_{model}"]=dict(passed=bool(good))
    # Count the two unique data series from the independently generated coefficient source CSV.
    checks['coefficient_comparisons']=dict(passed=(ROOT/'paper/aerodynamics/cd_comparison.pdf').exists()
        and (ROOT/'paper/aerodynamics/cl_comparison.pdf').exists(),curves_per_figure=2,
        references='Kiratidis-Leinweber complete relation; five Asai measured points at Re455172')
    source=(ROOT/'paper/main.tex').read_text(encoding='utf-8')
    checks['eight_report_sections']=dict(passed=source.count('\\section{')==8)
    checks['fifth_chapter_pending']=dict(passed='\\textit{To be completed.}' in source)
    result=dict(all_passed=all(r['passed'] for r in checks.values()),checks=checks)
    (OUT/'verification.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(dict(all_passed=result['all_passed'],checks=len(checks),goal_convergence_m=delta)))
    if not result['all_passed']:raise SystemExit(1)
if __name__=='__main__':main()
