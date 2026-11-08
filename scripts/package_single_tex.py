"""Package the two single-file papers with only their required figure resources."""
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    files = set()
    for folder in ('paper', '_中文版'):
        base = ROOT / folder
        files.update([base / 'main.tex', base / 'main.pdf'])
        source = (base / 'main.tex').read_text(encoding='utf-8')
        assert not re.search(r'\\(?:input|include|lstinputlisting)\b', source)
        path_line = next(line for line in source.splitlines() if line.startswith(r'\graphicspath'))
        search = [base] + [base / name for name in re.findall(r'\{([^{}]+/)\}', path_line)]
        for name in re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', source):
            target = next((directory / name for directory in search if (directory / name).is_file()), None)
            if target is None:
                raise FileNotFoundError(name)
            files.add(target.resolve())
    archive = ROOT.parent / 'UPC2026_ProblemB_单文件LaTeX_中英文.zip'
    readme = (
        '中英文各只有一个 main.tex，内嵌全部正文、参考文献、表格、TikZ 路线图与附录代码。\n'
        '保持目录结构，分别进入 paper、_中文版，运行三遍：\n'
        'xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error main.tex\n'
        '依赖 TeX Live/XeLaTeX、Times New Roman；中文另需 SimSun、SimHei、KaiTi 字体。\n'
        '图片作为共享外部资源，无其他 tex 或 Python 文件编译依赖。\n'
    )
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(files):
            bundle.write(path, path.relative_to(ROOT))
        bundle.writestr('README_编译说明.txt', readme)
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
    print(f'Single-TeX bundle: {len(files) + 1} files, {archive.stat().st_size} bytes')


if __name__ == '__main__':
    main()
