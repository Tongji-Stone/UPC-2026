"""Draw a simple geometry diagram for the paper."""
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Circle, Rectangle

plt.rcParams.update({'font.family':'Times New Roman','font.weight':'bold',
                     'axes.titleweight':'bold','mathtext.fontset':'custom',
                     'mathtext.rm':'Times New Roman',
                     'mathtext.it':'Times New Roman:italic',
                     'mathtext.bf':'Times New Roman:bold', 'mathtext.default':'bf'})

out=Path('results/paper_geometry');out.mkdir(parents=True,exist_ok=True)
fig, (top,front)=plt.subplots(1,2,figsize=(9,3.5),gridspec_kw={'width_ratios':[1.45,1]},constrained_layout=True)

# Horizontal projection: coordinates are metres; the small circle marks the ball.
top.plot([11,11],[-3.66,3.66],color='black',lw=1.8)
top.add_patch(Circle((0,0),.11,edgecolor='black',facecolor='white',lw=1.1,zorder=3))
top.plot([0,11],[0,2.65],color='0.38',lw=1.1,ls='--')
top.annotate('',xy=(11,-4.55),xytext=(0,-4.55),arrowprops={'arrowstyle':'<->','lw':.9,'color':'black'})
top.plot([0,0],[-4.3,-4.75],color='black',lw=.6);top.plot([11,11],[-4.3,-4.75],color='black',lw=.6)
top.text(5.5,-4.35,'11 m',ha='center',va='bottom',fontsize=10)
top.annotate('',xy=(4.0,0),xytext=(0,0),arrowprops={'arrowstyle':'->','lw':.9})
top.annotate('',xy=(0,1.7),xytext=(0,0),arrowprops={'arrowstyle':'->','lw':.9})
top.text(4.08,-.15,'$x$',fontsize=11);top.text(-.3,1.75,'$y$',fontsize=11)
top.text(-.05,-.55,'Penalty mark',ha='center',va='top',fontsize=9)
top.text(11.2,.1,'Goal plane\n$x=11$ m',ha='left',va='center',fontsize=9)
top.set(xlim=(-1.5,14),ylim=(-5.2,4.6),aspect='equal',title='Top view');top.axis('off')

# Front view of the goal, with axes through the centre of the goal line.
for x in [i*3.66/8 for i in range(-7,8)]:
    front.plot([x,x],[0,2.44],color='0.78',lw=.55,zorder=0)
for z in [i*2.44/5 for i in range(1,5)]:
    front.plot([-3.66,3.66],[z,z],color='0.78',lw=.55,zorder=0)
front.add_patch(Rectangle((-3.66,0),7.32,2.44,fill=False,edgecolor='black',lw=1.8))
front.plot([-4.3,4.3],[0,0],color='black',lw=.8)
front.plot([2.65],[1.3],marker='o',markersize=3,color='black')
front.text(2.65,1.48,'$P$',ha='center',fontsize=10)
front.annotate('',xy=(3.66,-.65),xytext=(-3.66,-.65),arrowprops={'arrowstyle':'<->','lw':.9})
front.plot([-3.66,-3.66],[-.45,-.8],color='black',lw=.6);front.plot([3.66,3.66],[-.45,-.8],color='black',lw=.6)
front.text(0,-.48,'7.32 m',ha='center',va='bottom',fontsize=10)
front.annotate('',xy=(4.35,2.44),xytext=(4.35,0),arrowprops={'arrowstyle':'<->','lw':.9})
front.text(4.55,1.22,'2.44 m',rotation=90,ha='left',va='center',fontsize=10)
front.annotate('',xy=(1.35,0),xytext=(0,0),arrowprops={'arrowstyle':'->','lw':.9})
front.annotate('',xy=(0,1.15),xytext=(0,0),arrowprops={'arrowstyle':'->','lw':.9})
front.text(1.4,.1,'$y$',fontsize=11);front.text(.16,1.15,'$z$',fontsize=11)
front.set(xlim=(-4.8,5.6),ylim=(-1.05,3.2),aspect='equal',title='Goal-plane view');front.axis('off')
fig.savefig(out/'geometry.png',dpi=240,bbox_inches='tight',facecolor='white')
fig.savefig(out/'geometry.pdf',bbox_inches='tight',facecolor='white')
