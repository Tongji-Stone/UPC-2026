from dataclasses import dataclass, replace, asdict
from typing import Callable

import numpy as np
from scipy.integrate import solve_ivp
from scipy.interpolate import RegularGridInterpolator


def linthorne_patel_coefficients(cd0=0.18, radius=0.11, kinematic_viscosity=1.5e-5):
    """LEGACY: historical Linthorne--Patel experiments, not the coupled paper model.

    Parameters radius and viscosity must match the associated PhysicsConfig.
    The paper discusses Cd0=0.1–0.2 for speeds 25–35 m/s.
    """
    if cd0 < 0 or radius <= 0 or kinematic_viscosity <= 0:
        raise ValueError('cd0 must be nonnegative; radius and viscosity must be positive')
    def lookup(reynolds, spin_parameter):
        # Re = 2 r v / nu; Sp = r omega / v.
        omega_rad_s = spin_parameter * reynolds * kinematic_viscosity / (2 * radius**2)
        rev_s = omega_rad_s / (2 * np.pi)
        return cd0 + .014 * rev_s, -.25 * np.expm1(-.5 * rev_s)
    return lookup


TEAMGEIST = (.4927, 12.58, 1.071, .1440, .1540, 23.17, 35.0)
MODEL_ID = 'KL18-Teamgeist-MuJoCo381-shell-v1'


def zero_spin_drag(speed):
    """Kiratidis--Leinweber (2018), Eq. 5/Table 1; speed in m/s."""
    a, vc, vs, bmin, bmax, vmin, vmax = TEAMGEIST
    def logistic(x):
        return 1/(1+np.exp(-abs(x))) if x >= 0 else np.exp(-abs(x))/(1+np.exp(-abs(x)))
    return ((a-bmin)*logistic(-(speed-vc)/vs)+bmin
            +(speed-vmin)*logistic((speed-vmin)/vs)*(bmax-bmin)/(vmax-vmin))


def kiratidis_leinweber_coefficients(reynolds, spin_parameter, radius=.11,
                                     kinematic_viscosity=1.5e-5):
    """Complete KL18 Eqs. 5,7--9, including the spin-dependent drag in CL."""
    if reynolds < 0 or spin_parameter < 0:
        raise ValueError('Re and Sp must be nonnegative')
    speed = reynolds*kinematic_viscosity/(2*radius)
    cd = zero_spin_drag(speed)+.514*spin_parameter
    ceiling = zero_spin_drag(0.)
    reference = zero_spin_drag(333793*kinematic_viscosity/(2*radius))+.514*.19
    cl = 1.15*spin_parameter**.83*max(ceiling-cd, 0.)/(ceiling-reference)
    return float(cd), float(cl)


def reynolds_table(reynolds, drag, lift):
    """Linearly interpolate supplied coefficients; refuse to extrapolate."""
    re = np.asarray(reynolds, float)
    cd, cl = np.asarray(drag, float), np.asarray(lift, float)
    if re.ndim != 1 or len(re) < 2 or np.any(np.diff(re) <= 0) or cd.shape != re.shape or cl.shape != re.shape:
        raise ValueError('coefficient table requires equal arrays and increasing Reynolds values')
    def lookup(value, spin):
        if not re[0] <= value <= re[-1]:
            raise ValueError('Reynolds number outside supplied coefficient table')
        return float(np.interp(value, re, cd)), float(np.interp(value, re, cl))
    return lookup


def reynolds_spin_table(reynolds, spin_parameter, drag, lift):
    """Bilinearly interpolate measured Re/Sp coefficient grids, without extrapolation."""
    re, sp = np.asarray(reynolds, float), np.asarray(spin_parameter, float)
    cd, cl = np.asarray(drag, float), np.asarray(lift, float)
    if (re.ndim != 1 or sp.ndim != 1 or len(re) < 2 or len(sp) < 2
        or np.any(np.diff(re) <= 0) or np.any(np.diff(sp) <= 0)
        or cd.shape != (len(re), len(sp)) or cl.shape != cd.shape):
        raise ValueError('coefficient grids must match increasing Re and spin axes')
    cd_interp = RegularGridInterpolator((re, sp), cd, bounds_error=True)
    cl_interp = RegularGridInterpolator((re, sp), cl, bounds_error=True)
    def lookup(value, spin):
        point = np.array([[value, spin]])
        return float(cd_interp(point)[0]), float(cl_interp(point)[0])
    return lookup


