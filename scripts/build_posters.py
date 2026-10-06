"""Optimise the dropped cover images and attach them to the work items.

Instagram will not let its reels be framed, so each card shows a cover image
instead. Drop a full-size screenshot into mirror/posters, name it below against
the reel it belongs to, and run this: it writes a web-sized copy into
mirror/assets/posters (which the site build ships) and sets the item's `poster`.

Keyed by the reel code rather than the title, because three items are called
some spelling of KayKav and two are Glory Zone.
"""
from pathlib import Path
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'mirror' / 'posters'
OUT = ROOT / 'mirror' / 'assets' / 'posters'
WORKS = ROOT / 'mirror' / 'works.json'
# sips -Z fits the LONGEST side, which on a portrait cover is the height. The
# card is 420px wide at most, so a 2x screen wants ~840px across: at 9:16 that
# is a 1500px height.
LONGEST = 1500
QUALITY = 68

POSTERS = {
    'DZ7a3NQqC6B': 'compintel.png',                 # CompIntel
    'DZwylcAIhJ0': 'kaykav.png',                    # KayKav
    'DZpeCP0IDB7': 'kaykav2.png',                   # Kaykav
    'DZ9xNCvIDzN': 'kaykav3.png',                   # KayKav
    'C4cy6z0t6rX': 'Gloryzone 2.png',               # GZ Abuja
    'C4r3up6N5ZA': 'GloryZone1.png',                # Gloryzone
    'DbXp2AmMc0V': 'needbills.png',                 # Need Bills
    'DbtI1wiNKMP': 'visa rejection.png',            # Visa Rejection
    'Db3bPZutAS1': 'get in the media.png',          # Get In The Media
    'DdExI2YtTXx': 'uk talent visa evidence.png',   # UK Talent Visa Evidence
    'DdYJkV8tTuD': 'better networking ep 4.png',    # Better Networking EP 4
}

def slug(value):
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', value.lower())).strip('-')

def code_of(url):
    found = re.search(r'/(?:p|reel|tv)/([A-Za-z0-9_-]+)/', url or '')
    return found.group(1) if found else None

items = json.loads(WORKS.read_text())
OUT.mkdir(parents=True, exist_ok=True)
used, written, missing = set(), 0, []

for item in items:
    code = code_of(item.get('url'))
    source_name = POSTERS.get(code)
    if not source_name:
        continue
    source = SOURCE / source_name
    if not source.exists():
        missing.append(source_name)
        continue
    name = slug(item['title'])
    suffix = 2
    while name in used:
        name = slug(item['title']) + '-' + str(suffix)
        suffix += 1
    used.add(name)
    target = OUT / (name + '.jpg')
    subprocess.run(['sips', '-Z', str(LONGEST), '-s', 'format', 'jpeg',
                    '-s', 'formatOptions', str(QUALITY), str(source), '--out', str(target)],
                   check=True, capture_output=True)
    item['poster'] = '/assets/posters/' + target.name
    written += 1

WORKS.write_text(json.dumps(items, indent=2) + '\n')
if missing:
    print('Missing from mirror/posters: ' + ', '.join(missing))
total = sum(f.stat().st_size for f in OUT.glob('*.jpg'))
print(f'Wrote {written} posters into mirror/assets/posters ({total/1024:.0f}KB total).')
