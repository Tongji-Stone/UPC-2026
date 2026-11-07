"""Independent numerical checks for the handoff artifacts."""
import csv
import json
import math
from pathlib import Path
from PIL import Image
from aerodynamic_formulas import *
from compute_aerodynamic_comparison import read_points,reference_at

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/processed/aerodynamic_parameters'
checks=[]
def check(name,condition):
    if not condition:raise AssertionError(name)
    checks.append(name)

check('G10 logistic midpoint',abs(cd_g10_v(12.19)-(.155+.346/2))<1e-14)
check('KL18 table tail',abs(cd_kl18_v(35)-.154)<1e-5)
check('KL18 reference anchor .19,.29',abs(cl_kl18(333793*1.5e-5/.22,.19)-.29)<.001)
check('zero-spin lift',cl_kl18(31,0)==0)
check('G10 original branch equality',cd_g10(31,.05)==cd_g10_v(31))
check('G10 original branch jump documented',abs(cd_g10(31,.0500001)-cd_g10(31,.05))>.009)
for sp in [0,.001,.05,.2,.35,1]:
    cv,cw,q,w=cq_and_torque(31.461246,sp)
    expected=(8*math.pi/15)*1.2*1.5*.11**5*w**2+8*math.pi*(1.2*1.5e-5)*.11**3*w
    check(f'torque direct SI equality Sp={sp}',math.isclose(q,expected,rel_tol=1e-12,abs_tol=1e-14))
    check(f'damping dissipates Sp={sp}',-q*w<=0)
    if sp:check(f'normalization identity Sp={sp}',math.isclose(cw,cv/sp**2,rel_tol=1e-13))
    else:check('CQomega undefined at zero, torque zero',cw is None and q==0)
pts=read_points()
check('68 unique Teamgeist markers',len(pts)==68 and len({p['point_id'] for p in pts})==68)
for coef in ['CD','CL']:
    check(f'{coef} Re extrapolation refused',reference_at(pts,coef,461432,.2)[0] is None)
    check(f'{coef} interior interpolation available',reference_at(pts,coef,449446,.2)[0] is not None)
    check(f'{coef} unsupported high spin refused',reference_at(pts,coef,449446,.9)[0] is None)
with (DATA/'参数对照.csv').open(encoding='utf-8-sig') as f: rows=list(csv.DictReader(f))
for r in rows:
    if r['reference_value']:
        check_ok=abs(float(r['model_value'])-float(r['reference_value'])-float(r['difference']))<1e-12
        if not check_ok:raise AssertionError('CSV residual mismatch')
check('CSV all residuals reproduced',True)
check('all 2007 primary residuals unique per model',len([(r['model'],r['reference_point_ids']) for r in rows if r['case'].startswith('experimental_')])==len(set((r['model'],r['reference_point_ids']) for r in rows if r['case'].startswith('experimental_'))))
for png in sorted((ROOT/'results/aerodynamic_parameters').glob('0*.png')):
    im=Image.open(png);dpi=im.info.get('dpi',(0,0))
    check(png.name+' >=300DPI and SVG',min(dpi)>299 and png.with_suffix('.svg').exists())
check('four figure groups',len(list((ROOT/'results/aerodynamic_parameters').glob('0*.png')))==4)
report=dict(status='passed',checks=checks,count=len(checks),csv_rows=len(rows),note='graphical reading bounds are not laboratory measurement confidence intervals')
(DATA/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'PASS: {len(checks)} checks, {len(rows)} comparison rows.')
