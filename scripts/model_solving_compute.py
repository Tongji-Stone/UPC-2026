"""Save the three-point gravity-and-drag prediction for plotting."""
import numpy as np
from pathlib import Path
from football.physics import PhysicsConfig,simulate
from football.inference.physical_fit import fit_velocity
t=np.array([0,.05,.1]);p=np.array([[0,0,.11],[1.5,.45,.44],[2.96,.86,.74]])
config=PhysicsConfig.for_model('M3');v=fit_velocity(t,p,config)['velocity']
f=simulate(p[0],v,config=config,plane_x=11,max_step=.005)
out=Path('results/model_solving');out.mkdir(parents=True,exist_ok=True)
np.savetxt(out/'trajectory.csv',np.column_stack((f.t,f.position)),delimiter=',',header='time_s,x_m,y_m,z_m',comments='')
np.savetxt(out/'observations.csv',np.column_stack((t,p)),delimiter=',',header='time_s,x_m,y_m,z_m',comments='')
