"""Verify exported bilingual PDFs and render the pages changed by Chapter 6."""
import hashlib
import re
import pymupdf
from PIL import Image,ImageDraw
from football.reporting import ROOT,save_json


def main():
    out=ROOT/'results/chapter6';qa=out/'qa';qa.mkdir(exist_ok=True);editions={}
    for folder,name in [('paper','english'),('_中文版','chinese')]:
        base=ROOT/folder;doc=pymupdf.open(base/'main.pdf')
        log=(base/'main.log').read_text(encoding='utf-8',errors='replace')
        errors=[l for l in log.splitlines() if any(x in l for x in ['Overfull','Missing character','undefined references','LaTeX Error'])]
        assert not errors,(name,errors)
        assert '??' not in '\n'.join(p.get_text() for p in doc)
        assert (base/'main.pdf').stat().st_mtime>=(base/'main.tex').stat().st_mtime
        aux=(base/'main.aux').read_text(encoding='utf-8');labels={}
        for label in ['fig:alam-drag','fig:torque','tab:torque-goals','tab:wind','eq:rotation-motion']:
            m=re.search(r'\\newlabel\{'+re.escape(label)+r'\}\{\{([^}]+)\}\{(\d+)\}',aux)
            assert m,label;labels[label]=dict(number=m[1],page=int(m[2]))
        assert labels['fig:alam-drag']['number']=='19'
        pages=sorted({r['page'] for r in labels.values()})
        contact=Image.new('RGB',(990,((len(pages)+2)//3)*450),'#eee9df');draw=ImageDraw.Draw(contact)
        for i,n in enumerate(pages):
            page=doc[n-1];pix=page.get_pixmap(matrix=pymupdf.Matrix(1.2,1.2));pix.save(str(qa/f'{name}_{n}.png'))
            im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples);im.thumbnail((310,420))
            x=i%3*330+10;y=i//3*450+24;contact.paste(im,(x,y));draw.text((x,y-18),f'{name} page {n}',fill='black')
            for block in page.get_text('blocks'):
                assert block[0]>=0 and block[1]>=0 and block[2]<=page.rect.width+.5 and block[3]<=page.rect.height+.5,(name,n,block[:4])
        contact.save(qa/f'{name}_contact.png')
        editions[name]=dict(pages=len(doc),labels=labels,no_unresolved_references=True,no_compile_errors=True,
            new_pages_within_bounds=True,tex_sha256=hashlib.sha256((base/'main.tex').read_bytes()).hexdigest(),
            pdf_sha256=hashlib.sha256((base/'main.pdf').read_bytes()).hexdigest())
    save_json(out/'pdf_verification.json',dict(all_passed=True,editions=editions))
    paths=[ROOT/'paper/main.tex',ROOT/'paper/main.pdf',ROOT/'_中文版/main.tex',ROOT/'_中文版/main.pdf',
        ROOT/'docs/第六章简化假设检验与复现.md']
    paths+=list((ROOT/'scripts').glob('chapter6_*.py'))+[ROOT/'scripts/reproduce_chapter6.ps1']
    paths+=[p for p in out.rglob('*') if p.is_file() and 'qa' not in p.relative_to(out).parts and p.name!='delivery_manifest.json']
    save_json(out/'delivery_manifest.json',dict(files={str(p.relative_to(ROOT)):dict(bytes=p.stat().st_size,
        sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths},
        git_delivery_branch='codex/report-narrative-revision-20261108',verification_stage='pre-push'))
    print({name:r['pages'] for name,r in editions.items()})


if __name__=='__main__':main()
