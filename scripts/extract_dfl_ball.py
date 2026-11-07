"""Extract the ball frames from a local DFL position XML using bounded memory."""
import argparse
import csv
import xml.etree.ElementTree as ET
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('xml')
    parser.add_argument('output')
    args = parser.parse_args()
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    current = None
    with open(args.output, 'w', newline='', encoding='utf-8') as out:
        fields = ['section', 'frame', 'timestamp', 'x_m', 'y_m', 'z_raw', 'status']
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        for event, el in ET.iterparse(args.xml, events=('start', 'end')):
            tag = el.tag.rsplit('}', 1)[-1]
            if event == 'start' and tag == 'FrameSet':
                current = el.attrib
            if event == 'end' and tag == 'Frame':
                a = el.attrib
                if current is not None and current.get('TeamId') == 'BALL':
                    writer.writerow(dict(section=current.get('GameSection'), frame=a.get('N'),
                                         timestamp=a.get('T'), x_m=a.get('X'), y_m=a.get('Y'),
                                         z_raw=a.get('Z'), status=a.get('BallStatus')))
                el.clear()
            elif event == 'end' and tag == 'FrameSet':
                current = None
                el.clear()


if __name__ == '__main__':
    main()
