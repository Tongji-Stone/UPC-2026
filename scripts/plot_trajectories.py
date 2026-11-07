"""Draw previously calculated physical model trajectories."""
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # register projection

root = Path('results/trajectories')
fig = plt.figure(figsize=(13, 8), constrained_layout=True)
ax3 = fig.add_subplot(221, projection='3d'); top = fig.add_subplot(222); side = fig.add_subplot(223)
colors = ['#68635b','#c4764a','#a4492c','#647d61','#a5906c']
for model, color in zip(['M0','M1','M3','M4','M5'], colors):
    p = np.loadtxt(root/f'{model}.csv', delimiter=',', skiprows=1)
    ax3.plot(p[:,1],p[:,2],p[:,3],label=model,color=color)
    top.plot(p[:,1],p[:,2],label=model,color=color)
    side.plot(p[:,1],p[:,3],label=model,color=color)
ax3.set(xlabel='x (m)',ylabel='y (m)',zlabel='z (m)',title='3D trajectory')
top.set(xlabel='x (m)',ylabel='y (m)',title='Top view'); side.set(xlabel='x (m)',ylabel='z (m)',title='Side view')
top.legend(); top.grid(alpha=.2); side.grid(alpha=.2)
fig.suptitle('Forward comparison: v=(30,9,7) m/s, spin=(0,0,35) rad/s; M5 uses constant coefficients')
fig.savefig(root/'model_trajectories.png',dpi=200); fig.savefig(root/'model_trajectories.svg')
