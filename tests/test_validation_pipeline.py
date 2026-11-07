from datetime import datetime, timedelta

import numpy as np
import pytest

from football.data.dfl import SelectionConfig, candidate, inspect_rows, iter_ball_frames, select_samples
from football.data.validation import align_forward, early_observations, validate_track
from football.data.ball3d import load_ball3d_tracks
from football.evaluation.benchmark import Prediction, PredictionRequest, run_benchmark, summarize_benchmark
from football.evaluation.metrics import brier_score, coverage, ellipse_contains, energy_score
from football.evaluation.predictors import gravity_ensemble, physical_predictor


def source_rows(n=160):
    start = datetime(2022, 8, 27, 12)
    return [{'section': 'firstHalf', 'frame': str(i+100),
             'timestamp': (start+timedelta(seconds=i*.04)).isoformat(),
             'x_m': str(30*i*.04), 'y_m': str(2*i*.04),
             'z_raw': str(2+.2*i*.04), 'status': '1'} for i in range(n)]


def case(sample_id='one', truth=True):
    t = np.arange(21)/25
    p = np.column_stack((30*t, 2*t, 2+3*t-4.905*t*t))
    hit = np.array([2*11/30, 2+3*11/30-4.905*(11/30)**2]) if truth else None
    return {'sample_id': sample_id, 'times': t, 'positions': p, 'truth_yz_m': hit}


def test_prefix_position_quality_cannot_use_future():
    sample = case()
    baseline = early_observations(sample['times'], sample['positions'], .05)
    sample['positions'][2:] = np.nan
    actual = early_observations(sample['times'], sample['positions'], .05)
    for a, b in zip(baseline, actual):
        np.testing.assert_array_equal(a, b)
    with pytest.raises(ValueError, match='non-finite'):
        early_observations(sample['times'], sample['positions'], .10)


@pytest.mark.parametrize('duration', [-1, np.nan, np.inf, 0])
def test_invalid_or_too_short_window(duration):
    sample = case()
    with pytest.raises(ValueError):
        early_observations(sample['times'], sample['positions'], duration)


def test_cutoff_is_strict_and_raw_time_is_preserved():
    times = np.array([10., 10.04, 10.05000000001, 10.08])
    positions = np.column_stack((times-times[0], times*0, times*0+1))
    observed, _ = early_observations(times, positions, .05)
    np.testing.assert_array_equal(observed, times[:2])


@pytest.mark.parametrize('positions,direction', [([[0, 0, np.nan]], [1, 0]),
                                                ([[0, 0, 1]], [np.nan, 1]), ([], [1, 0])])
def test_invalid_alignment(positions, direction):
    with pytest.raises(ValueError):
        align_forward(positions, direction)


def test_invalid_speed_limit():
    with pytest.raises(ValueError):
        validate_track([0, 1], [[0, 0, 1], [1, 0, 1]], max_speed=np.nan)


def test_namespaced_ball_only_stream_retains_exact_source_fields(tmp_path):
    path = tmp_path/'track.xml'
    path.write_text('<Root xmlns="urn:test"><FrameSet TeamId="HOME"><Frame N="0"/></FrameSet>'
                    '<FrameSet TeamId="BALL" GameSection="firstHalf">'
                    '<Frame N="17" T="2022-08-27T12:00:00" X="1" Y="2" Z="3" BallStatus="1"/>'
                    '</FrameSet><FrameSet TeamId="BALL" GameSection="secondHalf">'
                    '<Frame N="18" T="2022-08-27T13:00:00" X="4" Y="5" Z="6" BallStatus="0"/>'
                    '</FrameSet></Root>', encoding='utf-8')
    rows = list(iter_ball_frames(path))
    assert len(rows) == 2
    assert rows[0]['frame'] == '17' and rows[0]['z_raw'] == '3'
    assert rows[1]['section'] == 'secondHalf' and rows[1]['status'] == '0'


