"""Audit the reader-facing narrative, actual figure/table references and unchanged physics."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

import pymupdf
from latex_blocks import read_block

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/current_report'
BASELINE='d86d90c'
APPROVED='30d0dea'


def main():
    checks={};editions={};single={};layout={}
    def check(name,value,**details):checks[name]=dict(passed=bool(value),**details)
    def equations(source):
        return [re.sub(r'\s+','',re.sub(r'\\label\{[^}]+\}','',x))
                for x in re.findall(r'\\begin\{equation\}(.*?)\\end\{equation\}',source,re.S)]
    for lang,folder,titles in [('en','paper',('Problem Background','Problem Restatement','Assumptions','Notations')),
                               ('zh','_中文版',('问题背景','问题重述','基本假设','符号说明'))]:
        base=ROOT/folder;source=(base/'main.tex').read_text(encoding='utf-8')
        old=subprocess.check_output(['git','show',BASELINE+':'+folder+'/main.tex'],cwd=ROOT).decode('utf-8')
        approved=subprocess.check_output(['git','show',APPROVED+':'+folder+'/main.tex'],cwd=ROOT).decode('utf-8')
        doc=pymupdf.open(base/'main.pdf');aux=(base/'main.aux').read_text(encoding='utf-8')
        body=source.split(r'\begin{document}',1)[1]
        mainbody=body.split(r'\begin{thebibliography}',1)[0]
        # Appendix tables may be introduced in their own appendix paragraphs.
        refs=set(re.findall(r'\\(?:ref|eqref|pageref)\{([^}]+)\}',body))
        groups={}
        for label,num,page in re.findall(r'\\newlabel\{((?:fig|tab):[^}]+)\}\{\{([^}]+)\}\{(\d+)\}',aux):
            groups.setdefault((label.split(':')[0],num,int(page)),[]).append(label)
        missing=[dict(kind=k[0],number=k[1],page=k[2],labels=v) for k,v in groups.items() if not refs.intersection(v)]
        check(lang+'_all_rendered_figures_tables_referenced_in_body',not missing,missing=missing,groups=len(groups))
        cites={k.strip() for group in re.findall(r'\\cite(?:\[[^]]*\])?\{([^}]+)\}',mainbody) for k in group.split(',')}
        bib=set(re.findall(r'\\bibitem\{([^}]+)\}',source))
        check(lang+'_all_bibliography_entries_used_in_body',bib==cites,unused=sorted(bib-cites),undefined=sorted(cites-bib))
        background=source.split(r'\subsection{'+titles[0]+'}',1)[1].split(r'\subsection{'+titles[1]+'}',1)[0]
        restatement=source.split(r'\subsection{'+titles[1]+'}',1)[1].split(r'\begin{figure}',1)[0]
        assumptions=source.split(r'\subsection{'+titles[2]+'}',1)[1].split(r'\subsection{'+titles[3]+'}',1)[0]
        check(lang+'_background_is_context_only',all(x not in background for x in ['Problem B','本题','赛题','0.05','0.10','DOP853']))
        check(lang+'_restatement_complete',all(x in restatement for x in ['11','7.32','2.44','0.05','0.10','sec:model','sec:solving','sec:sensitivity'])
              and (('most likely' in restatement and 'uncertainty' in restatement) if lang=='en' else ('最可能' in restatement and '不确定性' in restatement)))
        check(lang+'_assumptions_are_physical',not any(x in assumptions for x in [r'\cite','tracking frame','integration','main model','main calculation','追踪帧','数值积分','主模型','主计算','CSV','搜索']))
        old_restatement=old.split(r'\subsection{'+titles[1]+'}',1)[1].split(r'\begin{figure}',1)[0]
        check(lang+'_remote_restatement_preserved',restatement==old_restatement)
        check(lang+'_workflow_unchanged',read_block(source,'WORKFLOW')==read_block(old,'WORKFLOW'))
        check(lang+'_numbered_physical_equations_unchanged',equations(source.split('% BEGIN MODEL_SOLVING')[0])==equations(old.split('% BEGIN MODEL_SOLVING')[0]))
        def abstract(s):
            start=s.index(r'\end{center}',s.index(r'\begin{document}'))+len(r'\end{center}')
            return s[start:s.index(r'\newpage\begingroup')]
        evaluation=r'\section{Model Evaluation}' if lang=='en' else r'\section{模型评价}'
        def chapter8(s):return s[s.index(evaluation):s.index(r'\begin{thebibliography}')]
        check(lang+'_approved_abstract_preserved',abstract(source)==abstract(approved))
        check(lang+'_approved_chapter8_preserved',chapter8(source)==chapter8(approved))
        check(lang+'_approved_sensitivity_analysis_preserved',read_block(source,'SENSITIVITY_BODY').split(r'\FloatBarrier',1)[1]==read_block(approved,'SENSITIVITY_BODY').split(r'\FloatBarrier',1)[1])
        check(lang+'_remote_chapter4_preserved',read_block(source,'MODEL_SOLVING')==read_block(old,'MODEL_SOLVING'))
        omega_def=source.index(r'Let $\boldsymbol\omega$' if lang=='en' else r'令 $\boldsymbol\omega$')
        check(lang+'_omega_before_lift_formula',omega_def<source.index(r'\label{eq:lift-force}'))
        check(lang+'_rigid_body_before_newton',source.index('Since the football is treated as a rigid body' if lang=='en' else '鉴于我们把足球视为刚体')<source.index(r'\dfrac{d\boldsymbol L}{dt}'))
        eqnums={}
        for key,expected in [('eq:drag-force','3'),('eq:lift-force','4'),('eq:motion','7'),('eq:initial','8')]:
            match=re.search(r'\\newlabel\{'+re.escape(key)+r'\}\{\{([^}]+)\}',aux)
            eqnums[key]=match[1] if match else None
            check(lang+'_'+key+'_number',bool(match) and match[1]==expected)
        is_single=not re.search(r'\\(?:input|include|lstinputlisting)\b',source)
        check(lang+'_single_tex',is_single)
        hashes=dict(tex_sha256=hashlib.sha256((base/'main.tex').read_bytes()).hexdigest(),pdf_sha256=hashlib.sha256((base/'main.pdf').read_bytes()).hexdigest())
        single[folder]=dict(passed=bool(is_single),pages=len(doc),no_external_tex_or_code_inputs=bool(is_single),**hashes)
        labels={}
        for label,num,page in re.findall(r'\\newlabel\{((?:fig|tab):[^}]+)\}\{\{([^}]+)\}\{(\d+)\}',aux):labels[label]=dict(number=num,page=int(page))
        photo_page=doc[labels['fig:shot-photos']['page']-1]
        photos=[x['bbox'] for x in photo_page.get_image_info() if x['width'] in [960,1024]]
        a,b=sorted(photos,key=lambda x:x[0]);equal=abs(a[1]-b[1])<.05 and abs((a[2]-a[0])-(b[2]-b[0]))<.05 and abs((a[3]-a[1])-(b[3]-b[1]))<.05
        check(lang+'_equal_side_by_side_photos',equal)
        tables=[doc[labels[key]['page']-1] for key in ['tab:placement-crossings','tab:power-crossings'] if key in labels]
        spans=[s for table in tables for block in table.get_text('dict')['blocks'] if 'lines' in block for line in block['lines'] for s in line['spans']]
        sizes=[s['size'] for s in spans if s['text'].strip() in ['0.360','0.684','0.657','0.374','0.113','0.475','0.155','0.146']]
        check(lang+'_error_table_12pt','tab:power-crossings' in labels and len(sizes)>=4 and all(abs(s-12*72/72.27)<.02 for s in sizes))
        tocintro=next(e[2] for e in doc.get_toc() if e[1] in ['Introduction','引言'])
        sizes=[s['size'] for page in list(doc)[1:tocintro-1] for block in page.get_text('dict')['blocks'] if 'lines' in block for line in block['lines'] for s in line['spans'] if s['bbox'][1]>65 and s['size']<14 and s['text'].strip()]
        check(lang+'_toc_12pt',bool(sizes) and all(abs(s-12*72/72.27)<.02 for s in sizes))
        editions[lang]=dict(pages=len(doc),figure_table_groups=len(groups),equation_numbers=eqnums,**hashes)
        layout[lang]=dict(pages=len(doc),labels=labels)
    changed=subprocess.check_output(['git','diff',BASELINE,'--name-only'],cwd=ROOT,encoding='utf-8').splitlines()
    reviewed_assets={'results/sensitivity_linear/asset_manifest.json'}
    numerical=[p for p in changed if p.startswith(('src/','data/','configs/','results/current_report/forward/','results/current_report/inverse/','results/current_report/other/'))
               or (p.startswith(('results/sensitivity_linear/','results/monte_carlo_linear/')) and not p.startswith('results/sensitivity_linear/figures/') and p not in reviewed_assets and not p.endswith(('verification.json','integration_verification.json')))]
    check('physics_inputs_and_calculations_unchanged',not numerical,changed=numerical)
    reviewed_changes=subprocess.check_output(['git','diff',APPROVED,'--name-only','--','results/chapter5_review'],cwd=ROOT,encoding='utf-8').splitlines()
    check('approved_figure13_calculations_preserved',not reviewed_changes,changed=reviewed_changes)
    result=dict(all_passed=all(c['passed'] for c in checks.values()),baseline_commit=BASELINE,approved_revision=APPROVED,editions=editions,checks=checks)
    (OUT/'narrative_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'single_tex_verification.json').write_text(json.dumps(dict(all_passed=all(x['passed'] for x in single.values()),editions=single,content_policy='Intentional bilingual narrative revision; numbered physical equations and calculations unchanged'),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'layout_revision_verification.json').write_text(json.dumps(dict(all_passed=result['all_passed'],editions=layout,checks={k:v for k,v in checks.items() if any(w in k for w in ['photos','12pt','workflow'])}),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(all_passed=result['all_passed'],checks=len(checks),failed=[k for k,v in checks.items() if not v['passed']],editions=editions),ensure_ascii=False))
    if not result['all_passed']:raise SystemExit(1)


if __name__=='__main__':main()
