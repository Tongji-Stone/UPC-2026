"""Import the documented ball3d GT CSV and clip-specific frame rate."""
import csv
from fractions import Fraction
import json

import numpy as np

from .validation import ball3d_track


def load_ball3d_tracks(csv_path, metadata_path):
    """Keep native frame/fps timestamps; convert decimetres to metres.

    Tracks remain in their first-appearance order. Missing frames are retained
    as gaps; observations are never interpolated. Duplicate times are errors.
    """
    with open(metadata_path, encoding='utf-8') as stream:
        metadata = json.load(stream)
    try:
        fps = float(Fraction(str(metadata['fps'])))
    except (KeyError, ValueError, ZeroDivisionError) as exc:
        raise ValueError('sequence_metadata.json must contain actual positive fps') from exc
    groups = {}
    with open(csv_path, encoding='utf-8', newline='') as stream:
        reader = csv.DictReader(stream)
        if not {'file_name', 'track_id', 'x', 'y', 'z'}.issubset(reader.fieldnames or []):
            raise ValueError('missing ball3d GT fields')
        for row in reader:
            if not row['track_id']:
                raise ValueError('missing track_id')
            groups.setdefault(row['track_id'], []).append(row)
    if not groups:
        raise ValueError('empty ground-truth file')
    tracks = []
    for track_id, rows in groups.items():
        frames = np.array([float(row['file_name']) for row in rows])
        if not np.isfinite(frames).all() or np.any(frames < 0) or np.any(frames != np.floor(frames)):
            raise ValueError('file_name must contain nonnegative integer frame indices')
        xyz_dm = np.array([[float(row[k]) for k in ('x', 'y', 'z')] for row in rows])
        times, positions = ball3d_track(frames, xyz_dm, fps)
        tracks.append({'track_id': track_id, 'source_frames': frames.astype(int),
                       'times': times, 'positions': positions, 'fps': fps,
                       'source_units': 'dm', 'units': 'm,s'})
    return tracks
