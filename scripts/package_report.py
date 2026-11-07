"""Package the full report project, inputs and results, excluding local caches and QA renders."""
import hashlib,json,shutil,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    excluded={'.git','__pycache__','.pytest_cache','.venv','.mypy_cache','.ruff_cache'}
    build_ext={'.aux','.out','.toc','.xdv','.fls','.fdb_latexmk'}
    files=[];manifest={}
    for p in ROOT.rglob('*'):
        if not p.is_file():continue
        rel=p.relative_to(ROOT)
        if any(s in excluded or s.endswith('.egg-info') for s in rel.parts):continue
        if p.suffix in build_ext or p.name.endswith('.synctex.gz') or p.name.startswith('.env'):continue
        if 'qa' in rel.parts or (rel.parent==Path('results/structure_v2') and p.suffix=='.png'):continue
        if p.name=='delivery_manifest.json':continue
        files.append(p);manifest[rel.as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    manifest_path=ROOT/'results/structure_v2/delivery_manifest.json'
    manifest_path.write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8');files.append(manifest_path)
    archive=ROOT.parent/'UPC2026_ProblemB_报告重构与四模型.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,Path(ROOT.name)/p.relative_to(ROOT))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
    pdf=ROOT.parent/'UPC2026_ProblemB_报告重构与四模型.pdf'
    shutil.copy2(ROOT/'paper/main.pdf',pdf)
    print(json.dumps(dict(files=len(files),archive_bytes=archive.stat().st_size,
        pdf_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest())))
if __name__=='__main__':main()
