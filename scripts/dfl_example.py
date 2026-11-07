"""Reproducible first eligible DFL flight sample and constant-velocity baseline."""
import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
import numpy as np

from football.data.validation import align_forward, early_observations, crossing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csv')
    ap.add_argument('--out', default='results/dfl_example')
    args = ap.parse_args()
    with open(args.csv, encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    # Scan in recorded order; take first complete 21-frame section satisfying
    # active ball, regular timestamps, plausible speed and airborne height.
    chosen = None
    for start in range(len(rows)-20):
        w = rows[start:start+21]
        try:
            if any(r['section'] != w[0]['section'] or r['status'] != '1' for r in w):
                continue
            t0 = datetime.fromisoformat(w[0]['timestamp'])
            t = np.array([(datetime.fromisoformat(r['timestamp'])-t0).total_seconds() for r in w])
            p = np.array([[float(r[k]) for k in ('x_m','y_m','z_raw')] for r in w])
            if not np.isfinite(p).all() or not np.allclose(np.diff(t), .04, atol=1e-6):
                continue
            if not (np.all(p[:,2] > .3) and np.all(p[:,2] < 15)):
                continue
            speed = np.linalg.norm(np.diff(p,axis=0),axis=1)/.04
            if np.any(speed > 45) or np.any(speed < 2):
                continue
            direction = p[1,:2]-p[0,:2]
            if np.linalg.norm(direction) < .2:
                continue
            q = align_forward(p,direction)
            hit = crossing(t,q,11,.10)
            if hit is None:
                continue
            chosen = w,t,q,hit
            break
        except (ValueError, TypeError):
            continue
    if chosen is None:
        raise SystemExit('No eligible sample found')
    w,t,q,hit = chosen
    predictions = {}
    for duration in (.05,.10):
        observed, points = early_observations(t,q,duration)
        velocity = (points[-1]-points[0])/(observed[-1]-observed[0])
        if velocity[0] <= 0:
            raise ValueError('non-forward velocity')
        arrival = observed[-1]+(11-points[-1,0])/velocity[0]
        pred = points[-1,1:]+velocity[1:]*(arrival-observed[-1])
        predictions[str(duration)] = {'input_times_s': observed.tolist(), 'predicted_yz_m': pred.tolist(),
                                      'error_m': float(np.linalg.norm(pred-hit[1][1:]))}
    out = Path(args.out)
    out.mkdir(parents=True,exist_ok=True)
    with (out/'sample.csv').open('w',encoding='utf-8',newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['frame','timestamp','t_s','x_m','y_m','z_m'])
        for row,tt,pp in zip(w,t,q):
            writer.writerow([row['frame'],row['timestamp'],tt,*pp])
    result = {'source':'DFL J03WOH', 'sample_start_frame': w[0]['frame'], 'section':w[0]['section'],
              'truth_crossing_time_s':hit[0], 'truth_yz_m':hit[1][1:].tolist(),
              'selection':'first 21 contiguous 25 Hz active frames, 0.3 < z < 15 m, 2 < speed < 45 m/s, initial horizontal displacement >= 0.2 m, forward crossing x=11 m after 0.10 s',
              'baseline':'constant velocity from first to last available observation', 'predictions':predictions}
    (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
