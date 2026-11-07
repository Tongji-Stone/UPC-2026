import unittest
import numpy as np
from football.physics import PhysicsConfig, simulate, forces, reynolds_table, reynolds_spin_table, linthorne_patel_coefficients


class PhysicsTests(unittest.TestCase):
    def test_uniform_and_plane(self):
        r = simulate((0, 0, 1), (10, 2, 1), config=PhysicsConfig.for_model('M0'), plane_x=5)
        self.assertEqual(r.event['type'], 'plane')
        self.assertAlmostEqual(r.event['time'], .5, places=8)
        np.testing.assert_allclose(r.event['position'], [5, 1, 1.5], atol=1e-8)

    def test_gravity_and_start_on_ground(self):
        r = simulate((0, 0, .11), (2, 0, 4), config=PhysicsConfig.for_model('M1'), plane_x=100)
        self.assertEqual(r.event['type'], 'ground')
        self.assertAlmostEqual(r.event['time'], 8/9.81, places=7)
        self.assertAlmostEqual(r.event['position'][0], 16/9.81, places=7)
        np.testing.assert_allclose(r.acceleration, np.tile([0, 0, -9.81], (len(r.t), 1)))

    def test_no_event(self):
        r = simulate((0, 0, 1), (1, 0, 0), config=PhysicsConfig.for_model('M0'), t_span=(0, .1))
        self.assertEqual(r.event['type'], 'none')
        self.assertIsNone(r.event['time'])

    def test_drag_loses_energy(self):
        r = simulate((0, 0, 10), (30, 0, 0), config=PhysicsConfig.for_model('M3', use_gravity=False), plane_x=100, t_span=(0, 1))
        energy = np.sum(r.velocity**2, axis=1)
        self.assertTrue(np.all(np.diff(energy) < 0))

    def test_zero_and_parallel_spin(self):
        cfg = PhysicsConfig.for_model('M4')
        for v, w in [([0,0,0], [0,0,0]), ([1,0,0], [1,0,0])]:
            result = forces(v, w, cfg)
            self.assertTrue(all(np.isfinite(f).all() for f in result.values()))
            np.testing.assert_array_equal(result['magnus'], [0,0,0])

    def test_magnus_vanishes_continuously_for_parallel_axis(self):
        cfg = PhysicsConfig.for_model('M4')
        transverse = np.linalg.norm(forces([10,0,0], [0,1,0], cfg)['magnus'])
        oblique = np.linalg.norm(forces([10,0,0], [1,.001,0], cfg)['magnus'])
        self.assertLess(oblique / transverse, .0011)

    def test_coefficient_callback_and_spin_decay(self):
        seen = []
        def coeff(re, sp):
            seen.append((re, sp))
            return .25, .1
        cfg = PhysicsConfig.for_model('M5', coefficients=coeff, spin_decay=1.,use_rotational_drag=False)
        r = simulate((0, 0, 2), (20, 0, 3), (0, 0, 10), cfg, t_span=(0,.4), plane_x=100)
        self.assertTrue(seen and all(x > 0 and y > 0 for x, y in seen))
        self.assertAlmostEqual(r.spin[-1, 2], 10*np.exp(-.4), places=6)

    def test_tables_interpolate_and_reject_outside(self):
        one = reynolds_table([1, 3], [.2, .4], [0, .2])
        np.testing.assert_allclose(one(2, 0), [.3, .1])
        with self.assertRaises(ValueError):
            one(4, 0)
        two = reynolds_spin_table([1, 3], [0, 2], [[0, 2], [2, 4]], [[0, 0], [2, 2]])
        np.testing.assert_allclose(two(2, 1), [2, 1])
        with self.assertRaises(ValueError):
            two(2, 3)

    def test_published_coefficients_and_units(self):
        radius, nu, speed = .11, 1.5e-5, 30.
        re = 2 * radius * speed / nu
        model = linthorne_patel_coefficients(radius=radius, kinematic_viscosity=nu)
        np.testing.assert_allclose(model(re, 0), [.18, 0])
        omega = 2 * np.pi * 4  # 4 revolutions per second
        cd, cl = model(re, radius * omega / speed)
        self.assertAlmostEqual(cd, .18 + .014 * 4)
        self.assertAlmostEqual(cl, .25 * (1 - np.exp(-2)))


if __name__ == '__main__':
    unittest.main()
