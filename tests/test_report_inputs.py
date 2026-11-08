"""Regression checks for the corrected real-penalty start frames."""
import hashlib
import unittest
import numpy as np
from football.reporting import DATA,read_json,read_csv,goal_crossing


class CorrectedInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=read_json(DATA/'inputs.json')

    def test_exact_selected_points(self):
        expected={
            'J03WMX':[[3.04,.55,.13],[4.19,.82,.15],[5.25,1.07,.18]],
            'J03WOH':[[.77,.08,.24],[1.99,.34,.46],[3.18,.62,.65]],
            'J03WR9':[[1.47,.49,.23],[2.57,.85,.34],[3.64,1.20,.41]]}
        for c in self.data['cases']:
            np.testing.assert_allclose(c['fit_positions_m'],expected[c['case']],atol=1e-12)
            np.testing.assert_allclose(c['fit_times_s'],[0,.04,.08],atol=1e-12)
            selected=[q['frame'] for q in c['samples'] if q['selected_for_current_fit']]
            self.assertEqual(selected,c['fit_frames'])

    def test_raw_frames_and_hashes_unchanged(self):
        self.assertEqual(len(read_csv(DATA/'完整位置采样.csv')),39)
        for name,h in self.data['config']['original_file_sha256'].items():
            self.assertEqual(hashlib.sha256((DATA/name).read_bytes()).hexdigest(),h)
        wr=next(c for c in self.data['cases'] if c['case']=='J03WR9')
        self.assertTrue(wr['samples'][1]['repeated'])
        self.assertEqual(wr['samples'][0]['time_s'],-.04)
        self.assertEqual(wr['samples'][1]['time_s'],0)

    def test_time_origin_and_crossing_roundtrip(self):
        for c in self.data['cases']:
            origin=.08 if c['case']=='J03WMX' else .04
            self.assertAlmostEqual(c['time_origin_source_s'],origin)
            for q in c['samples']:self.assertAlmostEqual(q['time_s']+origin,q['source_time_s'])
            crossing=goal_crossing(c['samples'])
            np.testing.assert_allclose(crossing['position'],c['goal']['position'],atol=1e-12)
            self.assertAlmostEqual(crossing['time_s'],c['goal']['time_s'])
            self.assertAlmostEqual(c['goal']['time_s']+origin,float(c['source_summary']['球门穿越相对时间_s']))


if __name__=='__main__':unittest.main()
