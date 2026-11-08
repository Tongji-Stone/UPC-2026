"""Additional analytic and physical checks, with no changes to paper sources."""
import json
import math
import numpy as np
from scipy.integrate import solve_ivp
from sensitivity_v2_compute import (BASE,CFG,P0,DATA,flight,rhs_factory,drag0,hashes,save_json)


def main():
    vacuum=flight(BASE,{**CFG,'rho':0.},tight=True)
    t=11/BASE[0]
    expected=[BASE[1]*t,P0[2]+BASE[2]*t-.5*9.81*t*t,t]
    vacuum_error=max(abs(a-b) for a,b in zip([vacuum['y'],vacuum['z'],vacuum['t']],expected))
    f=flight(BASE,tight=True)
    sol=solve_ivp(rhs_factory(BASE[3:],CFG),(0,f['t']),np.r_[P0,BASE[:3]],
                  method='DOP853',rtol=1e-12,atol=1e-14,max_step=.005,
                  t_eval=np.linspace(0,f['t'],401))
    energy=.5*CFG['mass']*np.sum(sol.y[3:]**2,axis=0)+CFG['mass']*9.81*sol.y[2]
    speed=np.linalg.norm(sol.y[3:],axis=0)
    sp=CFG['radius']*np.linalg.norm(BASE[3:])/speed
    cd=np.array([drag0(v) for v in speed])+.514*sp
    den=drag0(0)-drag0(333793*CFG['nu']/(2*CFG['radius']))-.514*.19
    cl=1.15*sp**.83*np.maximum(drag0(0)-cd,0)/den
    peak_sp=.83*(drag0(0)-drag0(speed[0]))/(1.83*.514)
    v=json.loads((DATA/'verification.json').read_text(encoding='utf-8'))
    extra=dict(vacuum_analytic_max_difference=vacuum_error,
        mechanical_energy_initial_J=float(energy[0]),mechanical_energy_final_J=float(energy[-1]),
        maximum_sampled_energy_increment_J=float(np.diff(energy).max()),
        baseline_initial_CD=float(cd[0]),baseline_final_CD=float(cd[-1]),
        baseline_initial_CL=float(cl[0]),baseline_final_CL=float(cl[-1]),
        baseline_initial_Sp=float(sp[0]),baseline_final_Sp=float(sp[-1]),
        initial_CL_peak_Sp=float(peak_sp),
        protected_unchanged=v['protected_before']==hashes())
    assert vacuum_error<1e-10 and extra['maximum_sampled_energy_increment_J']<0 and extra['protected_unchanged']
    save_json('physical_checks.json',extra)
    print(json.dumps(extra,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
