"""Literature formula reproductions. SI units; no changes to the flight solver.

G10: Goff & Carre (2010), Eqs 3,4. KL18: Kiratidis & Leinweber (2018),
Eqs 5-9/Table 1. Eq 8 alone is an intermediate reference curve.
"""
import math

PARAMS = {
    'Teamgeist': (.4927,12.58,1.071,.1440,.1540,23.17,35.),
    'Tango12': (.5452,12.86,1.304,.1657,.1953,16.22,35.),
    'Jabulani': (.4839,18.69,1.377,.1413,.1780,23.29,35.),
    'Brazuca': (.4740,12.92,1.,.1657,.2112,14.61,35.),
}


def sigmoid(x):
    if x>=0: return 1/(1+math.exp(-x))
    e=math.exp(x)
    return e/(1+e)


def cd_g10_v(v):
    return .155+.346*sigmoid(-(v-12.19)/1.309)


def cd_g10(v,sp):
    # Original text gives strict inequalities; equality assigned to Eq 3.
    return .4127*sp**.3056 if v>12.19 and sp>.05 else cd_g10_v(v)


def cd_kl18_v(v,ball='Teamgeist'):
    a,vc,vs,bmin,bmax,vmin,vmax=PARAMS[ball]
    return (a-bmin)*sigmoid(-(v-vc)/vs)+bmin+(v-vmin)*sigmoid((v-vmin)/vs)*(bmax-bmin)/(vmax-vmin)


def spin_slope(ball='Teamgeist'):
    lo,hi=cd_kl18_v(30,'Teamgeist'),cd_kl18_v(30,'Brazuca')
    return .514*(1+.05*(cd_kl18_v(30,ball)-lo)/(hi-lo))


def cd_kl18(v,sp,ball='Teamgeist'):
    return cd_kl18_v(v,ball)+spin_slope(ball)*sp


def cl_kl18_sp(sp):
    return 1.15*sp**.83


def cl_kl18(v,sp,ball='Teamgeist',nu=1.5e-5,r=.11):
    # Re=0 ceiling: zero-spin baseline (a to within 3e-6), not a spin-dependent ceiling.
    ceiling=cd_kl18_v(0,'Teamgeist')
    ref=cd_kl18(333793*nu/(2*r),.19,'Teamgeist')
    return cl_kl18_sp(sp)*max(ceiling-cd_kl18(v,sp,ball),0)/(ceiling-ref)


def cq_and_torque(v,sp,r=.11,rho=1.2,nu=1.5e-5,c_ang=1.5,viscous=True):
    """MuJoCo 3.8.1 ellipsoid sphere; Q scaled by 0.5*rho*pi*r^2*r.

    Cq_v = Q/(q A r); Cq_w = Q/[0.5 rho (r*w)^2 A r].
    Cq_w is undefined at w=0; actual torque vanishes continuously.
    """
    re=2*r*v/nu;omega=sp*v/r
    cqv=16/15*c_ang*sp**2+(32*sp/re if viscous else 0)
    cqw=cqv/sp**2 if sp>0 else None
    q=cqv*.5*rho*math.pi*r**3*v*v
    return cqv,cqw,q,omega


def literature_coefficients(reynolds,spin_parameter,nu=1.5e-5,radius=.11):
    """Drop-in candidate for PhysicsConfig.coefficients; KL18, not auto-installed."""
    if reynolds<0 or spin_parameter<0: raise ValueError('Re and Sp must be nonnegative')
    v=reynolds*nu/(2*radius)
    return cd_kl18(v,spin_parameter),cl_kl18(v,spin_parameter,nu=nu,r=radius)
