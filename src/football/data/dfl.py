"""DFL ball-only extraction and a fixed, auditable flight sample manifest."""
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
import xml.etree.ElementTree as ET

import numpy as np

from .validation import align_forward, crossing, validate_track


@dataclass(frozen=True)
class SelectionConfig:
    frames: int = 21
    count: int = 30
    frame_interval_s: float = .04
    min_height_m: float = .3
    max_height_m: float = 15.
    min_speed_m_s: float = 2.
    max_speed_m_s: float = 45.
    max_acceleration_m_s2: float = 80.
    min_initial_displacement_m: float = .2
    plane_x_m: float = 11.
    last_cutoff_s: float = .1
    separation_s: float = 2.

    def __post_init__(self):
        values = np.array(list(asdict(self).values()), float)
        if (not np.isfinite(values).all() or self.frames < 4 or self.count < 1
                or self.frames != int(self.frames) or self.count != int(self.count)
                or self.frame_interval_s <= 0 or self.min_height_m < 0
                or self.max_height_m <= self.min_height_m or self.min_speed_m_s < 0
                or self.max_speed_m_s <= self.min_speed_m_s or self.max_acceleration_m_s2 <= 0
                or self.min_initial_displacement_m <= 0 or self.plane_x_m <= 0
                or self.last_cutoff_s < self.frame_interval_s or self.separation_s < 0):
            raise ValueError('invalid flight selection configuration')


def iter_ball_frames(path):
    """Keep source order, frame numbers and timestamps; remove parsed nodes."""
    stack = []
    section = None
    for event, element in ET.iterparse(path, events=('start', 'end')):
        tag = element.tag.rsplit('}', 1)[-1]
        if event == 'start':
            stack.append(element)
            if tag == 'FrameSet':
                section = element.attrib.copy()
            continue
        if tag == 'Frame' and section is not None and section.get('TeamId') == 'BALL':
            a = element.attrib
            yield {'section': section.get('GameSection', ''), 'frame': a.get('N', ''),
                   'timestamp': a.get('T', ''), 'x_m': a.get('X', ''), 'y_m': a.get('Y', ''),
                   'z_raw': a.get('Z', ''), 'status': a.get('BallStatus', '')}
        if tag == 'FrameSet':
            section = None
        # Removing each closed element bounds memory even for non-ball players.
        if len(stack) > 1:
            stack[-2].remove(element)
        element.clear()
        stack.pop()


def inspect_rows(rows, z_scale):
    """Report quality without silently sorting, filling or dropping source rows."""
    if not np.isfinite(z_scale) or z_scale <= 0:
        raise ValueError('positive explicit z_scale required')
    seen_frames, seen_times = set(), set()
    counts = Counter({key: 0 for key in (
        'rows', 'duplicate_frame_keys', 'duplicate_timestamp_keys', 'missing_or_invalid_rows',
        'below_ground_rows', 'nonpositive_time_steps', 'non_25hz_steps', 'speed_over_60_m_s')})
    intervals = []
    previous = None
    for row in rows:
        counts['rows'] += 1
        frame_key = (row['section'], row['frame'])
        time_key = (row['section'], row['timestamp'])
        counts['duplicate_frame_keys'] += frame_key in seen_frames
        counts['duplicate_timestamp_keys'] += time_key in seen_times
        seen_frames.add(frame_key)
        seen_times.add(time_key)
        try:
            if int(row['frame']) < 0:
                raise ValueError('invalid source frame')
            stamp = datetime.fromisoformat(row['timestamp'])
            position = np.array([float(row[k]) for k in ('x_m', 'y_m', 'z_raw')])
            position[2] *= z_scale
            if not np.isfinite(position).all():
                raise ValueError('nonfinite position')
            counts['below_ground_rows'] += bool(position[2] < 0)
            if previous is not None and previous[0] == row['section']:
                dt = (stamp-previous[1]).total_seconds()
                intervals.append(dt)
                counts['nonpositive_time_steps'] += dt <= 0
                counts['non_25hz_steps'] += abs(dt-.04) > 1e-6
                if dt > 0:
                    counts['speed_over_60_m_s'] += bool(np.linalg.norm(position-previous[2])/dt > 60)
            previous = row['section'], stamp, position
        except (ValueError, TypeError, OverflowError):
            counts['missing_or_invalid_rows'] += 1
            previous = None
    return {'counts': dict(counts), 'interval_s': {
        'n': len(intervals), 'median': float(np.median(intervals)) if intervals else None,
        'min': min(intervals) if intervals else None, 'max': max(intervals) if intervals else None},
        'z_scale_to_m': z_scale}


