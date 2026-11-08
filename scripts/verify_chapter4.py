"""Audit Chapter 4 inputs, saved predictions, bilingual equations and figure dependencies.

Checks saved sources and results; compilation diagnostics are recorded separately by
the desktop editor. No claim is made about an older exported main.pdf.
"""
import hashlib
import re
import subprocess
import numpy as np
from football.reporting import ROOT,DATA,OUT,read_json,read_csv,save_json,fingerprint
from latex_blocks import read_block


def main():
    checks={}; crossings=[]; documents={}
    def check(name,value):checks[name]=bool(value)
    data=read_json(DATA/'inputs.json')
    check('39_source_frames',sum(len(c['samples']) for c in data['cases'])==39)
    signature=fingerprint()
    for case in data['cases']:
        check(case['case']+'_times',np.allclose(case['fit_times_s'],[0,.04,.08]))
        for model in ['M1','M2','M3','M4']:
            p=OUT/f"inverse/{case['case']}_{model}.json";saved=read_json(p);r=saved['record']
            name=case['case']+'_'+model
            check(name+'_current_source',saved['source_fingerprint']==signature)
            check(name+'_selected_inputs',np.allclose(saved['fit_input']['positions_m'],case['fit_positions_m']) and saved['fit_input']['frames']==case['fit_frames'])
            check(name+'_fit_interval',r['physical_fit_interval'])
            check(name+'_selection',saved['fit']['active_parameters']==dict(M1=3,M2=4,M3=6,M4=7)[model])
            error=None;pred=None
            if r['event']['type']=='plane':
                pred=r['event']['position'][1:]
                error=float(np.linalg.norm(np.array(pred)-case['goal']['local_position'][1:]))
                check(name+'_crossing_error',abs(error-r['scored_goal_error_m'])<1e-10)
            else:check(name+'_no_false_goal',r['scored_goal_error_m'] is None)
            crossings.append(dict(case=case['case'],model=model,status=r['status'],observed=case['goal']['local_position'][1:],predicted=pred,distance_m=error))
    for folder in ['paper','_中文版']:
        source=(ROOT/folder/'main.tex').read_text(encoding='utf-8');documents[folder]=source
        body=source.split(r'\begin{document}',1)[1].split(r'\begin{thebibliography}',1)[0]
        labels=re.findall(r'\\label\{([^}]+)\}',source)
        refs=set(re.findall(r'\\(?:ref|eqref|pageref)\{([^}]+)\}',source))
        check(folder+'_references',refs<=set(labels)|{'LastPage'})
        check(folder+'_unique_labels',len(labels)==len(set(labels)))
        bib=set(re.findall(r'\\bibitem\{([^}]+)\}',source))
        cites={key for group in re.findall(r'\\cite\{([^}]+)\}',body) for key in group.split(',')}
        check(folder+'_bibliography_in_body',bib==cites)
        check(folder+'_single_file',not re.search(r'\\(?:input|include|lstinputlisting)\b',source))
        check(folder+'_removed_outputs',all(x not in source for x in ['PenaltyErrorSummaryTable','tab:models','penalty_spatial_overview.pdf','penalty_m4_dynamics.pdf']))
        check(folder+'_observation_table_once',source.count(r'\PenaltyObservationTable')==2)
        for macro,count in [('PlacementCrossingTable',8),('PowerCrossingTable',4)]:
            table=source.split('\\newcommand{\\'+macro+'}{',1)[1].split(r'\end{table}',1)[0]
            check(folder+'_'+macro+'_rows',len(re.findall(r'^(?:Case |案例)[123] &',table,re.M))==count)
        for fig in ['placement-paths','placement-dynamics','power-paths','power-dynamics','problem-m4']:
            check(folder+'_cites_'+fig,r'\ref{fig:'+fig+'}' in body)
        dependencies=re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}',source)
        search=[ROOT/folder,ROOT/'paper/assets',ROOT/'paper/aerodynamics',OUT/'figures',ROOT/'results/sensitivity_linear/figures']
        check(folder+'_images_exist',all(any((base/name).exists() for base in search) for name in dependencies))
        check(folder+'_section_count',read_block(source,'MODEL_SOLVING').count(r'\subsection{')==3)
    eq=lambda s:[re.sub(r'\s+','',e) for e in re.findall(r'\\begin\{equation\}(.*?)\\end\{equation\}',s,re.S)]
    check('bilingual_numbered_equations',eq(documents['paper'])==eq(documents['_中文版']))
    macros=lambda s:dict(re.findall(r'\\newcommand\{\\(\w+)\}\{([-+]?\d+(?:\.\d+)?)\}',s))
    check('bilingual_numeric_macros',macros(documents['paper'])==macros(documents['_中文版']))
    baseline=read_json(ROOT/'results/structure_linear_spin/problem/problem_b_M4.json')['record']
    problem=read_json(OUT/'problem/problem_b_M4.json')
    check('problem_same_entry',problem['fit']['active_parameters']==7 and problem['fit']['selection']=='minimum position residual across deterministic starts')
    check('problem_same_reference',np.allclose(problem['record']['event']['position'],baseline['event']['position'],atol=1e-6,rtol=0))
    unchanged=['src/football/physics/model.py','src/football/inference/four_model_fit.py']
    check('shared_physics_and_fit_unchanged',all(subprocess.check_output(['git','diff','HEAD','--',p],cwd=ROOT)==b'' for p in unchanged))
    check('sensitivity_and_real_results_unchanged',subprocess.check_output(['git','diff','HEAD','--','results/sensitivity_linear','results/monte_carlo_linear','results/current_report/inverse','data/current_report'],cwd=ROOT)==b'')
    check('shared_dynamics_axes',read_json(OUT/'figures/figure_contract.json')['dynamics_axes']==dict(time_s=[0,.4],speed_m_s=[20,33],drag_N=[0,8],lift_N=[0,6]))
    result=dict(all_passed=all(checks.values()),checks=checks,crossings=crossings,
        source_sha256={f:hashlib.sha256((ROOT/f/'main.tex').read_bytes()).hexdigest() for f in documents},
        compilation='Use the desktop editor compiler on each saved main.tex; exported PDFs are separate artifacts.')
    save_json(OUT/'chapter4/verification.json',result)
    print(dict(all_passed=result['all_passed'],checks=len(checks),failed=[k for k,v in checks.items() if not v]))
    if not result['all_passed']:raise SystemExit(1)


if __name__=='__main__':main()
