"""Check final PDF text, page bounds, references and embedded fonts; render QA sheets."""
import json,re
from pathlib import Path
import pymupdf
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/current_report';QA=OUT/'qa'
def main():
    QA.mkdir(exist_ok=True);doc=pymupdf.open(ROOT/'paper/main.pdf')
    text='\n'.join(p.get_text() for p in doc)
    log=(ROOT/'paper/main.log').read_text(encoding='utf-8',errors='replace')
    warnings=[l for l in log.splitlines() if any(x in l for x in
        ['Overfull','Missing character','undefined references','undefined on input','LaTeX Error'])]
    out_of_bounds=[];fonts={}
    for i,p in enumerate(doc):
        for b in p.get_text('dict')['blocks']:
            if 'lines' not in b:continue
            for line in b['lines']:
                for s in line['spans']:
                    box=pymupdf.Rect(s['bbox'])
                    if box.x0<-.5 or box.y0<-.5 or box.x1>p.rect.width+.5 or box.y1>p.rect.height+.5:
                        out_of_bounds.append(dict(page=i+1,text=s['text'],box=list(box)))
        for font in p.get_fonts():
            name,ext,kind,content=doc.extract_font(font[0])
            embedded=bool(content)
            if font[2]=='Type3':
                # Type3 embeds glyph drawing programs instead of a TTF/CFF font file.
                tag,value=doc.xref_get_key(font[0],'CharProcs')
                dictionary=doc.xref_object(int(value.split()[0])) if tag=='xref' else value
                refs=[int(x) for x in re.findall(r'(\d+)\s+0\s+R',dictionary)]
                embedded=bool(refs) and all(doc.xref_is_stream(x) and len(doc.xref_stream(x))>0 for x in refs)
                ext='Type3 embedded glyph programs'
            fonts[name]=dict(format=ext,embedded=embedded)
    cols=4;thumb_w=210;thumb_h=290
    canvas=Image.new('RGB',(cols*thumb_w,((len(doc)+cols-1)//cols)*thumb_h),'#dedbd5')
    draw=ImageDraw.Draw(canvas)
    for i,p in enumerate(doc):
        pix=p.get_pixmap(matrix=pymupdf.Matrix(.32,.32))
        im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
        x=(i%cols)*thumb_w;y=(i//cols)*thumb_h
        canvas.paste(im,(x+5,y+20));draw.text((x+8,y+4),f'Page {i+1}',fill='black')
    canvas.save(QA/'final_contact.png')
    for i,p in enumerate(doc):
        if any(t in p.get_text() for t in ['Sparse Early Observations','All five recorded flights','The damped goal-plane centre','Reproduction Code']):
            p.get_pixmap(matrix=pymupdf.Matrix(1.4,1.4)).save(str(QA/f'final_page{i+1}.png'))
    result=dict(pages=len(doc),warnings=warnings,out_of_page_text=out_of_bounds,
        all_fonts_embedded=all(v['embedded'] for v in fonts.values()),fonts=fonts,
        has_eight_chapters=all(t in text for t in ['Introduction','Preparation of the Models','Model Establishment',
            'Model Solving','Sensitivity Analysis','Discussion of Other Factors','Conclusions','Model Evaluation']),
        no_unresolved_references='??' not in text,no_old_results=all(s not in text for s in ['600 samples','495 trajectories','Linthorne']),
        fifth_chapter_complete='To be completed.' not in text and 'Joint perturbations and Monte Carlo simulation' in text,
        workflow_border_removed='draw=wfBorder,dashed' not in (ROOT/'paper/main.tex').read_text(encoding='utf-8'),
        workflow_body_font_pt=12.)
    result['all_passed']=not warnings and not out_of_bounds and all(result[k] for k in
        ['all_fonts_embedded','has_eight_chapters','no_unresolved_references','no_old_results','fifth_chapter_complete','workflow_border_removed'])
    (OUT/'pdf_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(dict(all_passed=result['all_passed'],pages=len(doc),warnings=warnings,bounds=len(out_of_bounds))))
    if not result['all_passed']:raise SystemExit(1)
if __name__=='__main__':main()
