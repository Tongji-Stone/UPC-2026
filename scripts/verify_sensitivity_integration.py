"""Check the bilingual source integration and compiled papers against saved data."""
import csv,hashlib,json,re,subprocess,sys
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/sensitivity_v2'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return path.read_text(encoding='utf-8')

def main():
    baseline=json.loads(read(ROOT/'data/sensitivity_v2/source_baseline.json'))
    assets=json.loads(read(OUT/'asset_manifest.json'))
    checks={}
    checks['baseline_commit_recorded']=bool(re.fullmatch(r'[0-9a-f]{40}',baseline['commit']))
    checks['reviewed_input_data_unchanged']=all(sha(ROOT/name)==value for name,value in assets['sources'].items())
    checks['physics_inverse_original_values_unchanged']=all(sha(ROOT/name)==value for name,value in baseline['immutable_files'].items())
    en=read(ROOT/'paper/main.tex');zh=read(ROOT/'_中文版/main.tex')
    se=read(ROOT/'paper/sensitivity.tex');sz=read(ROOT/'_中文版/sensitivity.tex')
    equations=lambda s:re.findall(r'\\begin\{equation\}(.*?)\\end\{equation\}',s,re.S)
    checks['old_physical_equations_preserved']=all(baseline['main_equations'][folder]==equations(read(ROOT/folder/'main.tex')) for folder in ['paper','_中文版'])
    checks['new_bilingual_equations_identical']=equations(se)==equations(sz)
    checks['all_old_labels_preserved']=all(set(baseline['main_labels'][folder])<=
          set(re.findall(r'\\label\{([^}]+)\}',read(ROOT/folder/'main.tex'))) for folder in ['paper','_中文版'])
    checks['ball_properties_fixed']=assets['fixed_mass_kg']==.43 and assets['fixed_radius_m']==.11 and assets['one_factor_parameters']==9 and assets['one_factor_runs']==369
    with (OUT/'compensation.csv').open(encoding='utf-8-sig') as stream:
        compensation=list(csv.DictReader(stream))
    checks['compensation_varies_density_only']=len(compensation)==4 and all(r['parameter']=='rho' for r in compensation)
    me=read(ROOT/'paper/sensitivity_results.tex');mz=read(ROOT/'_中文版/sensitivity_results.tex')
    checks['bilingual_scalar_values_identical']=me.split(r'\newcommand{\SensitivityOneFactorTable}')[0]==mz.split(r'\newcommand{\SensitivityOneFactorTable}')[0]
    tables=lambda s:re.findall(r'\\begin\{tabular\}.*?\\end\{tabular\}',s,re.S)
    nums=lambda s:re.findall(r'(?<![A-Za-z])[-+]?\d+(?:\.\d+)?',s)
    checks['bilingual_new_table_values_identical']=[nums(x) for x in tables(me)]==[nums(x) for x in tables(mz)]
    checks['nine_parameter_table_excludes_mass_radius']=all(x not in me for x in ['Ball mass','Radius + launch height'])
    checks['reviewed_monte_carlo_count_seed']=assets['monte_carlo_primary_count']==100000 and assets['monte_carlo_seed']==20261108
    with (ROOT/'results/sensitivity_v2/one_factor.csv').open(encoding='utf-8-sig') as stream:
        response=[r for r in csv.DictReader(stream) if r['parameter'] not in ('mass','radius')]
    groups={key:[r for r in response if r['parameter']==key] for key in {r['parameter'] for r in response}}
    checks['response_plots_nine_full_41_point_scans']=len(groups)==9 and all(len(g)==41 for g in groups.values())
    checks['response_curves_recover_reference_at_zero']=all(
        max(abs(float(r[k])) for k in ('dy','dz','dt'))<1e-9
        for r in response if abs(float(r['delta']))<1e-12)
    checks['response_figure_files_in_both_versions']=all((folder/name).exists() for folder in [ROOT/'results/sensitivity_v2/figures'] for name in ['one_factor_position_response.pdf','one_factor_time_response.pdf'])
    checks['both_response_figures_referenced']=all(name in section for section in [se,sz]
        for name in ['one_factor_position_response.pdf','one_factor_time_response.pdf'])
    overlay=json.loads(read(OUT/'time_response_overlay_record.json'))
    checks['time_plot_one_axes_nine_curves']=overlay['layout']=='one axes; nine overlaid curves' and len(overlay['curves'])==9
    checks['time_plot_common_normalized_limits']=all(abs(c['x'][0]+1)<1e-12 and abs(c['x'][-1]-1)<1e-12 for c in overlay['curves'])
    checks['time_plot_preserves_all_original_samples']=all(
        c['points']==41 and
        all(abs(x-float(r['delta'])/c['half_width'])<1e-12 and abs(y-1000*float(r['dt']))<1e-10
            for x,y,r in zip(c['x'],c['arrival_time_change_ms'],
                           sorted(groups[c['parameter']],key=lambda r:float(r['delta']))))
        for c in overlay['curves'])
    parallel=json.loads(read(OUT/'parallel_coordinates_record.json'))
    accepted=json.loads(read(ROOT/'data/sensitivity_v2/parallel_display.json'))
    checks['parallel_display_sample_ids_preserved']=parallel['selected_ids']==accepted['selected_ids'] and parallel['display_seed']==20261112
    checks['parallel_display_counts_documented']=parallel['display_count']==400 and parallel['displayed_clear']==382 and parallel['displayed_high']==18 and parallel['full_count']==100000
    checks['parallel_scaling_and_input_observation_recorded']=parallel['all_scaled_values_within_unit_interval'] and len(parallel['input_half_widths'])==9 and len(parallel['output_min'])==3 and min(parallel['displayed_high_elevation_range_degrees'])>0
    checks['only_parallel_component_in_paper']=all('monte_carlo_parallel_coordinates.pdf' in text and 'monte_carlo_parallel_spider_preview' not in text for text in [se,sz])
    checks['shared_sensitivity_figures']=all('../results/sensitivity_v2/figures/' in text for text in [en,zh])
    checks['reference_positions_documented']=all('tab:sensitivity-reference' in text for text in [se,sz])
    checks['independent_reference_frozen']=sha(ROOT/'data/sensitivity_v2/representative_state.json')==json.loads(read(OUT/'baseline.json'))['source_sha256']
    documents={};dependencies={}
    for folder,source,section,macros in [('paper',en,se,me),('_中文版',zh,sz,mz)]:
        document=PdfReader(str(ROOT/folder/'main.pdf'));texts=[p.extract_text() or '' for p in document.pages]
        text='\n'.join(texts);log=read(ROOT/folder/'main.log')
        checks[folder+'_complete_compilation']=not re.search(r'^!',log,re.M) and 'Output written' in log
        checks[folder+'_no_overflow_missing_glyphs']='Overfull' not in log and 'Missing character' not in log
        checks[folder+'_references_resolved']='undefined references' not in log and 'undefined on input line' not in log and '??' not in text
        checks[folder+'_placeholder_removed']=all(x not in source+section for x in ['To be completed.','待完成。','will be added after Section 5'])
        checks[folder+'_new_inputs_active']=r'\input{sensitivity.tex}' in source and r'\input{sensitivity_results.tex}' in source
        checks[folder+'_compact_contents']=(r'{\small\tableofcontents}' in source or r'\begingroup\small\tableofcontents\endgroup' in source or r'\fontsize{10}{11.5}\selectfont\tableofcontents' in source)
        checks[folder+'_key_results_present']=all(x in text for x in ['0.1183','94.87','2.0308','3.3515','100000','369'])
        combined=source+read(ROOT/folder/'sections/model_solving.tex')+section+macros+read(ROOT/folder/'report_results.tex')
        path_line=next(line for line in source.splitlines() if line.startswith(r'\graphicspath'))
        graphic_paths=[ROOT/folder]+[ROOT/folder/p for p in re.findall(r'\{([^{}]+/)\}',path_line)]
        graphics={}
        for name in re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}',combined):
            resolved=next((p/name for p in graphic_paths if (p/name).is_file()),None)
            graphics[name]=resolved.resolve().relative_to(ROOT.resolve()).as_posix() if resolved else None
        inputs=re.findall(r'\\input\{([^}]+)\}',source)
        resolved_inputs=all((ROOT/folder/name).is_file() for name in inputs)
        checks[folder+'_graphics_and_inputs_resolved']=all(graphics.values()) and resolved_inputs
        dependencies[folder]=dict(graphics=graphics,all_dependencies_resolved=checks[folder+'_graphics_and_inputs_resolved'],
            old_examples_absent=all(x not in combined for x in ['ProblemResultsTable','MatchResultsTable','structure_v2','kick_cases']))
        refs=set(re.findall(r'\\(?:eqref|ref|pageref)\{([^}]+)\}',combined))
        labels=set(re.findall(r'\\label\{([^}]+)\}',combined))|{'LastPage'}
        checks[folder+'_all_source_references_defined']=refs<=labels
        citations={key.strip() for group in re.findall(r'\\cite\{([^}]+)\}',combined) for key in group.split(',')}
        bibliography=set(re.findall(r'\\bibitem\{([^}]+)\}',source))
        checks[folder+'_citation_keys_defined']=citations<=bibliography
        documents[folder]=dict(pages=len(document.pages),sha256=sha(ROOT/folder/'main.pdf'),
            underfull_boxes=log.count('Underfull'),sensitivity_equations=len(equations(section)),new_tables=len(tables(macros)))
    (ROOT/'results/current_report/dependency_audit.json').write_text(json.dumps(dependencies,ensure_ascii=False,indent=2),encoding='utf-8')
    result=dict(all_passed=all(checks.values()),checks=checks,documents=documents,
        visual_review='See visual_review.json for the separately recorded rendered-page inspection.',
        sources='results/sensitivity_v2 and results/monte_carlo',
        baseline_commit=baseline['commit'],original_model_and_results_preserved=True)
    (OUT/'integration_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(all_passed=result['all_passed'],checks=len(checks),documents=documents,
                         failed=[k for k,v in checks.items() if not v]),ensure_ascii=False,indent=2))
    if not result['all_passed']:raise SystemExit(1)

if __name__=='__main__':main()
