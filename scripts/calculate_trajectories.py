"""Save illustrative forward trajectories for physical model comparison."""
from pathlib import Path
import numpy as np
from football.physics import PhysicsConfig, simulate

out = Path('results/trajectories'); out.mkdir(parents=True, exist_ok=True)
for model in ['M0', 'M1', 'M3', 'M4', 'M5']:
    # M5 is deliberately given the default constant coefficients in this example.
    flight = simulate((0,0,.11), (30,9,7), spin=(0,0,35), config=PhysicsConfig.for_model(model), max_step=.005)
    np.savetxt(out/f'{model}.csv', np.column_stack((flight.t,flight.position,flight.velocity,flight.acceleration)),
               delimiter=',', header='t_s,x_m,y_m,z_m,vx_m_s,vy_m_s,vz_m_s,ax_m_s2,ay_m_s2,az_m_s2', comments='')
