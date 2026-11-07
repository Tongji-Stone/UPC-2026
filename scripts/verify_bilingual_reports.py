"""Check editorial structure, unchanged equations/results and Chinese style mapping."""
from pathlib import Path
import re,json,hashlib
import pymupdf
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/bilingual_report';OUT.mkdir(exist_ok=True)
def main():
    en=(ROOT/'paper/main.tex').read_text(encoding='utf-8');zh=(ROOT/'_中文版/main.tex').read_text(encoding='utf-8')
    checks={}
    def check(name,passed,**detail):checks[name]=dict(passed=bool(passed),**detail)
    equations=lambda s:re.findall(r'\\begin\{equation\}(.*?)\\end\{equation\}',s,re.S)
    check('identical_display_equations',equations(en)==equations(zh),count=len(equations(en)))
    check('identical_citation_keys',set(re.findall(r'\\cite\{([^}]+)\}',en))==set(re.findall(r'\\cite\{([^}]+)\}',zh)))
    for label,nextlabel,coefficient in [('sec:drag','sec:lift','cd'),('sec:lift','sec:dynamics','cl')]:
        section=en[en.index('\\label{'+label+'}'):en.index('\\label{'+nextlabel+'}')]
        listed=section[section.index(r'\begin{enumerate}'):section.index(r'\end{enumerate}')]
        items=listed.split(r'\item')[1:]
        check(coefficient+'_quantity_bold',len(items)==5 and all(s.lstrip().startswith(r'\textbf{') for s in items))
        check(coefficient+'_formula_inside_item',r'\label{eq:'+coefficient+'-full}' in items[3])
        tail=section[section.index(r'\end{enumerate}'):]
        check(coefficient+'_tail_comparison_only',r'\begin{equation}' not in tail)
    check('workflow_footer_removed',all('gravity $\\cdot$ drag' not in (ROOT/p/'assets/workflow_tikz.tex').read_text(encoding='utf-8') for p in ['paper','_中文版']))
    check('english_figures_retained',all(hashlib.sha256((ROOT/'results/structure_v2/figures'/p.name).read_bytes()).hexdigest()==hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'_中文版/figures').glob('*.pdf')))
    blocks=lambda s:re.findall(r'\\begin\{tabular\}.*?\\end\{tabular\}',s,re.S)
    numbers=lambda s:re.findall(r'(?<![A-Za-z])[-+]?\d+(?:\.\d+)?',s)
    a=(ROOT/'paper/report_results.tex').read_text(encoding='utf-8');b=(ROOT/'_中文版/report_results.tex').read_text(encoding='utf-8')
    check('identical_table_numbers',[numbers(x) for x in blocks(a)]==[numbers(x) for x in blocks(b)])
    for language,folder in [('english','paper'),('chinese','_中文版')]:
        document=pymupdf.open(ROOT/folder/'main.pdf');text='\n'.join(p.get_text() for p in document)
        log=(ROOT/folder/'main.log').read_text(encoding='utf-8',errors='replace')
        warnings=[l for l in log.splitlines() if any(x in l for x in ['Overfull','Missing character','undefined references','LaTeX Error'])]
        check(language+'_clean_compile',not warnings,pages=len(document),warnings=warnings)
        check(language+'_resolved_references','??' not in text)
        if language=='chinese':
            style_fonts={}
            for p in document:
                for block in p.get_text('dict')['blocks']:
                    for line in block.get('lines',[]):
                        for span in line['spans']:
                            if '空气密度' in span['text']:style_fonts.setdefault('bold_quantity',[]).append(span['font'])
                            if '待完成' in span['text']:style_fonts['italic_pending']=span['font']
            fontnames={f[3] for p in document for f in p.get_fonts()}
            check('song_regular_hei_bold_kai_italic',all(any(f in name for name in fontnames) for f in ['SimSun','SimHei','KaiTi'])
                and style_fonts.get('italic_pending')=='KaiTi',observed=style_fonts)
            for i,p in enumerate(document):
                if any(t in p.get_text() for t in ['空气密度','阻力危机','摘要','待完成']):
                    p.get_pixmap(matrix=pymupdf.Matrix(1.25,1.25)).save(str(OUT/f'chinese_page{i+1}.png'))
        canvas=Image.new('RGB',(800,((len(document)+3)//4)*280),'#dedbd5');draw=ImageDraw.Draw(canvas)
        for i,p in enumerate(document):
            pix=p.get_pixmap(matrix=pymupdf.Matrix(.30,.30));im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
            x=(i%4)*200;y=(i//4)*280;canvas.paste(im,(x+6,y+20));draw.text((x+6,y+4),f'{language} {i+1}',fill='black')
        canvas.save(OUT/f'{language}_contact.png')
    result=dict(all_passed=all(x['passed'] for x in checks.values()),checks=checks)
    (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(all_passed=result['all_passed'],checks=len(checks),failed=[k for k,v in checks.items() if not v['passed']])))
    if not result['all_passed']:raise SystemExit(1)
if __name__=='__main__':main()
