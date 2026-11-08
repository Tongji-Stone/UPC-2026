"""Check expanded equations/tables, shared graphics, fonts and render every page."""
import re
import pymupdf
from PIL import Image,ImageDraw
from football.reporting import ROOT,OUT,save_json
from latex_blocks import read_block

def main():
    qa=OUT/'qa';qa.mkdir(exist_ok=True);checks={};texts={}
    def check(k,ok,**detail):checks[k]=dict(passed=bool(ok),**detail)
    for lang,folder in [('english','paper'),('chinese','_中文版')]:
        root=ROOT/folder;s=(root/'main.tex').read_text(encoding='utf-8')
        texts[lang]=s
        check(lang+'_single_tex',not re.search(r'\\(?:input|include|lstinputlisting)\b',s))
        d=pymupdf.open(root/'main.pdf');text='\n'.join(p.get_text() for p in d)
        log=(root/'main.log').read_text(encoding='utf-8',errors='replace')
        warnings=[l for l in log.splitlines() if any(x in l for x in ['Overfull','Missing character','undefined','LaTeX Error'])]
        check(lang+'_compile',not warnings,warnings=warnings,pages=len(d));check(lang+'_references','??' not in text)
        check(lang+'_shared_figures','results/current_report/figures/' in s)
        check(lang+'_removed_examples',all(x not in s for x in ['ProblemResultsTable','MatchResultsTable','structure_v2','kick_cases']))
        check(lang+'_aggregate_table_removed',r'\InverseResultsTable' not in s)
        check(lang+'_overview_and_detail','penalty_spatial_overview.pdf' in s and 'penalty_J03WOH.pdf' in s)
        check(lang+'_new_time_statement',(r'0,0.04,0.08' in s or '0, 0.04 and 0.08' in s or '0、0.04、0.08' in s))
        check(lang+'_wmx_three_frame_times',(r'0,0.04,0.08' in s or '0, 0.04 and 0.08' in s or '0、0.04、0.08' in s))
        canvas=Image.new('RGB',(840,((len(d)+3)//4)*290),'#e5e0d8');draw=ImageDraw.Draw(canvas);fontnames=set()
        for i,p in enumerate(d):
            pix=p.get_pixmap(matrix=pymupdf.Matrix(.32,.32));im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
            x=(i%4)*210;y=(i//4)*290;canvas.paste(im,(x+5,y+20));draw.text((x+5,y+3),f'{lang} {i+1}',fill='black')
            p.get_pixmap(matrix=pymupdf.Matrix(1,1)).save(str(qa/f'{lang}_{i+1:02}.png'))
            fontnames.update(f[3] for f in p.get_fonts())
        canvas.save(qa/f'{lang}_contact.png')
        if lang=='chinese':
            italic_chinese=bool(re.search(r'\\textit\{[^}]*[\u4e00-\u9fff]',s))
            check('song_hei_kai_fonts',all(any(n in f for f in fontnames) for n in ['SimSun','SimHei'])
                and 'ItalicFont=KaiTi' in s.replace(' ','') and (not italic_chinese or any('KaiTi' in f for f in fontnames)))
    equations=lambda s:[re.sub(r'\s+','',x) for x in re.findall(r'\\begin\{equation\}(.*?)\\end\{equation\}',s,re.S)]
    check('identical_equations',equations(texts['english'])==equations(texts['chinese']))
    cites=lambda s:set(re.findall(r'\\cite\{([^}]+)\}',s))
    check('identical_citations',cites(texts['english'])==cites(texts['chinese']))
    blocks=lambda s:re.findall(r'\\begin\{tabular\}.*?\\end\{tabular\}',s,re.S)
    numbers=lambda s:re.findall(r'(?<![A-Za-z])[-+]?\d+(?:\.\d+)?',s)
    en=''.join(read_block(texts['english'],name) for name in ['REPORT_RESULTS','SENSITIVITY_RESULTS'])
    zh=''.join(read_block(texts['chinese'],name) for name in ['REPORT_RESULTS','SENSITIVITY_RESULTS'])
    check('identical_table_numbers',[numbers(x) for x in blocks(en)]==[numbers(x) for x in blocks(zh)])
    result=dict(all_passed=all(v['passed'] for v in checks.values()),checks=checks);save_json(OUT/'bilingual_verification.json',result)
    print(dict(all_passed=result['all_passed'],failed=[k for k,v in checks.items() if not v['passed']]))
    if not result['all_passed']:raise SystemExit(1)

if __name__=='__main__':main()
