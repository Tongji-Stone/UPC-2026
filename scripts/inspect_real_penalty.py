"""提取 J03WOH 点球附近的球轨迹并标出实际球门平面穿越。"""
import csv
import datetime as dt
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results' / 'b_real_penalty'
EVENT_ID = '18232100000995'
FIRST, LAST = 128954, 128965


def main():
    event = next(e for e in ET.parse(ROOT / 'data/raw/J03WOH_events.xml').getroot().iter('Event')
                 if e.get('EventId') == EVENT_ID)
    if event.find('.//Penalty/ShotAtGoal/SuccessfulShot') is None:
        raise RuntimeError('event is no longer a successful penalty')
    with (ROOT / 'data/processed/J03WOH_ball.csv').open(encoding='utf-8', newline='') as f:
        frames = [row for row in csv.DictReader(f) if FIRST <= int(row['frame']) <= LAST]
    if [int(r['frame']) for r in frames] != list(range(FIRST, LAST + 1)):
        raise ValueError('missing or unordered frames')
    t0 = dt.datetime.fromisoformat(frames[0]['timestamp'])
    for row in frames:
        row['elapsed_s'] = (dt.datetime.fromisoformat(row['timestamp']) - t0).total_seconds()
    goal_x = 52.5  # centered coordinates, half of 105 m pitch length
    pair = next((a, b) for a, b in zip(frames, frames[1:])
                if float(a['x_m']) < goal_x <= float(b['x_m']))
    a, b = pair
    alpha = (goal_x-float(a['x_m'])) / (float(b['x_m'])-float(a['x_m']))
    def lerp(key):
        return float(a[key]) + alpha*(float(b[key])-float(a[key]))
    result = {'match': 'J03WOH', 'event_id': EVENT_ID, 'event_timestamp': event.get('EventTime'),
              'event_description': 'Penalty / ShotAtGoal / SuccessfulShot',
              'pitch_m': [105., 68.], 'coordinate_origin': 'pitch center',
              'goal_plane_x_m': goal_x, 'goal_y_limits_m': [-3.66, 3.66],
              'first_frame': FIRST, 'last_frame': LAST,
              'crossing_bracketing_frames': [int(a['frame']), int(b['frame'])],
              'linear_interpolation_fraction': alpha, 'crossing_elapsed_s': lerp('elapsed_s'),
              'crossing_y_m': lerp('y_m'), 'crossing_z_raw': lerp('z_raw'),
              'height_unit': 'not established by paper; working assumption metres',
              'selection_note': 'earliest visible segment after long repeated position near penalty event; first step appears slower',
              'event_alignment_note': 'event time is 0.88 s before first selected frame, not a kick timestamp',
              'source': 'https://huggingface.co/datasets/pysport/idsse-data; CC BY 4.0'}
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'trajectory.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=frames[0].keys()); writer.writeheader(); writer.writerows(frames)
    (OUT / 'event_and_crossing.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
