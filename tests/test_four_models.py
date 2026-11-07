import unittest
from dataclasses import replace
import numpy as np
from football.physics import PhysicsConfig,simulate,forces,state_derivative,rotational_torque
from football.inference.four_model_fit import fit_early
from football.inference.coupled_fit import observed_trajectory

class FourModelTests(unittest.TestCase):
    def test_hierarchy_and_scales(self):
        for m,drag,lift in [('M1',False,False),('M2',True,False),('M3',True,True),('M4',True,True)]:
            cfg=PhysicsConfig.for_model(m)
            self.assertEqual((cfg.use_drag,cfg.use_magnus,cfg.use_rotational_drag),(drag,lift,False))
        cfg=PhysicsConfig.for_model('M4');a=forces([30,2,4],[0,30,10],cfg)
        b=forces([30,2,4],[0,30,10],replace(cfg,drag_scale=2,lift_scale=3))
        np.testing.assert_allclose(b['drag'],2*a['drag']);np.testing.assert_allclose(b['magnus'],3*a['magnus'])

    def test_main_model_spin_and_work(self):
        for model in ['M1','M2','M3','M4']:
            cfg=PhysicsConfig.for_model(model)
            f=simulate([0,0,1],[30,2,3],[4,20,30],cfg,t_span=(0,.3),plane_x=100)
            np.testing.assert_allclose(f.spin,np.tile([4,20,30],(len(f.t),1)),atol=1e-12)
            self.assertLessEqual(np.max(np.sum(f.forces['drag']*f.velocity,axis=1)),1e-10)
            np.testing.assert_allclose(np.sum(f.forces['magnus']*f.velocity,axis=1),0,atol=1e-10)

    def test_rotational_analytic(self):
        for viscous in [False,True]:
            c=PhysicsConfig.for_model('M4',use_rotational_drag=True,use_viscous_torque=viscous)
            w0=100.;t=.2
            k2=8*np.pi*c.air_density*c.angular_drag_coefficient*c.radius**5/(15*c.moment_of_inertia)
            k1=8*np.pi*c.dynamic_viscosity*c.radius**3/c.moment_of_inertia if viscous else 0
            expected=w0/(1+k2*w0*t) if not k1 else w0*np.exp(-k1*t)/(1+k2*w0/k1*(-np.expm1(-k1*t)))
            r=simulate([0,0,5],[10,0,0],[0,0,w0],c,t_span=(0,t),plane_x=100,rtol=1e-11,atol=1e-13)
            self.assertAlmostEqual(np.linalg.norm(r.spin[-1]),expected,places=7)
            self.assertLess(rotational_torque([0,0,w0],c)@[0,0,w0],0)

    def test_synthetic_gravity_inverse(self):
        c=PhysicsConfig.for_model('M1');t=np.array([0,.04,.08]);s=[30,2,5,0,0,0]
        p=observed_trajectory(t,[0,0,1],s,c)[:,:3]
        r=fit_early(t,p,c,'M1')
        np.testing.assert_allclose(r['initial_state'][:3],s[:3],atol=1e-10)
        self.assertEqual(r['active_parameters'],3)

    def test_constant_lift_axis_invariance(self):
        c=PhysicsConfig.for_model('M3')
        a=state_derivative(0,np.r_[[0,0,1],[30,2,5],[0,1,0]],c)
        b=state_derivative(0,np.r_[[0,0,1],[30,2,5],[0,200,0]],c)
        np.testing.assert_allclose(a,b,atol=1e-12)

    def test_synthetic_variable_model_regularized_fit(self):
        c=PhysicsConfig.for_model('M4');t=np.array([0,.05,.1])
        p=observed_trajectory(t,[0,0,.5],[30,2,5,0,0,30],c)[:,:3]
        r=fit_early(t,p,c,'M4',max_nfev=80)
        self.assertLess(r['rss_m2'],6e-12)
        self.assertEqual(r['active_parameters'],8)
        self.assertEqual(len(r['starts']),19)
        self.assertLess(r['coefficient_distance'],1.1e-8)
        predicted=observed_trajectory(t,p[0],r['initial_state'],
            replace(c,drag_scale=r['drag_scale'],lift_scale=r['lift_scale']))[:,:3]
        np.testing.assert_allclose(predicted,p,atol=3e-6)

    def test_zero_speed_spin_and_invalid_scales(self):
        for m in ['M1','M2','M3','M4']:
            c=PhysicsConfig.for_model(m)
            for v,w in [([0,0,0],[0,0,0]),([30,0,0],[0,0,0]),([30,0,0],[20,0,0])]:
                f=forces(v,w,c);np.testing.assert_allclose(f['magnus'],0)
                self.assertTrue(np.isfinite(np.r_[list(f.values())]).all())
        with self.assertRaises(ValueError):simulate([0,0,1],[30,0,0],config=replace(c,drag_scale=-1))

    def test_iteration_limit_is_a_fit_failure(self):
        c=PhysicsConfig.for_model('M3')
        r=fit_early([0,.04,.08],[[0,0,1],[1,.2,1.4],[2.2,.6,1.8]],c,'M3',max_nfev=1)
        self.assertFalse(r['success'])
        self.assertEqual(len(r['stages']),1)

if __name__=='__main__':unittest.main()
