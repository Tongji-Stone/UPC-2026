import unittest
import numpy as np
from dataclasses import replace
from football.physics import (PhysicsConfig,simulate,forces,rotational_torque,
    state_derivative,kiratidis_leinweber_coefficients,coefficients,validate_config)
from football.inference.coupled_fit import observed_trajectory,fit_initial_state


class CoupledTests(unittest.TestCase):
    def setUp(self):self.cfg=PhysicsConfig.for_model('M5')

    def test_reference_and_limits(self):
        cd,cl=kiratidis_leinweber_coefficients(333793,.19)
        self.assertAlmostEqual(cl,1.15*.19**.83,places=12)
        self.assertEqual(kiratidis_leinweber_coefficients(450000,0)[1],0)
        np.testing.assert_array_equal(rotational_torque([0,0,0],self.cfg),0)
        for v,w in [([0,0,0],[2,1,3]),([30,0,0],[10,0,0])]:
            f=forces(v,w,self.cfg)
            np.testing.assert_array_equal(f['magnus'],0)
            self.assertTrue(np.isfinite(state_derivative(0,np.r_[[0,0,1],v,w],self.cfg)).all())

    def test_torque_normalization(self):
        r=self.cfg.radius;nu=self.cfg.kinematic_viscosity;v=30.;sp=.2
        w=np.array([0.,0.,sp*v/r]);q=rotational_torque(w,self.cfg)
        re=2*r*v/nu;cq=16/15*1.5*sp**2+32*sp/re
        self.assertAlmostEqual(np.linalg.norm(q)/(.5*1.2*v*v*np.pi*r**3),cq,places=12)
        self.assertLess(q@w,0)

    def test_energy_identity(self):
        v=np.array([30.,8.,6.]);w=np.array([3.,-10.,30.])
        f=forces(v,w,self.cfg);q=rotational_torque(w,self.cfg)
        self.assertLess(f['drag']@v,0)
        self.assertAlmostEqual(f['magnus']@v,0,places=10)
        state=np.r_[[0.,0.,2.],v,w];dy=state_derivative(0,state,self.cfg)
        edot=self.cfg.mass*v@dy[3:6]+self.cfg.mass*self.cfg.gravity*v[2]+self.cfg.moment_of_inertia*w@dy[6:9]
        self.assertAlmostEqual(edot,f['drag']@v+q@w,places=9)
        self.assertLess(edot,0)

    def test_analytic_spin_decay(self):
        cfg=self.cfg;r=cfg.radius;inertia=cfg.moment_of_inertia
        a=(8*np.pi/15)*cfg.air_density*cfg.angular_drag_coefficient*r**5/inertia
        b=8*np.pi*cfg.dynamic_viscosity*r**3/inertia
        flight=simulate([0,0,30],[25,3,2],[0,0,50],cfg,plane_x=1000,t_span=(0,.5),rtol=1e-10,atol=1e-12)
        exact=50*np.exp(-b*flight.t)/(1+a*50*(-np.expm1(-b*flight.t))/b)
        np.testing.assert_allclose(flight.spin[:,2],exact,rtol=2e-9)
        np.testing.assert_allclose(flight.spin[:,:2],0,atol=1e-14)

    def test_no_double_damping(self):
        with self.assertRaises(ValueError):validate_config(replace(self.cfg,spin_decay=1.))

    def test_forward_inverse_same_rhs_and_recovery(self):
        state=np.array([30.,7.,6.,5.,-12.,30.]);times=np.array([0.,.05,.1])
        p=observed_trajectory(times,[0,0,.11],state,self.cfg)[:,:3]
        fitted=fit_initial_state(times,p,self.cfg,starts=[state+[.05,-.05,.02,.2,.1,-.1]],max_nfev=150)
        self.assertLess(fitted['best']['max_component_residual_m'],1e-7)
        pred=np.asarray(fitted['best']['initial_state'])
        reference=simulate(p[0],state[:3],state[3:],self.cfg,rtol=1e-10,atol=1e-12)
        recovered=simulate(p[0],pred[:3],pred[3:],self.cfg,rtol=1e-10,atol=1e-12)
        np.testing.assert_allclose(recovered.event['position'],reference.event['position'],atol=1e-4)
        self.assertIsNone(fitted['measurement_noise_model'])

    def test_integrator_convergence(self):
        args=([0,0,.11],[30,8,6],[5,-12,30],self.cfg)
        a=simulate(*args,rtol=1e-8,atol=1e-10)
        b=simulate(*args,rtol=1e-10,atol=1e-12)
        np.testing.assert_allclose(a.event['position'],b.event['position'],atol=2e-5)


if __name__=='__main__':unittest.main()
