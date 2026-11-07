"""Recover plotted marker centers, not laboratory raw records, from Asai (2007).

Usage: python scripts/extract_aerodynamic_points.py [path/to/local/Asai.pdf]
PDF coordinates are points (1/72 inch), origin top-left. Fixed path indices
refer to the SHA256-identified user-supplied PDF. No fitted curve is digitized.
"""
import csv
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/sources/aerodynamic_parameters'


def main():
    pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / 'Fundamental_aerodynamics_of_the_soccer_ball.pdf'
    doc = fitz.open(pdf)
    p4, p6 = doc[3].get_drawings(), doc[5].get_drawings()
    # Calibration from visible tick paths; log axis is independently checked at 1e5.
    cal = {
        'fig4': dict(page=4, x_type='log', x_pt=[95.85400390625,208.8199920654297], x_value=[40000,600000], y_pt=[608.9960327148438,495.8330383300781], y_value=[0,.5]),
        'fig8': dict(page=6, x_type='linear', x_pt=[99.6290054321289,132.80599975585938,165.98300170898438,199.16000366210938,232.33700561523438], x_value=[0,.1,.2,.3,.4], y_pt=[604.9349365234375,571.7579345703125,538.5809326171875,505.4039306640625,472.2269287109375],y_value=[0,.1,.2,.3,.4]),
        'fig9': dict(page=6,x_type='linear',x_pt=[346.4769287109375,377.4039306640625,408.5809326171875,439.7579345703125,470.6849365234375],x_value=[0,.1,.2,.3,.4],y_pt=[624.6829223632812,593.5059204101562,562.0789184570312,530.4019165039062,499.97491455078125],y_value=[0,.1,.2,.3,.4])}
    for c in cal.values():
        xv = np.log(c['x_value']) if c['x_type']=='log' else c['x_value']
        c['x_affine'] = np.polyfit(c['x_pt'],xv,1).tolist()
        c['y_affine'] = np.polyfit(c['y_pt'],c['y_value'],1).tolist()
        c['coordinate_tolerance_pt'] = 1.0
        c['tolerance_meaning'] = 'conservative graphical reading bound; not experimental SD/CI'
    cal['fig4']['check_Re_at_100000_tick'] = float(np.exp(np.polyval(cal['fig4']['x_affine'],134.03099060058594)))
    assert abs(cal['fig4']['check_Re_at_100000_tick']/100000-1) < .01
    groups = [
        ('fig4','CD','Teamgeist',None,list(range(143,170,2))+[172,174,176,178]),
        ('fig4','CD','Fevernova',None,list(range(59,99,2))),
        ('fig4','CD','Roteiro',None,list(range(99,143,2))),
        ('fig8','CD','Teamgeist',455172,list(range(24,29))),
        ('fig8','CD','Teamgeist',424827,list(range(30,35))),
        ('fig8','CD','Teamgeist',394482,list(range(54,59))),
        ('fig8','CD','Teamgeist',364137,list(range(48,53))),
        ('fig8','CD','Teamgeist',333793,[37,39,41,43,45]),
        ('fig9','CL','Teamgeist',455172,list(range(81,86))),
        ('fig9','CL','Teamgeist',424827,list(range(87,92))),
        ('fig9','CL','Teamgeist',394482,list(range(111,116))),
        ('fig9','CL','Teamgeist',364137,list(range(105,110))),
        ('fig9','CL','Teamgeist',333793,[94,96,98,100,102]),
    ]
    rows=[]
    for fig,coef,ball,re,ids in groups:
        c=cal[fig]
        for idx in ids:
            d=(p4 if fig=='fig4' else p6)[idx];r=d['rect']
            x,y=(r.x0+r.x1)/2,(r.y0+r.y1)/2
            xx=float(np.polyval(c['x_affine'],x));yy=float(np.polyval(c['y_affine'],y))
            if fig=='fig4':
                xx=float(np.exp(xx)); reynolds,sp=xx,0.
                dx=xx*(np.exp(abs(c['x_affine'][0]))-1)
            else: reynolds,sp=re,xx;dx=abs(c['x_affine'][0])
            rows.append(dict(point_id=f'A07_{fig}_{idx}',source='Asai2007',figure=fig,page=c['page'],ball=ball,
                coefficient=coef,original_symbol='Cs' if coef=='CL' else 'Cd',Re=reynolds,Sp=sp,value=yy,
                x_pdf_pt=x,y_pdf_pt=y,path_index=idx,x_read_bound=dx,coefficient_read_bound=abs(c['y_affine'][0]),
                acquisition='PDF_vector_marker_center',experimental_uncertainty='',
                note='FRP Teamgeist replica' if fig!='fig4' else 'nonspinning commercial ball'))
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'asai2007_digitized.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (OUT/'digitization_calibration.json').write_text(json.dumps(dict(pdf_name=pdf.name,pdf_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),calibration=cal,point_count=len(rows)),ensure_ascii=False,indent=2),encoding='utf-8')
    # Crop originals and overlay recovered centers for an auditable visual check.
    for name,pg,clip in [('fig4',3,(65,485,303,637)),('fig8',5,(68,466,296,637)),('fig9',5,(316,485,545,658))]:
        doc[pg].get_pixmap(matrix=fitz.Matrix(4,4),clip=fitz.Rect(*clip)).save(OUT/f'asai2007_{name}.png')
        overlay=fitz.open();overlay.insert_pdf(doc,from_page=pg,to_page=pg)
        for row in rows:
            if row['figure']==name and row['ball']=='Teamgeist':
                overlay[0].draw_circle((row['x_pdf_pt'],row['y_pdf_pt']),1.15,color=(.85,.18,.1),width=.5)
        overlay[0].get_pixmap(matrix=fitz.Matrix(4,4),clip=fitz.Rect(*clip)).save(OUT/f'asai2007_{name}_audit.png')
    print(f'Extracted {len(rows)} plotted data markers; SHA256 saved; log calibration checked.')


if __name__=='__main__': main()
