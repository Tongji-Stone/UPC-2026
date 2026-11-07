from dataclasses import dataclass, field, replace
from typing import Callable

import numpy as np
from scipy.integrate import solve_ivp
from scipy.interpolate import RegularGridInterpolator


def linthorne_patel_coefficients(cd0=0.18, radius=0.11, kinematic_viscosity=1.5e-5):
    """Linthorne & Patel (2011), Eqs. 3–4. Spin is in revolutions per second.

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
    use_gravity: bool = True
    use_drag: bool = False
    use_magnus: bool = False
    wind: tuple = (0., 0., 0.)
    spin_decay: float = 0.
    # Callback returns (Cd, Cl), with Re and spin parameter as inputs.
    coefficients: Callable[[float, float], tuple[float, float]] | None = None

    @classmethod
    def for_model(cls, name, **overrides):
        options = {
            "M0": dict(use_gravity=False),
            "M1": {},
            "M3": dict(use_drag=True),
            "M4": dict(use_drag=True, use_magnus=True),
            "M5": dict(use_drag=True, use_magnus=True),
        }
        if name not in options:
            raise ValueError("model must be M0, M1, M3, M4 or M5")
        return replace(cls(**options[name]), **overrides)


@dataclass
class FlightResult:
    t: np.ndarray
    position: np.ndarray
    velocity: np.ndarray
    spin: np.ndarray
    acceleration: np.ndarray
    forces: dict
    event: dict


def forces(velocity, spin, config):
    """Return force components on ball, in newtons."""
    v = np.asarray(velocity, dtype=float) - np.asarray(config.wind, dtype=float)
    omega = np.asarray(spin, dtype=float)
    speed = np.linalg.norm(v)
    weight = np.array([0., 0., -config.mass * config.gravity if config.use_gravity else 0.])
    drag = np.zeros(3)
    magnus = np.zeros(3)
    if speed > 1e-12:
        re = 2 * config.radius * speed / config.kinematic_viscosity
        sp = config.radius * np.linalg.norm(omega) / speed
        cd, cl = (config.coefficients(re, sp) if config.coefficients is not None
                  else (config.drag_coefficient, config.lift_coefficient))
        q_area = 0.5 * config.air_density * np.pi * config.radius**2 * speed**2
        if config.use_drag:
            drag = -q_area * cd * v / speed
        cross = np.cross(omega, v)
        norm = np.linalg.norm(cross)
        if config.use_magnus and norm > 1e-12:
            # The literature fit is for transverse spin. Project its effect
            # onto the plane perpendicular to airflow for an oblique spin axis.
            sin_angle = norm / (np.linalg.norm(omega) * speed)
            magnus = q_area * cl * sin_angle * cross / norm
    return {"gravity": weight, "drag": drag, "magnus": magnus}


def simulate(position, velocity, spin=(0., 0., 0.), config=None,
             t_span=(0., 1.), plane_x=11., rtol=1e-8, atol=1e-10,
             max_step=np.inf):
    """Integrate until forward plane crossing, descending ground contact, or t_span end."""
    config = config or PhysicsConfig.for_model("M1")
    if config.mass <= 0 or config.radius <= 0 or config.kinematic_viscosity <= 0:
        raise ValueError("mass, radius and viscosity must be positive")
    if config.spin_decay < 0 or t_span[1] <= t_span[0]:
        raise ValueError("spin_decay must be nonnegative and t_span increasing")
    state = np.concatenate([np.asarray(position, dtype=float), np.asarray(velocity, dtype=float), np.asarray(spin, dtype=float)])
    if state.shape != (9,) or not np.isfinite(state).all():
        raise ValueError("position, velocity and spin must be finite 3-vectors")
    if state[2] < config.radius - 1e-10:
        raise ValueError("ball center starts below ground contact height")
    def rhs(t, y):
        components = forces(y[3:6], y[6:9], config)
        return np.concatenate((y[3:6], sum(components.values()) / config.mass,
                               -config.spin_decay * y[6:9]))
    def plane(t, y):
        return y[0] - plane_x
    plane.terminal = True
    plane.direction = 1
    def ground(t, y):
        return y[2] - config.radius
    ground.terminal = True
    ground.direction = -1
    solution = solve_ivp(rhs, t_span, state, events=(plane, ground), rtol=rtol,
                         atol=atol, max_step=max_step)
    if not solution.success:
        raise RuntimeError(solution.message)
    name = "plane" if len(solution.t_events[0]) else "ground" if len(solution.t_events[1]) else "none"
    event = {"type": name, "time": float(solution.t[-1]) if name != "none" else None,
             "position": solution.y[:3, -1].copy() if name != "none" else None,
             "velocity": solution.y[3:6, -1].copy() if name != "none" else None}
    parts = [forces(y[3:6], y[6:9], config) for y in solution.y.T]
    components = {key: np.array([item[key] for item in parts]) for key in ("gravity", "drag", "magnus")}
    acceleration = sum(components.values()) / config.mass
    return FlightResult(solution.t, solution.y[:3].T, solution.y[3:6].T,
                        solution.y[6:9].T, acceleration, components, event)