def test_quality_counts_duplicates_missing_and_gaps_without_repair():
    rows = source_rows(5)
    rows[1] = rows[0].copy()
    rows[3]['z_raw'] = ''
    quality = inspect_rows(rows, 1.)
    assert quality['counts']['rows'] == 5
    assert quality['counts']['duplicate_frame_keys'] == 1
    assert quality['counts']['duplicate_timestamp_keys'] == 1
    assert quality['counts']['missing_or_invalid_rows'] == 1
    assert quality['counts']['nonpositive_time_steps'] == 1


def test_selection_is_fixed_spaced_and_auditable():
    rows = source_rows()
    config = SelectionConfig(count=3)
    a, manifest_a, audit_a = select_samples(rows, match_id='test', z_scale=1, config=config)
    b, manifest_b, audit_b = select_samples(rows, match_id='test', z_scale=1, config=config)
    assert manifest_a == manifest_b and audit_a == audit_b
    assert [s['sample_id'] for s in a] == ['test:firstHalf:100', 'test:firstHalf:150', 'test:firstHalf:200']
    assert all(m['plane_kind'] == 'virtual' for m in manifest_a)
    assert [r['row_index'] for r in audit_a] == list(range(len(audit_a)))
    for first, second in zip(a, b):
        np.testing.assert_array_equal(first['positions'], second['positions'])
    assert sum(r['reason'] == 'selected' for r in audit_a) == 3


@pytest.mark.parametrize('fault,reason', [('inactive', 'section_or_inactive'),
                                        ('gap', 'missing_or_irregular'),
                                        ('duplicate', 'missing_or_irregular'),
                                        ('height', 'height'), ('velocity_jump', 'abrupt_velocity_change')])
def test_candidate_exclusion_reasons(fault, reason):
    rows = source_rows(21)
    if fault == 'inactive': rows[10]['status'] = '0'
    if fault == 'gap': rows[10]['timestamp'] = '2022-08-27T12:00:00.410000'
    if fault == 'duplicate': rows[10]['frame'] = rows[9]['frame']
    if fault == 'height': rows[10]['z_raw'] = '0.1'
    if fault == 'velocity_jump': rows[10]['x_m'] = str(float(rows[10]['x_m'])+.2)
    assert candidate(rows, SelectionConfig(), 1.)[0] == reason


def test_selection_requires_explicit_valid_z_scale():
    with pytest.raises(ValueError):
        select_samples(source_rows(), match_id='test', z_scale=0)


def test_weighted_energy_score_and_proper_event_score():
    assert energy_score([[0, 0], [2, 0]], [0, 0], [.25, .75]) == pytest.approx(1.125)
    assert energy_score([[2, 0]], [0, 0], [1]) == pytest.approx(2)
    assert brier_score([1., .25], [True, False]) == {'n': 2, 'mean': .03125}
    with pytest.raises(ValueError): energy_score([[0, 0]], [0, 0], [-1])
    with pytest.raises(ValueError): coverage([True, np.nan])
    with pytest.raises(ValueError): coverage(['false', 'true'])
    with pytest.raises(ValueError): brier_score([np.nan], [True])


def test_ellipse_regions_are_nested_and_singular_regions_explicit():
    cloud = np.random.default_rng(7).normal(size=(256, 2))
    assert ellipse_contains(cloud, [0, 0], .68)
    assert ellipse_contains(cloud, [0, 0], .95)
    assert not ellipse_contains(cloud, [100, 100], .95)
    with pytest.raises(ValueError, match='singular'):
        ellipse_contains(np.ones((10, 2)), [1, 1], .95)


def test_predictor_receives_prefix_only_and_cannot_mutate_other_models():
    sample = case()
    observed = []
    def spy(request, rng):
        observed.append(request.times_s.copy())
        assert not request.positions_m.flags.writeable
        assert request.times_s[-1] <= request.cutoff_s
        return Prediction('plane', np.array([1., 2.]), 1.)
    sample['positions'][3:] = np.nan
    records = run_benchmark([sample], {'spy': spy})
    assert len(records) == 2
    np.testing.assert_array_equal(observed[0], [0., .04])
    np.testing.assert_array_equal(observed[1], [0., .04, .08])