@dataclass(frozen=True)
class PhysicsConfig:
    mass: float = 0.43
    radius: float = 0.11
    air_density: float = 1.2
    kinematic_viscosity: float = 1.5e-5
    gravity: float = 9.81
    drag_coefficient: float = 0.25
    lift_coefficient: float = 0.2
    drag_scale: float = 1.
    lift_scale: float = 1.
    coefficient_mode: str = 'constant'
    constant_acceleration: tuple | None = None
    use_gravity: bool = True
    use_drag: bool = False
    use_magnus: bool = False
    wind: tuple = (0., 0., 0.)
    spin_decay: float = 0.
    use_rotational_drag: bool = False
    use_viscous_torque: bool = True
    angular_drag_coefficient: float = 1.5
    inertia_coefficient: float = 2./3.
    model_id: str = 'comparison'
    # Callback returns (Cd, Cl), with Re and spin parameter as inputs.
    coefficients: Callable[[float, float], tuple[float, float]] | None = None

    @classmethod
    def for_model(cls, name, **overrides):
        options = {
            "M0": dict(use_gravity=False),
            "M1": dict(model_id='four-model-v2-M1'),
            "M2": dict(use_drag=True, model_id='four-model-v2-M2'),
            "M3": dict(use_gravity=False, constant_acceleration=(0., 0., -9.81), model_id='constant-acceleration-M3'),
            "M4": dict(use_drag=True, use_magnus=True, coefficient_mode='linear_spin',
                       model_id='four-model-v2-M4'),
            "M5": dict(use_drag=True, use_magnus=True, use_rotational_drag=True,
                       model_id=MODEL_ID),
        }
        if name not in options:
            raise ValueError("model must be M0, M1, M2, M3, M4 or archived M5")
        cfg = replace(cls(**options[name]), **overrides)
        if name in ('M2', 'M4'):
            cd, cl = kiratidis_leinweber_coefficients(333793, .19,
                cfg.radius, cfg.kinematic_viscosity)
            cfg = replace(cfg, drag_coefficient=overrides.get('drag_coefficient', cd),
                          lift_coefficient=overrides.get('lift_coefficient', cl/.19 if name == 'M4' else cl))
        return cfg

    @property
    def moment_of_inertia(self):
        return self.inertia_coefficient*self.mass*self.radius**2

    @property
    def dynamic_viscosity(self):
        return self.air_density*self.kinematic_viscosity


@dataclass
class FlightResult:
    t: np.ndarray
    position: np.ndarray
    velocity: np.ndarray
    spin: np.ndarray
    acceleration: np.ndarray
    forces: dict
    event: dict
    torque: np.ndarray
    angular_acceleration: np.ndarray
    diagnostics: dict


def coefficients(velocity, spin, config):
    speed = float(np.linalg.norm(np.asarray(velocity)-np.asarray(config.wind)))
    if speed <= 1e-12:
        return 0., 0., 0., 0., speed
    re = 2*config.radius*speed/config.kinematic_viscosity
    sp = config.radius*float(np.linalg.norm(spin))/speed
    if config.coefficients is not None:
        cd, cl = config.coefficients(re, sp)
    elif config.coefficient_mode == 'linear_spin':
        cd, cl = config.drag_coefficient, config.lift_coefficient * sp
    elif config.model_id == MODEL_ID or config.coefficient_mode == 'KL18':
        cd, cl = kiratidis_leinweber_coefficients(
            re, sp, config.radius, config.kinematic_viscosity)
    else:
        cd, cl = config.drag_coefficient, config.lift_coefficient
    return float(cd), float(cl), re, sp, speed


def rotational_torque(spin, config):
    """MuJoCo 3.8.1 ellipsoid model, spherical specialization; SI torque."""
    w = np.asarray(spin, dtype=float)
    if not config.use_rotational_drag:
        return -config.moment_of_inertia*config.spin_decay*w
    r = config.radius
    factor = ((8*np.pi/15)*config.air_density*config.angular_drag_coefficient*r**5*np.linalg.norm(w)
              +(8*np.pi*config.dynamic_viscosity*r**3 if config.use_viscous_torque else 0.))
    return -factor*w


def state_derivative(t, state, config):
    """The single nine-state RHS used for prediction and inverse fitting."""
    f = forces(state[3:6], state[6:9], config)
    return np.r_[state[3:6], sum(f.values())/config.mass,
                 rotational_torque(state[6:9], config)/config.moment_of_inertia]


def validate_config(config):
    if min(config.mass, config.radius, config.kinematic_viscosity,
           config.inertia_coefficient) <= 0 or config.air_density < 0:
        raise ValueError('positive ball, viscosity and inertia parameters required')
    if config.spin_decay < 0 or config.angular_drag_coefficient < 0:
        raise ValueError('damping parameters must be nonnegative')
    if min(config.drag_scale, config.lift_scale) < 0:
        raise ValueError('force correction factors must be nonnegative')
    if config.use_rotational_drag and config.spin_decay != 0:
        raise ValueError('rotational torque and legacy spin_decay cannot be combined')