def candidate(rows, config, z_scale):
    """Selection may inspect the answer; its full data never go to predictors."""
    if any(r['section'] != rows[0]['section'] or r['status'] != '1' for r in rows):
        return 'section_or_inactive', None
    try:
        stamps = [datetime.fromisoformat(r['timestamp']) for r in rows]
        times = np.array([(stamp-stamps[0]).total_seconds() for stamp in stamps])
        frames = np.array([int(r['frame']) for r in rows])
        positions = np.array([[float(r[k]) for k in ('x_m', 'y_m', 'z_raw')] for r in rows])
        positions[:, 2] *= z_scale
        if (not np.isfinite(positions).all() or not np.all(np.diff(frames) == 1)
                or not np.allclose(np.diff(times), config.frame_interval_s, atol=1e-6, rtol=0)):
            return 'missing_or_irregular', None
        if np.any((positions[:, 2] <= config.min_height_m) | (positions[:, 2] >= config.max_height_m)):
            return 'height', None
        velocity = np.diff(positions, axis=0) / np.diff(times)[:, None]
        speed = np.linalg.norm(velocity, axis=1)
        if np.any((speed < config.min_speed_m_s) | (speed > config.max_speed_m_s)):
            return 'speed', None
        acceleration = np.linalg.norm(np.diff(velocity, axis=0), axis=1) / config.frame_interval_s
        if np.any(acceleration > config.max_acceleration_m_s2):
            return 'abrupt_velocity_change', None
        direction = positions[1, :2]-positions[0, :2]
        if np.linalg.norm(direction) < config.min_initial_displacement_m:
            return 'initial_direction', None
        local = align_forward(positions, direction)
        validate_track(times, local)
        truth = crossing(times, local, config.plane_x_m, config.last_cutoff_s)
        if truth is None:
            return 'no_heldout_crossing', None
        return 'selected', (times, local, truth, direction/np.linalg.norm(direction))
    except (ValueError, TypeError, OverflowError):
        return 'missing_or_irregular', None


def select_samples(rows, *, match_id, z_scale, config=None):
    """Chronological prefix, fixed QC and two-second separation; no model scores."""
    config = config or SelectionConfig()
    inspect_rows([], z_scale)  # Validate the explicit height conversion.
    audit, samples, manifest = [], [], []
    index = 0
    while index + config.frames <= len(rows) and len(samples) < config.count:
        window = rows[index:index+config.frames]
        reason, value = candidate(window, config, z_scale)
        audit.append({'row_index': index, 'section': window[0]['section'],
                      'start_frame': window[0]['frame'], 'reason': reason})
        if value is None:
            index += 1
            continue
        times, positions, truth, direction = value
        sample_id = f"{match_id}:{window[0]['section']}:{window[0]['frame']}"
        samples.append({'sample_id': sample_id, 'times': times, 'positions': positions,
                        'truth_time_s': truth[0], 'truth_yz_m': truth[1][1:]})
        manifest.append({'sample_id': sample_id, 'match_id': match_id,
                         'section': window[0]['section'], 'start_frame': window[0]['frame'],
                         'end_frame': window[-1]['frame'], 'source_row_index': index,
                         'source_timestamp': window[0]['timestamp'], 'plane_kind': 'virtual',
                         'plane_x_m': config.plane_x_m, 'direction_xy': direction.tolist(),
                         'translation_xy_m': [float(window[0]['x_m']), float(window[0]['y_m'])],
                         'truth_time_s': truth[0], 'truth_yz_m': truth[1][1:].tolist(),
                         'z_scale_to_m': z_scale})
        next_index = index + max(config.frames, int(np.ceil(config.separation_s/config.frame_interval_s)))
        for skipped in range(index+1, min(next_index, len(rows)-config.frames+1)):
            # A new section can start its own independent separation period.
            if rows[skipped]['section'] != window[0]['section']:
                next_index = skipped
                break
            audit.append({'row_index': skipped, 'section': rows[skipped]['section'],
                          'start_frame': rows[skipped]['frame'], 'reason': 'separation_skip'})
        index = next_index
    return samples, manifest, audit
