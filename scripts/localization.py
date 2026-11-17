"""Simplified Chinese language pack tooling.

The pack is translated directly from the English text shipped with RTSS:
entry structure (#src / #hst / #dlu) comes from the official sample pack in
Localization/RUS, help topics come from the English Help folder.

  extract  write UTF-8 work files (English source + current Chinese, if any)
  build    turn the work files into the GBK / CRLF pack in src/localization/CHN
  check    compare src/localization/CHN with an RTSS installation
  icon     redraw the 16x16 language icon (zhcn.ico)
"""
from pathlib import Path
import argparse, json, re, sys

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'src/localization/CHN'
WORK = ROOT / 'build/l10n-work'
DEFAULT_RTSS = Path('C:/Program Files (x86)/RivaTuner Statistics Server')
SAMPLE = 'RUS'  # the reference pack RTSS keeps up to date for translators
TOKEN = re.compile(r'%(?:PRODUCTNAME%|(?:I64)?[-+0-9.#]*[a-zA-Z%])|\\[nt]')


def parse_db(text):
    """Return the entries of a translation database file."""
    entries, cur = [], None
    for line in text.splitlines():
        if line.startswith('#src '):
            cur = {'src': line[5:], 'dst': '', 'extra': []}
        elif cur is None:
            continue
        elif line.startswith('#dst '):
            cur['dst'] = line[5:]
        elif line.startswith(('#hst', '#dlu')):
            cur['extra'].append(line)
        elif line.startswith('#end'):
            entries.append(cur)
            cur = None
    return entries


def read(path, enc):
    return path.read_bytes().decode(enc)


def db_files(base):
    return sorted(p.relative_to(base) for p in base.rglob('*') if p.is_file())


def extract(rtss):
    sample = rtss / 'Localization' / SAMPLE / 'Translation'
    for rel in db_files(sample):
        entries = parse_db(read(sample / rel, 'cp1251'))
        current = PACK / 'Translation' / rel
        known = {e['src']: e['dst'] for e in parse_db(read(current, 'gbk'))} if current.is_file() else {}
        for e in entries:
            e['dst'] = known.get(e['src'], '')
        out = WORK / 'ui' / rel.with_name(rel.name + '.json')
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding='utf-8')
    for rel in db_files(rtss / 'Help'):
        if rel.name == 'MAP':
            continue
        for kind, src, enc in [('help-en', rtss / 'Help' / rel, 'cp1252'), ('help-zh', PACK / 'Help' / rel, 'gbk')]:
            if src.is_file():
                out = WORK / kind / rel.with_name(rel.name + '.txt')
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(read(src, enc).replace('\r\n', '\n'), encoding='utf-8')
    print(f'work files written to {WORK}')


def write_gbk(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.replace('\r\n', '\n').replace('\n', '\r\n').encode('gbk'))


def build():
    errors = []
    for f in sorted((WORK / 'ui').rglob('*.json')):
        rel = f.relative_to(WORK / 'ui').with_suffix('')
        lines = []
        for e in json.loads(f.read_text(encoding='utf-8')):
            dst = e['dst'].strip()
            if not dst:
                errors.append(f'{rel}: missing translation for {e["src"]!r}')
            if TOKEN.findall(e['src']) != TOKEN.findall(dst):
                errors.append(f'{rel}: format tokens differ in {e["src"]!r}')
            lines += ['#src ' + e['src'], '#dst ' + dst, *e['extra'], '#end']
        write_gbk(PACK / 'Translation' / rel, '\n'.join(lines) + '\n')
    for f in sorted((WORK / 'help-zh').rglob('*.txt')):
        rel = f.relative_to(WORK / 'help-zh').with_suffix('')
        write_gbk(PACK / 'Help' / rel, f.read_text(encoding='utf-8').rstrip('\n') + '\n')
    if errors:
        sys.exit('\n'.join(errors))
    print(f'pack written to {PACK}')


def check(rtss):
    problems = []
    sample = rtss / 'Localization' / SAMPLE / 'Translation'
    for rel in db_files(sample):
        ours = PACK / 'Translation' / rel
        if not ours.is_file():
            problems.append(f'missing file Translation/{rel.as_posix()}')
            continue
        want = {e['src'] for e in parse_db(read(sample / rel, 'cp1251'))}
        have = {e['src']: e for e in parse_db(read(ours, 'gbk'))}
        problems += [f'{rel.as_posix()}: missing {s!r}' for s in sorted(want - have.keys())]
        problems += [f'{rel.as_posix()}: obsolete {s!r}' for s in sorted(have.keys() - want)]
        problems += [f'{rel.as_posix()}: format tokens differ in {s!r}'
                     for s, e in have.items() if TOKEN.findall(s) != TOKEN.findall(e['dst'])]
    for rel in db_files(rtss / 'Help'):
        if rel.name != 'MAP' and not (PACK / 'Help' / rel).is_file():
            problems.append(f'missing help topic {rel.as_posix()}')
    for rel in db_files(PACK / 'Help'):
        if not (rtss / 'Help' / rel).is_file():
            problems.append(f'obsolete help topic {rel.as_posix()}')
    print('\n'.join(problems) or 'language pack matches this RTSS installation')
    sys.exit(1 if problems else 0)


def icon(cn_font):
    from PIL import Image, ImageDraw, ImageFont
    S = 8
    im = Image.new('RGBA', (16 * S, 16 * S))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, 16 * S - 1, 16 * S - 1), radius=4 * S, fill='#8DDABD')
    f = ImageFont.truetype(str(cn_font), 13 * S)
    f.set_variation_by_axes([800])
    d.text((8 * S, 8 * S), '中', font=f, fill='#10241C', anchor='mm')
    im.resize((16, 16), Image.Resampling.LANCZOS).save(PACK / 'zhcn.ico', sizes=[(16, 16)])
    print(f'icon written to {PACK / "zhcn.ico"}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=['extract', 'build', 'check', 'icon'])
    parser.add_argument('--rtss', type=Path, default=DEFAULT_RTSS, help='RTSS installation folder')
    parser.add_argument('--cn-font', type=Path, default=Path('C:/Windows/Fonts/NotoSansSC-VF.ttf'))
    args = parser.parse_args()
    {'extract': lambda: extract(args.rtss), 'build': build, 'check': lambda: check(args.rtss),
     'icon': lambda: icon(args.cn_font)}[args.command]()
