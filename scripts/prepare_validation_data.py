"""Create a fixed DFL sample list, quality report and complete selection audit."""
import argparse
from collections import Counter
import csv
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from football.data.dfl import SelectionConfig, inspect_rows, iter_ball_frames, select_samples


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8', newline='\n')


def write_csv(path, rows):
    if not rows:
        raise ValueError(f'no records for {path}')
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0], lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('xml', type=Path)
    parser.add_argument('--z-scale', required=True, type=float, help='Explicit multiplier from source Z to metres')
    parser.add_argument('--match-id', default='J03WOH')
    parser.add_argument('--count', type=int, default=30)
    parser.add_argument('--out', type=Path, default=Path('data/processed/data_validation'))
    args = parser.parse_args()
    config = SelectionConfig(count=args.count)
    rows = list(iter_ball_frames(args.xml))
    quality = inspect_rows(rows, args.z_scale)
    samples, manifest, audit = select_samples(rows, match_id=args.match_id, z_scale=args.z_scale, config=config)
    if not samples:
        raise SystemExit('No samples satisfy the fixed rules; inspect the source instead of tuning to errors')
    args.out.mkdir(parents=True, exist_ok=True)
    selected_rows = []
    for sample, entry in zip(samples, manifest):
        for offset, (t, point) in enumerate(zip(sample['times'], sample['positions'])):
            raw = rows[entry['source_row_index']+offset]
            selected_rows.append({'sample_id': sample['sample_id'], 'source_frame': raw['frame'],
                                  'source_timestamp': raw['timestamp'], 't_s': t,
                                  'x_m': point[0], 'y_m': point[1], 'z_m': point[2]})
    write_csv(args.out / 'selected_tracks.csv', selected_rows)
    write_csv(args.out / 'selection_audit.csv', audit)
    digest = hashlib.sha256()
    with args.xml.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    metadata = {'source_filename': args.xml.name, 'source_sha256': digest.hexdigest(),
                'selected_tracks_sha256': hashlib.sha256((args.out/'selected_tracks.csv').read_bytes()).hexdigest(),
                'source_bytes': args.xml.stat().st_size, 'source': 'Deutsche Fußball Liga (DFL)',
                'paper': 'https://doi.org/10.1038/s41597-025-04505-y',
                'dataset': 'https://doi.org/10.6084/m9.figshare.28196177', 'license': 'CC-BY-4.0',
                'z_unit_status': 'assumed metres; consistent with kloppy Sportec parser; source paper gives no explicit Z unit',
                'z_scale_to_m': args.z_scale, 'position_reference': 'source ball height treated as ball centre',
                'selection_config': asdict(config), 'selected_n': len(samples),
                'stop_rule': 'first count eligible samples in source order; no model errors used',
                'audit_reason_counts': dict(Counter(r['reason'] for r in audit)),
                'unexamined_start_rows': max(0, len(rows)-config.frames+1-len(audit)),
                'quality': quality, 'samples': manifest}
    acquisition = args.xml.parent/'download_manifest.json'
    if acquisition.exists():
        metadata['acquisition'] = json.loads(acquisition.read_text(encoding='utf-8'))
    write_json(args.out / 'manifest.json', metadata)
    print(json.dumps({k: v for k, v in metadata.items() if k not in ('samples', 'acquisition')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
