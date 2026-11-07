import sys
from pathlib import Path
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from dfl_early_goal_evaluation import early_inputs, polynomial_goal, physical_goal


def test_future_frames_are_never_inputs_to_prediction():
    t=np.array([0.,.04,.08,.12,.16]);p=np.array([[0.,0.,.11],[1.2,.2,.4],[2.38,.4,.66],[3.5,.6,.9],[4.6,.8,1.1]])
    changed=p.copy();changed[3:]=[100.,-500.,1000.]
    ta,pa=early_inputs(t,p);tb,pb=early_inputs(t,changed)
    assert np.allclose(ta,[0,.04,.08]) and np.array_equal(pa,pb) and np.array_equal(ta,tb)
    for model in ('M1','M5','M5_6_prior'):
        a=physical_goal(model,ta,pa,11);b=physical_goal(model,tb,pb,11)
        assert a[0]==b[0]
        if a[1] is not None:assert np.allclose(a[1],b[1])
    a=polynomial_goal(ta,pa,11);b=polynomial_goal(tb,pb,11)
    assert a[0]==b[0]
    if a[1] is not None:assert np.allclose(a[1],b[1])


def test_m2_requires_three_measured_positions():
    assert polynomial_goal(np.array([0.,.04]),np.array([[0.,0.,.11],[1.,0.,.2]]),11)[0]=='insufficient_observations'
