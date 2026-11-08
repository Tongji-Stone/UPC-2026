import unittest
from dataclasses import replace
import numpy as np
from football.physics import PhysicsConfig,simulate,forces,state_derivative,rotational_torque
from football.inference.four_model_fit import fit_early, InverseBounds
from football.inference.coupled_fit import observed_trajectory

class FourModelTests(unittest.TestCase):
    def test_inverse_bounds_on_all_models_and_custom_limits(self):
        t=[0,.05,.1]; p=[[0,0,1],[2.5,1,1.2],[5,2,1.4]]
        limits=InverseBounds(velocity_component_max_m_s=25,spin_component_max_rad_s=20,
                             force_scale_min=.8,force_scale_max=1.2)
        for model in ['M1','M2','M3','M4']:
            r=fit_early(t,p,PhysicsConfig.for_model(model),model,max_nfev=1,bounds=limits)
            velocity=np.asarray(r['initial_state'][:3]);spin=np.asarray(r['initial_state'][3:])
            self.assertTrue(model == 'M3' or 0 <= velocity[0] <= 25)
            self.assertTrue(model == 'M3' or np.all(np.abs(velocity[1:]) <= 25))
            if model=='M4': self.assertTrue(np.all(np.abs(spin) <= 20))
            if model in ('M2','M3','M4'): self.assertTrue(.8 <= r['drag_scale'] <= 1.2)
            if model in ('M3','M4'): self.assertTrue(.8 <= r['lift_scale'] <= 1.2)
            self.assertEqual(r['fit_bounds']['velocity_component_max_m_s'],25)

    def test_invalid_inverse_bounds_rejected(self):
        with self.assertRaises(ValueError): InverseBounds(velocity_component_max_m_s=np.inf)
        with self.assertRaises(ValueError): InverseBounds(force_scale_min=2,force_scale_max=1)

    def test_hierarchy_and_scales(self):
        for m,drag,lift in [('M1',False,False),('M2',True,False),('M3',False,False),('M4',True,True)]:
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

    def test_linear_spin_force_and_constant_acceleration(self):
        cfg = PhysicsConfig.for_model('M4')
        velocity = np.array([30., 2., 4.]); spin = np.array([0., 30., 10.])
        expected = .5 * cfg.air_density * np.pi * cfg.radius**3 * cfg.lift_coefficient * np.cross(spin, velocity)
        np.testing.assert_allclose(forces(velocity, spin, cfg)['magnus'], expected)
        np.testing.assert_allclose(forces(velocity, 2*spin, cfg)['magnus'], 2*expected)
        t=np.array([0., .05, .1]); v=np.array([20.,2.,4.]); a=np.array([-3.,4.,-8.]); p0=np.array([0.,0.,1.])
        p=p0+t[:,None]*v+.5*t[:,None]**2*a
        result=fit_early(t,p,PhysicsConfig.for_model('M3'),'M3')
        np.testing.assert_allclose(result['initial_state'][:3],v,atol=1e-10)
        np.testing.assert_allclose(result['constant_acceleration'],a,atol=1e-10)

    def test_synthetic_constant_model_fit(self):
        c=PhysicsConfig.for_model('M4');t=np.array([0,.05,.1])
        p=observed_trajectory(t,[0,0,.5],[30,2,5,0,0,30],c)[:,:3]
        r=fit_early(t,p,c,'M4',max_nfev=80)
        self.assertLess(r['rss_m2'],6e-12)
        self.assertEqual(r['active_parameters'],7)
        self.assertEqual(len(r['starts']),6)
        self.assertTrue(.5 <= r['drag_scale'] <= 1.5)
        self.assertTrue(.5 <= r['lift_scale'] <= 1.5)
        self.assertAlmostEqual(np.linalg.norm(r['initial_state'][3:]), 30.)
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
        c=PhysicsConfig.for_model('M4')
        r=fit_early([0,.04,.08],[[0,0,1],[1,.2,1.4],[2.2,.6,1.8]],c,'M4',max_nfev=1)
        self.assertFalse(r['success'])
        self.assertEqual(len(r['stages']),1)

if __name__=='__main__':unittest.main()
