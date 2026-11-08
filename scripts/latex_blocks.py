"""Read and refresh generated regions in each edition's single LaTeX source."""
import re


def read_block(source, name):
    start = '% BEGIN ' + name + '\n'
    end = '% END ' + name
    return source.split(start, 1)[1].split(end, 1)[0]


def write_block(path, name, body):
    source = path.read_text(encoding='utf-8')
    pattern = r'(?m)^% BEGIN ' + re.escape(name) + r'\n.*?^% END ' + re.escape(name) + r'$'
    replacement = '% BEGIN ' + name + '\n' + body.rstrip() + '\n% END ' + name
    updated, count = re.subn(pattern, lambda _: replacement, source, flags=re.S)
    if count != 1:
        raise ValueError(f'{path}: expected one generated region {name}, found {count}')
    path.write_text(updated, encoding='utf-8')
