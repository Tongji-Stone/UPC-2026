"""Analytic and physical checks for constant CD and linear CL=alpha*Sp."""
import json
import numpy as np
from scipy.integrate import solve_ivp
from sensitivity_v2_compute import BASE, CFG, P0, flight, rhs_factory, hashes, save_json
from football.physics import PhysicsConfig


def main():
    before = hashes()
    vacuum = flight(BASE, {**CFG, 'rho': 0.}, tight=True)
    t = 11 / BASE[0]
    expected = [BASE[1]*t, P0[2]+BASE[2]*t-.5*9.81*t*t, t]
    error = max(abs(a-b) for a, b in zip([vacuum['y'],vacuum['z'],vacuum['t']], expected))
    baseline = flight(BASE, tight=True)
    rhs = rhs_factory(BASE[3:], CFG)
    sol = solve_ivp(rhs, (0., baseline['t']), np.r_[P0, BASE[:3]],
        method='DOP853', rtol=1e-12, atol=1e-14, max_step=.005,
        t_eval=np.linspace(0., baseline['t'], 401))
    velocity = sol.y[3:].T
    speed = np.linalg.norm(velocity, axis=1)
    ref = PhysicsConfig.for_model('M4')
    cd = CFG['ad'] * ref.drag_coefficient
    alpha = CFG['al'] * ref.lift_coefficient
    lift = .5*CFG['rho']*np.pi*CFG['radius']**3*alpha*np.cross(BASE[3:], velocity)
    drag_power = -.5*CFG['rho']*np.pi*CFG['radius']**2*cd*speed**3
    acceleration = np.array([rhs(t, y)[3:] for t,y in zip(sol.t, sol.y.T)])
    energy_power = CFG['mass']*(np.einsum('ij,ij->i', velocity, acceleration)+9.81*velocity[:,2])
    energy = .5*CFG['mass']*speed**2+CFG['mass']*9.81*sol.y[2]
    changed = BASE.copy(); changed[3:] *= 1.1
    compensated = flight(changed, {**CFG,'al':CFG['al']/1.1}, tight=True)
    compensation_error = float(np.linalg.norm([compensated[k]-baseline[k] for k in ['y','z','t']]))
    result = dict(model='constant CD; CL=alpha*Sp', mass_kg=CFG['mass'],radius_m=CFG['radius'],
        vacuum_analytic_max_difference=error,mechanical_energy_initial_J=float(energy[0]),
        mechanical_energy_final_J=float(energy[-1]),maximum_sampled_energy_increment_J=float(np.diff(energy).max()),
        maximum_lift_power_W=float(abs(np.einsum('ij,ij->i', lift,velocity)).max()),
        maximum_energy_balance_difference_W=float(abs(energy_power-drag_power).max()),
        actual_CD=cd,actual_alpha=alpha,initial_CL=float(alpha*CFG['radius']*np.linalg.norm(BASE[3:])/speed[0]),
        final_CL=float(alpha*CFG['radius']*np.linalg.norm(BASE[3:])/speed[-1]),
        exact_spin_alpha_compensation_difference=compensation_error,protected_unchanged=before==hashes())
    assert error < 1e-10 and result['maximum_sampled_energy_increment_J'] < 0
    assert result['maximum_lift_power_W'] < 1e-10 and result['maximum_energy_balance_difference_W'] < 1e-10
    assert compensation_error < 1e-10 and result['protected_unchanged']
    result['all_passed'] = True
    save_json('physical_checks.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
