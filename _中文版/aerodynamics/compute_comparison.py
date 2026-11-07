"""Reproduce published coefficient laws and compare them with digitized A07 data.

Only coefficient tables are calculated. No trajectory solver is imported or run.
Python 3.10+; standard library only. Paths are relative to this file.
"""
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RE = 455172.0
RADIUS = 0.11
SPEED = 30.0
# Reconstructed from the experiment's Re / wind-speed legend, not a reported viscosity.
NU = 2 * RADIUS * SPEED / RE
PARAMETERS = dict(a=.4927, vc=12.58, vs=1.071, bmin=.1440,
                  bmax=.1540, vmin=23.17, vmax=35.0, spin_slope=.514)


def sigmoid(x):
    if x >= 0:
        return 1 / (1 + math.exp(-x))
    e = math.exp(x)
    return e / (1 + e)


def baseline(v):
    p = PARAMETERS
    return ((p['a'] - p['bmin']) * sigmoid(-(v-p['vc'])/p['vs'])
            + p['bmin'] + (v-p['vmin']) * sigmoid((v-p['vmin'])/p['vs'])
            * (p['bmax']-p['bmin'])/(p['vmax']-p['vmin']))


def cd(re, sp, nu=NU):
    return baseline(re*nu/(2*RADIUS)) + PARAMETERS['spin_slope']*sp


def cl(re, sp, nu=NU):
    ceiling = baseline(0)
    reference = cd(333793, .19, nu)
    return 1.15*sp**.83 * max(ceiling-cd(re, sp, nu), 0)/(ceiling-reference)


def cq(re, sp, c_angular=1.5):
    return (16/15)*c_angular*sp**2 + 32*sp/re


def write_csv(name, rows):
    with (ROOT/'data'/name).open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    source = ROOT/'data'/'asai2007_digitized.csv'
    with source.open(encoding='utf-8-sig', newline='') as f:
        points = list(csv.DictReader(f))
    selected = []
    curves = []
    metrics = {}
    for coefficient, figure, function in [('CD','fig8',cd),('CL','fig9',cl)]:
        group = sorted([p for p in points if p['ball']=='Teamgeist'
                        and p['figure']==figure and float(p['Re'])==RE],
                       key=lambda p: float(p['Sp']))
        assert len(group)==5
        for p in group:
            sp, measured = float(p['Sp']), float(p['value'])
            predicted = function(RE, sp)
            selected.append(dict(coefficient=coefficient, point_id=p['point_id'],
                                 figure=figure, original_symbol=p['original_symbol'],
                                 Re=RE, v_m_s=SPEED, nu_m2_s=NU, Sp=sp,
                                 measured=measured, formula=predicted,
                                 residual=predicted-measured,
                                 read_bound=float(p['coefficient_read_bound'])))
        residuals = [r['residual'] for r in selected if r['coefficient']==coefficient]
        metrics[coefficient] = dict(n=len(group),
            MAE=sum(abs(x) for x in residuals)/len(group),
            RMSE=math.sqrt(sum(x*x for x in residuals)/len(group)),
            bias=sum(residuals)/len(group), max_abs=max(abs(x) for x in residuals),
            sp_min=float(group[0]['Sp']), sp_max=float(group[-1]['Sp']))
        lo, hi = metrics[coefficient]['sp_min'], metrics[coefficient]['sp_max']
        for i in range(401):
            sp = lo+(hi-lo)*i/400
            curves.append(dict(coefficient=coefficient, Re=RE, Sp=sp,
                               formula=function(RE, sp)))
    # Algebraic/physical checks target the normalization and the reference anchor.
    assert abs(cl(333793, .19)-1.15*.19**.83) < 1e-12
    assert cl(RE,0)==0 and cq(RE,0)==0
    assert abs(cd(RE,0)-baseline(SPEED)) < 1e-12
    for sp in (.01,.1,.3):
        omega=sp*SPEED/RADIUS
        rho=1.2
        mu=rho*NU
        direct=(8*math.pi/15)*rho*1.5*RADIUS**5*omega**2+8*math.pi*mu*RADIUS**3*omega
        normalized=.5*rho*SPEED**2*math.pi*RADIUS**3*cq(RE,sp)
        assert math.isclose(direct, normalized, rel_tol=1e-12)
        assert math.isclose(cq(RE,sp)/sp**2, 16/15*1.5+32/(RE*sp), rel_tol=1e-12)
        assert -direct*omega < 0  # Rotational work is dissipative.
    write_csv('comparison_points.csv', selected)
    write_csv('formula_curves.csv', curves)
    summary = dict(ball='Teamgeist FRP replica', Re=RE, speed_m_s=SPEED,
        radius_m=RADIUS, air_density_kg_m3=1.2, nu_reconstructed_m2_s=NU,
        nu_note='Reconstructed from the experimental legend; not reported viscosity.',
        parameters=PARAMETERS, ceiling=baseline(0), reference_cd=cd(333793,.19),
        reference_cl=cl(333793,.19), metrics=metrics,
        digitized_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        data_note='Digitized publication markers; shared data with the published fit.',
        formulas='Kiratidis and Leinweber (2018), Eqs. (5), (7)-(9), Table 1.',
        checks='Reference anchor, zero spin, CD baseline, CQ normalization, dissipation passed.')
    (ROOT/'data'/'comparison_summary.json').write_text(json.dumps(summary,indent=2), encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