def config_record(config):
    record = asdict(config)
    record.pop('coefficients')
    if (config.model_id == MODEL_ID or config.coefficient_mode == 'KL18') and config.coefficients is None:
        record.pop('drag_coefficient')
        record.pop('lift_coefficient')
    record.update(dynamic_viscosity=config.dynamic_viscosity,
                  moment_of_inertia=config.moment_of_inertia,
                  coefficient_callback='custom' if config.coefficients else 'model default',
                  sources={'CD_CL': ('Fixed CD and linear CL=alpha*Sp, anchored to Kiratidis & Leinweber 2018 reference point' if config.coefficient_mode == 'linear_spin' else 'Kiratidis & Leinweber 2018 reference point; fixed constants' if config.coefficient_mode == 'constant' else 'Kiratidis & Leinweber 2018, Eqs 5,7--9/Table 1'),
                           'mass_radius_gravity':'Maponi & Piombin 2025 Table 1: 0.43 kg, 0.11 m, 9.81 m/s2',
                           'torque':'Grad 2026 supp 8.4; MuJoCo 3.8.1 spherical ellipsoid',
                           'angular_drag':'MuJoCo default 1.5, a declared reference setting',
                           'inertia':'Maponi & Piombin 2025 Eq 6, thin spherical shell',
                           'air':'rho=1.2 from Asai 2007; nu=1.5e-5 reference air setting'},
                  assumptions=['still air reference unless wind is supplied',
                               'constant spin unless rotational torque is enabled',
                               'isotropic thin shell', 'sin(theta) oblique-spin extension'])
    return record


def forces(velocity, spin, config):
    """Return force components on ball, in newtons."""
    v = np.asarray(velocity, dtype=float) - np.asarray(config.wind, dtype=float)
    omega = np.asarray(spin, dtype=float)
    speed = np.linalg.norm(v)
    weight = (config.mass * np.asarray(config.constant_acceleration, dtype=float)
              if config.constant_acceleration is not None else
              np.array([0., 0., -config.mass * config.gravity if config.use_gravity else 0.]))
    drag = np.zeros(3)
    magnus = np.zeros(3)
    if speed > 1e-12:
        cd, cl, _, _, _ = coefficients(velocity, spin, config)
        q_area = 0.5 * config.air_density * np.pi * config.radius**2 * speed**2
        if config.use_drag:
            drag = -q_area * config.drag_scale * cd * v / speed
        cross = np.cross(omega, v)
        norm = np.linalg.norm(cross)
        if config.use_magnus and norm > 1e-12:
            # The literature fit is for transverse spin. Project its effect
            # onto the plane perpendicular to airflow for an oblique spin axis.
            sin_angle = norm / (np.linalg.norm(omega) * speed)
            magnus = q_area * config.lift_scale * cl * sin_angle * cross / norm
    return {"gravity": weight, "drag": drag, "magnus": magnus}


def simulate(position, velocity, spin=(0., 0., 0.), config=None,
             t_span=(0., 1.), plane_x=11., rtol=1e-8, atol=1e-10,
             max_step=np.inf):
    """Integrate until forward plane crossing, descending ground contact, or t_span end."""
    config = config or PhysicsConfig.for_model("M1")
    validate_config(config)
    if t_span[1] <= t_span[0]:
        raise ValueError("t_span must be increasing")
    state = np.concatenate([np.asarray(position, dtype=float), np.asarray(velocity, dtype=float), np.asarray(spin, dtype=float)])
    if state.shape != (9,) or not np.isfinite(state).all():
        raise ValueError("position, velocity and spin must be finite 3-vectors")
    if state[2] < config.radius - 1e-10:
        raise ValueError("ball center starts below ground contact height")
    def plane(t, y):
        return y[0] - plane_x
    plane.terminal = True
    plane.direction = 1
    def ground(t, y):
        return y[2] - config.radius
    ground.terminal = True
    ground.direction = -1
    solution = solve_ivp(lambda t,y:state_derivative(t,y,config), t_span, state,
                         events=(plane, ground), rtol=rtol, atol=atol, max_step=max_step,
                         method='DOP853')
    if not solution.success:
        raise RuntimeError(solution.message)
    name = "plane" if len(solution.t_events[0]) else "ground" if len(solution.t_events[1]) else "none"
    event = {"type": name, "time": float(solution.t[-1]) if name != "none" else None,
             "position": solution.y[:3, -1].copy() if name != "none" else None,
             "velocity": solution.y[3:6, -1].copy() if name != "none" else None,
             "spin": solution.y[6:9, -1].copy() if name != "none" else None}
    parts = [forces(y[3:6], y[6:9], config) for y in solution.y.T]
    components = {key: np.array([item[key] for item in parts]) for key in ("gravity", "drag", "magnus")}
    acceleration = sum(components.values()) / config.mass
    torques = np.array([rotational_torque(w,config) for w in solution.y[6:9].T])
    c = np.array([coefficients(v,w,config) for v,w in zip(solution.y[3:6].T,solution.y[6:9].T)])
    diagnostic = dict(speed_range=[float(c[:,4].min()),float(c[:,4].max())],
        Re_range=[float(c[:,2].min()),float(c[:,2].max())],
        Sp_range=[float(c[:,3].min()),float(c[:,3].max())],
        above_35_m_s=bool(c[:,4].max()>35),
        outside_A07_spinning_Re=bool(c[:,2].min()<333793 or c[:,2].max()>455172),
        above_A07_global_Sp=bool(c[:,3].max()>.32),
        note='These are coverage flags, not a claim of support over a rectangular Re-Sp grid.')
    return FlightResult(solution.t, solution.y[:3].T, solution.y[3:6].T,
                        solution.y[6:9].T, acceleration, components, event,
                        torques, torques/config.moment_of_inertia, diagnostic)
