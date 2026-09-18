"""Update the static mirror's navigation and generate its Pricing route."""
from pathlib import Path
import html
import json
import re

ROOT = Path(__file__).resolve().parents[1] / 'mirror'
nav = ROOT / 'assets/Nav-BGLgzeL4.js'
s = nav.read_text()
s = re.sub(r'var g=\[.*?\];function _', 'var g=[{label:`Selected Work`,href:`/design`},{label:`Pricing`,href:`/pricing`}];function _', s, count=1)
nav.write_text(s)

def navigation(match):
    start, content, end = match.groups()
    links = re.findall(r'<div class="nav-brand-item[^\"]*">.*?</div>', content)
    selected = next((re.search(r'href="([^\"]+)"', link).group(1) for link in links if 'aria-current="page"' in link), '/')
    selected = selected if selected in ('/design', '/pricing') else '/design'
    result = []
    for label, href in [('Selected Work', '/design'), ('Pricing', '/pricing')]:
        active = href == selected
        result.append(f'<div class="nav-brand-item{" nav-brand-item--active" if active else ""}"><a href="{href}" class="nav-brand{" nav-brand--active" if active else ""}"' + (' aria-current="page"' if active else '') + f' data-label="{label}"><span>{label}</span></a></div>')
    return start + ''.join(result) + end

pattern = r'(<nav class="nav-content" aria-label="Primary navigation">)(.*?)(</nav>)'
for path in ROOT.rglob('*.html'):
    s = path.read_text()
    updated = re.sub(pattern, navigation, s, flags=re.S)
    if updated != s:
        path.write_text(updated)

# Use native RSC elements: the existing router and shared animated Nav work
# identically for direct loads, prefetching, client navigation, and history.
def element(tag, children, **props):
    return ['$', tag, None, {**props, 'children': children}]
main = element('main', [
    element('p', 'Working together', className='pricing-eyebrow'),
    element('h1', 'Pricing'),
    element('p', 'Pricing details coming soon.', className='pricing-description'),
], className='pricing-page')

def render(node):
    if isinstance(node, str):
        return html.escape(node)
    _, tag, _, props = node
    attrs = ''.join(f' {"class" if k == "className" else k}="{html.escape(v)}"' for k, v in props.items() if k != 'children')
    children = props['children']
    return f'<{tag}{attrs}>' + (''.join(render(n) for n in children) if isinstance(children, list) else render(children)) + f'</{tag}>'

rsc = (ROOT / 'engineering.rsc').read_text()
rsc = rsc.replace('/engineering', '/pricing').replace('"engineering"', '"pricing"')
rsc = rsc.replace('& Engineering', 'Pricing').replace('Engineering projects by Deji Ajetomobi', 'Pricing')
rsc = rsc.replace('Interactive tools and experiments by Deji Ajetomobi, exploring the space between design and engineering.', 'Pricing details coming soon.')
# Keep the existing image asset until a pricing-specific image is supplied.
rsc = rsc.replace('/opengraph/pricing-', '/opengraph/engineering-')
rsc = re.sub(r'8:I[^\n]*\n', '', rsc)
rsc = re.sub(r'^1:.*$', lambda _: '1:' + json.dumps(main, separators=(',', ':')), rsc, flags=re.M)
(ROOT / 'pricing.rsc').write_text(rsc)
page = (ROOT / 'engineering/index.html').read_text().split('<script>self.__VINEXT_RSC_CHUNKS__')[0]
page = re.sub(r'<main\b.*?</main>', lambda _: render(main), page, flags=re.S)
page = page.replace('/engineering', '/pricing').replace('&amp; Engineering', 'Pricing').replace('Engineering projects by Deji Ajetomobi', 'Pricing')
page = page.replace('Interactive tools and experiments by Deji Ajetomobi, exploring the space between design and engineering.', 'Pricing details coming soon.')
page = page.replace('/opengraph/pricing-', '/opengraph/engineering-')
page = page.replace('href="/design" class="nav-brand nav-brand--active" aria-current="page"', 'href="/design" class="nav-brand"')
page = page.replace('<div class="nav-brand-item nav-brand-item--active">', '<div class="nav-brand-item">')
page = page.replace('<div class="nav-brand-item"><a href="/pricing" class="nav-brand"', '<div class="nav-brand-item nav-brand-item--active"><a href="/pricing" class="nav-brand nav-brand--active" aria-current="page"')
page += '<script>self.__VINEXT_RSC_CHUNKS__=[' + json.dumps(rsc).replace('<', '\\u003c') + '];self.__VINEXT_RSC_DONE__=true</script>'
(ROOT / 'pricing').mkdir(exist_ok=True)
(ROOT / 'pricing/index.html').write_text(page)

# The former About homepage now opens Selected Work.
(ROOT / 'index.html').write_text('''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Selected Work</title><meta http-equiv="refresh" content="0;url=/design"><link rel="canonical" href="/design"><script>location.replace('/design' + location.search + location.hash)</script></head><body><a href="/design">View Selected Work</a></body></html>''')
(ROOT / '.rsc').write_text((ROOT / 'design.rsc').read_text())
