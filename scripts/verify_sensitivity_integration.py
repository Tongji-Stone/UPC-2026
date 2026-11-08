"""Verify the active linear-spin experiments, bilingual paper, plots and PDFs."""
import csv
import hashlib
import json
import re
from pathlib import Path

import numpy as np
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/sensitivity_linear'
MC=ROOT/'results/monte_carlo_linear'

def read(p): return p.read_text(encoding='utf-8')
def js(p): return json.loads(read(p))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):
    with p.open(encoding='utf-8-sig') as f: return list(csv.DictReader(f))
def equations(s): return [re.sub(r'\s+','',x) for x in re.findall(r'\\begin\{equation\}(.*?)\\end\{equation\}',s,re.S)]
def main():
    checks={}
    def check(name,value): checks[name]=bool(value)
    cfg=js(ROOT/'configs/sensitivity_v2.json')
    baseline=js(OUT/'baseline.json');assets=js(OUT/'asset_manifest.json')
    verification=js(OUT/'verification.json');physical=js(OUT/'physical_checks.json')
    reference=js(ROOT/cfg['baseline_result']);summary=js(MC/'summary.json');mv=js(MC/'verification.json')
    check('constant_CD_linear_CL_model',reference['configuration']['coefficient_mode']=='linear_spin')
    check('fixed_mass_radius',cfg['physics']['mass']==.43 and cfg['physics']['radius']==.11 and mv['mass_kg']==.43 and mv['radius_m']==.11)
    check('reference_recomputed_from_current_sources',all(sha(ROOT/p)==h for p,h in reference['source_sha256'].items()))
    check('baseline_source_matches',baseline['source_sha256']==sha(ROOT/cfg['baseline_result']))
    check('publication_source_hashes_match',all(sha(ROOT/p)==h for p,h in assets['sources'].items()))
    check('shared_rhs_matches',verification['max_rhs_difference']<1e-10 and verification['fast_vs_repository_m']<1e-7)
    check('physical_limits_and_compensation',physical['all_passed'])
    scans=rows(OUT/'one_factor.csv');groups={k:[r for r in scans if r['parameter']==k] for k in cfg['one_factor_half_widths']}
    check('nine_41_point_scans',len(scans)==369 and len(groups)==9 and all(len(v)==41 for v in groups.values()))
    check('mass_radius_not_scanned',not any(r['parameter'] in ['mass','radius'] for r in scans))
    check('zero_perturbation_reference',all(max(abs(float(r[k])) for k in ['dy','dz','dt'])<1e-8 for r in scans if abs(float(r['delta']))<1e-12))
    overlay=js(OUT/'time_response_overlay_record.json')
    check('time_one_axes_nine_curves',overlay['layout']=='one axes; nine overlaid curves' and len(overlay['curves'])==9)
    check('time_all_scan_points_preserved',all(c['points']==41 and all(abs(x-float(r['delta'])/c['half_width'])<1e-12 and abs(y-1000*float(r['dt']))<1e-10 for x,y,r in zip(c['x'],c['arrival_time_change_ms'],sorted(groups[c['parameter']],key=lambda r:float(r['delta'])))) for c in overlay['curves']))
    profile=rows(OUT/'profile.csv');pr=cfg['profile']
    check('profile_tolerance',all(float(r['residual_m'])<=pr['coordinate_tolerance_m'] for r in profile))
    check('profile_bounds',all(pr['force_multiplier_bounds'][0]-1e-9<=float(r[k])<=pr['force_multiplier_bounds'][1]+1e-9 for r in profile for k in ['ad','al']))
    check('profile_velocity_spin_bounds',all(float(r['speed'])<=pr['max_speed_m_s'] and max(abs(float(r[f's{i}'])) for i in [3,4,5])<=pr['spin_component_max_rad_s']+1e-8 for r in profile))
    check('density_only_compensation',all(r['parameter']=='rho' and float(r['displacement'])<1e-8 for r in rows(OUT/'compensation.csv')))
    sample=np.load(MC/'samples.npz')
    check('MC_count_and_seed',len(sample['time'])==cfg['monte_carlo']['samples']==summary['count']==100000 and mv['seed']==cfg['monte_carlo']['seed'])
    check('MC_seed_reproducible',mv['random_prefix_reproduced'])
    check('MC_all_reach_plane',summary['plane']==summary['count'] and np.all(sample['event']==0))
    check('MC_clearance_statistics',int(sample['clear'].sum())==summary['clear'] and summary['clear']+summary['nonclear_at_plane']==summary['count'])
    check('MC_numerical_convergence',mv['maximum_adaptive_difference_m']<1e-6 and mv['maximum_half_step_difference_m']<1e-6)
    check('MC_empirical_joint_region',abs(summary['ellipse_95']['empirical_coverage']-.95)<1e-12)
    display=js(ROOT/'data/sensitivity_v2/parallel_display.json');parallel=js(OUT/'parallel_coordinates_record.json')
    ids=np.array(display['selected_ids']);actual_clear=int(sample['clear'][ids].sum())
    check('parallel_original_display_ids',parallel['selected_ids']==display['selected_ids'] and len(ids)==400)
    check('parallel_actual_clearance_counts',parallel['displayed_clear']==actual_clear and parallel['displayed_high']==400-actual_clear)
    check('parallel_scaling',parallel['all_scaled_values_within_unit_interval'])
    documents={};dependencies={};sources={}
    for folder in ['paper','_中文版']:
        main=read(ROOT/folder/'main.tex');section=read(ROOT/folder/'sections/model_solving.tex');sensitivity=read(ROOT/folder/'sensitivity.tex')
        tables=read(ROOT/folder/'report_results.tex')+read(ROOT/folder/'sensitivity_results.tex')
        expanded=main+section+sensitivity+tables;sources[folder]=expanded
        log=read(ROOT/folder/'main.log');doc=PdfReader(ROOT/folder/'main.pdf');text='\n'.join(p.extract_text() or '' for p in doc.pages)
        check(folder+'_clean_compile',not any(x in log for x in ['Overfull','Missing character','undefined references','LaTeX Error']) and 'Output written' in log)
        check(folder+'_references_resolved','??' not in text)
        labels=set(re.findall(r'\\label\{([^}]+)\}',expanded))|{'LastPage'}
        refs=set(re.findall(r'\\(?:eqref|ref|pageref)\{([^}]+)\}',expanded))
        check(folder+'_source_refs_defined',refs<=labels)
        cites={x.strip() for group in re.findall(r'\\cite\{([^}]+)\}',expanded) for x in group.split(',')}
        check(folder+'_citation_keys_defined',cites<=set(re.findall(r'\\bibitem\{([^}]+)\}',main)))
        check(folder+'_current_result_paths','results/sensitivity_linear/figures/' in main and 'results/current_report/figures/' in main)
        check(folder+'_chapter_complete',all(x not in expanded for x in ['To be completed.','待完成。','沿用队友','We retain the individual-parameter']))
        check(folder+'_new_results_present',all(x in text for x in [f"{summary['y_range'][0]:.4f}",f"{summary['y_range'][1]:.4f}",f"{100*summary['clear_fraction']:.3f}",f"{js(OUT/'profile_summary.json')['wide']['max_displacement']:.4f}"]))
        check(folder+'_no_old_results',all(x not in text for x in ['0.1183','94.87','2.6826','0.3007']))
        path_line=next(x for x in main.splitlines() if x.startswith(r'\graphicspath'))
        paths=[ROOT/folder]+[ROOT/folder/x for x in re.findall(r'\{([^{}]+/)\}',path_line)]
        graphics={}
        for name in re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}',expanded):
            target=next((p/name for p in paths if (p/name).is_file()),None)
            graphics[name]=target.resolve().relative_to(ROOT).as_posix() if target else None
        check(folder+'_graphics_resolved',all(graphics.values()))
        check(folder+'_inputs_resolved',all((ROOT/folder/p).is_file() for p in re.findall(r'\\input\{([^}]+)\}',main)))
        dependencies[folder]=dict(graphics=graphics,all_dependencies_resolved=all(graphics.values()))
        documents[folder]=dict(pages=len(doc.pages),sha256=sha(ROOT/folder/'main.pdf'))
    check('bilingual_display_equations',equations(sources['paper'])==equations(sources['_中文版']))
    table_blocks=lambda s:re.findall(r'\\begin\{tabular\}.*?\\end\{tabular\}',s,re.S)
    numbers=lambda s:re.findall(r'(?<![A-Za-z])[-+]?\d+(?:\.\d+)?',s)
    check('bilingual_table_values',[numbers(x) for x in table_blocks(sources['paper'])]==[numbers(x) for x in table_blocks(sources['_中文版'])])
    check('writing_guidance_and_internal_notes',(ROOT/'docs/文章表述修改依据.md').is_file() and (ROOT/'check.md').is_file())
    result=dict(all_passed=all(checks.values()),checks=checks,documents=documents,model='constant CD and linear CL=alpha*Sp')
    (OUT/'integration_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'results/current_report/dependency_audit.json').write_text(json.dumps(dependencies,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(all_passed=result['all_passed'],checks=len(checks),failed=[k for k,v in checks.items() if not v],documents=documents),ensure_ascii=True,indent=2))
    if not result['all_passed']: raise SystemExit(1)

if __name__=='__main__': main()