def test_denominators_include_non_crossing_failed_and_unavailable_predictions():
    samples = [case('crossed'), case('not_crossed', truth=False)]
    models = {'ok': lambda q, rng: Prediction('plane', np.array([0., 1.]), .8),
              'ground': lambda q, rng: Prediction('ground', crossing_probability=.1),
              'unavailable': lambda q, rng: Prediction('insufficient_observations')}
    records = run_benchmark(samples, models, durations=(.05,))
    summary = summarize_benchmark(records)
    assert summary['groups']['0.05_ok']['cases'] == 2
    assert summary['groups']['0.05_ok']['paired_crossing_n'] == 1
    assert summary['groups']['0.05_ok']['crossing_brier']['n'] == 2
    assert summary['groups']['0.05_ground']['errors'] is None
    assert summary['groups']['0.05_ground']['prediction_crossing_n'] == 0
    assert summary['common_cases']['0.05']['n'] == 0
    assert 'unavailable' not in summary['common_cases']['0.05']['models']


def test_bad_predictor_is_recorded_as_failure():
    records = run_benchmark([case()], {'bad': lambda q, rng: Prediction('plane', [np.nan, 2])})
    assert all(r['status'] == 'error' and r['error_type'] == 'ValueError' for r in records)
    assert summarize_benchmark(records)['groups']['0.05_bad']['cases'] == 1


def test_no_common_cases_when_all_models_are_unavailable():
    records = run_benchmark([case()], {'M2': physical_predictor('M2')}, durations=(.05,))
    assert summarize_benchmark(records)['common_cases']['0.05']['n'] == 0


def test_ensemble_seed_is_independent_of_model_order():
    ensemble = gravity_ensemble(samples=32)
    a = run_benchmark([case()], {'ensemble': ensemble})
    b = run_benchmark([case()], {'extra': physical_predictor('M1'), 'ensemble': ensemble})
    b = [r for r in b if r['model'] == 'ensemble']
    for x, y in zip(a, b):
        for key in ('prediction_yz_m', 'crossing_probability', 'energy_score_m', 'coverage_95'):
            assert x[key] == y[key]


@pytest.mark.parametrize('model', ['M0', 'M1', 'M2', 'M3', 'M4', 'M5'])
def test_model_adapters_use_shared_contract(model):
    records = run_benchmark([case()], {model: physical_predictor(model)})
    assert not any(r['status'] == 'error' for r in records)
    if model == 'M2':
        assert records[0]['status'] == 'insufficient_observations'
    if model == 'M1':
        assert records[0]['error_m'] < 1e-6 and records[1]['error_m'] < 1e-6


def test_ensemble_validates_noise_configuration():
    with pytest.raises(ValueError): gravity_ensemble(sigma_m=0)
    with pytest.raises(ValueError): gravity_ensemble(samples=2)


def test_ball3d_import_uses_actual_clip_fps_and_keeps_missing_frame_gap(tmp_path):
    csv_path, metadata_path = tmp_path/'gt.csv', tmp_path/'sequence_metadata.json'
    csv_path.write_text('file_name,track_id,x,y,z\n30,7,100,0,20\n32,7,110,1,22\n', encoding='utf-8')
    metadata_path.write_text('{"fps":"30000/1001"}', encoding='utf-8')
    track = load_ball3d_tracks(csv_path, metadata_path)[0]
    np.testing.assert_allclose(track['times'], np.array([30,32])*1001/30000)
    np.testing.assert_allclose(track['positions'], [[10,0,2],[11,.1,2.2]])
    assert track['track_id'] == '7'
    metadata_path.write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='fps'):
        load_ball3d_tracks(csv_path, metadata_path)


def test_ball3d_duplicate_native_frames_are_rejected(tmp_path):
    csv_path, metadata_path = tmp_path/'gt.csv', tmp_path/'sequence_metadata.json'
    csv_path.write_text('file_name,track_id,x,y,z\n0,7,0,0,20\n0,7,1,0,22\n', encoding='utf-8')
    metadata_path.write_text('{"fps":25}', encoding='utf-8')
    with pytest.raises(ValueError, match='duplicates'):
        load_ball3d_tracks(csv_path, metadata_path)
