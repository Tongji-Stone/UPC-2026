"""Current early-frame evaluation; legacy M5 labels alias the coupled model."""
import numpy as np
from football.physics import PhysicsConfig, simulate
from football.inference.physical_fit import fit_velocity
from football.inference.coupled_fit import fit_initial_state
from coupled_compute import real

def polynomial_goal(t,p,plane):
    if len(t)<3: return 'insufficient_observations',None
    h=np.column_stack((t, .5*t*t))
    params=np.linalg.lstsq(h[1:],(p-p[0])[1:],rcond=None)[0]
    vx,ax=params[:,0]; vz,az=params[:,2]
    def roots(a,b,c):
        coeff=np.trim_zeros(np.array([a,b,c]),'f')
        return np.roots(coeff) if len(coeff)>1 else []
    valid=[r.real for r in roots(.5*ax,vx,p[0,0]-plane)
           if abs(r.imag)<1e-8 and r.real>=t[-1] and vx+ax*r.real>0 and r.real<=3]
    if not valid:return 'no_plane_crossing',None
    arrival=min(valid)
    ground=[r.real for r in roots(.5*az,vz,p[0,2]-.11)
            if abs(r.imag)<1e-8 and 1e-9<r.real<arrival and vz+az*r.real<0]
    if ground:return 'ground',None
    return 'plane',(p[0]+arrival*params[0]+.5*arrival**2*params[1])[1:]


def early_inputs(times,positions,cutoff=.10):
    times=np.asarray(times,float);positions=np.asarray(positions,float)
    mask=times<=times[0]+cutoff+1e-10
    return times[mask]-times[0],positions[mask].copy()


def physical_goal(model,t,p,plane):
    cfg=PhysicsConfig.for_model('M5' if model.startswith('M5') else model)
    if model.startswith('M5'):
        q=np.array(fit_initial_state(t,p,cfg)['best']['initial_state'])
    else:
        q=np.r_[fit_velocity(t,p,cfg)['velocity'],np.zeros(3)]
    flight=simulate(p[0],q[:3],q[3:],cfg,t_span=(0,3),plane_x=plane)
    if flight.event['type']!='plane':return flight.event['type'],None
    if flight.event['time']<t[-1]:return 'plane_before_last_observation',None
    return 'plane',flight.event['position'][1:]


if __name__=='__main__':real()
