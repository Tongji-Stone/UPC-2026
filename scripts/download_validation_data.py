"""Download only the official DFL J03WOH tracking XML; verify before use."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request


def download_ranges(url, target, size, workers):
    """Bounded parallel byte ranges, written directly to one temporary file."""
    chunk_size = 1024 * 1024
    with target.open('wb') as stream:
        stream.truncate(size)
    def transfer(start):
        end = min(start+chunk_size, size)-1
        for attempt in range(3):
            try:
                request = urllib.request.Request(url, headers={'Range': f'bytes={start}-{end}'})
                with urllib.request.urlopen(request, timeout=30) as response:
                    if response.status != 206 or response.headers.get('Content-Range') != f'bytes {start}-{end}/{size}':
                        raise ValueError('server did not honour exact byte range')
                    payload = response.read(end-start+2)
                if len(payload) != end-start+1:
                    raise ValueError('truncated byte range')
                with target.open('r+b') as stream:
                    stream.seek(start)
                    stream.write(payload)
                return len(payload)
            except (OSError, ValueError):
                if attempt == 2:
                    raise
    completed = 0
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for length in executor.map(transfer, range(0, size, chunk_size)):
            completed += length
            if completed % (32*chunk_size) == 0:
                print(f'Fetched {completed}/{size} bytes', flush=True)


def digest(path, algorithm):
    result = hashlib.new(algorithm)
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('data/raw/data_validation'))
    parser.add_argument('--source', choices=('figshare', 'mirror'), default='figshare')
    parser.add_argument('--workers', type=int, default=8, help='Parallel mirror byte ranges (1-16)')
    args = parser.parse_args()
    if not 1 <= args.workers <= 16:
        parser.error('--workers must be between 1 and 16')
    url = 'https://api.figshare.com/v2/articles/28196177'
    with urllib.request.urlopen(url, timeout=60) as response:
        metadata = json.load(response)
    source = next(f for f in metadata['files']
                  if 'positions_raw_observed' in f['name'] and 'J03WOH' in f['name'])
    download_url = source['download_url']
    if args.source == 'mirror':
        with urllib.request.urlopen('https://huggingface.co/api/datasets/pysport/idsse-data', timeout=30) as response:
            revision = json.load(response)['sha']
        download_url = f"https://huggingface.co/datasets/pysport/idsse-data/resolve/{revision}/{source['name']}"
    args.out.mkdir(parents=True, exist_ok=True)
    target = args.out / source['name']
    if not target.exists():
        partial = target.with_suffix('.xml.part')
        try:
            if args.source == 'mirror' and args.workers > 1:
                download_ranges(download_url, partial, source['size'], args.workers)
            else:
                with urllib.request.urlopen(download_url, timeout=30) as response, partial.open('wb') as out:
                    for chunk in iter(lambda: response.read(64 * 1024), b''):
                        out.write(chunk)
            if partial.stat().st_size != source['size'] or digest(partial, 'md5') != source['computed_md5']:
                raise ValueError('official file size or MD5 mismatch')
            partial.replace(target)
        finally:
            partial.unlink(missing_ok=True)
    if target.stat().st_size != source['size'] or digest(target, 'md5') != source['computed_md5']:
        raise ValueError('existing file does not match official metadata')
    manifest = {
        'retrieved_utc': datetime.now(timezone.utc).isoformat(),
        'metadata_url': url, 'doi': metadata['doi'], 'license': metadata['license'],
        'download_url': download_url,
        'attribution': 'Deutsche Fußball Liga (DFL); Bassek et al. (2025), doi:10.1038/s41597-025-04505-y',
        'file': source, 'sha256': digest(target, 'sha256'),
    }
    (args.out / 'download_manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(target)
    print('Verified size, MD5 and SHA256:', manifest['sha256'])


if __name__ == '__main__':
    main()
