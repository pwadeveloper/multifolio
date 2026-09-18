"""Build the Pricing page and matching RSC payload from one content tree."""
from pathlib import Path
import html
import json
import re

ROOT = Path(__file__).resolve().parents[1] / 'mirror'

def el(tag, children='', **props):
    return ['$', tag, None, props if tag in ('br', 'hr') else {**props, 'children': children}]

def render(node):
    if isinstance(node, str):
        return html.escape(node)
    _, tag, _, props = node
    attrs = ''.join(f' {"class" if key == "className" else key}="{html.escape(str(value))}"' for key, value in props.items() if key != 'children')
    if tag in ('br', 'hr'): return f'<{tag}{attrs}/>'
    children = props['children']
    return f'<{tag}{attrs}>' + (''.join(render(child) for child in children) if isinstance(children, list) and (not children or children[0] != '$') else render(children)) + f'</{tag}>'

main = el('main', [
    el('section', [
        el('p', 'MULTIMUDIA / VIDEO EDITING', className='pricing-kicker'),
        el('div', [
            el('h1', ['Short-form impact.', el('br'), el('span', 'Long-form stories.')]),
            el('p', 'A little of both. One package to bring your content to life, from the quick watch to the deeper dive.', className='pricing-lead'),
        ], className='pricing-heading-row'),
    ], className='pricing-hero'),
    el('section', [
        el('div', [
            el('div', [el('span', '01 / THE STARTING PACKAGE', className='pricing-kicker'), el('span', '5 videos. One package.', className='pricing-tag')], className='package-topline'),
            el('h2', 'The content package'),
            el('p', 'A mix of short and long-form edits, ready for your next chapter.', className='package-description'),
            el('div', [
                el('div', [el('span', '04', className='deliverable-number'), el('div', [el('h3', 'Short-form videos'), el('p', 'For your Reels, Shorts & social feed.')]), el('div', [el('span', '▶') for _ in range(4)], className='short-film-strip', **{'aria-hidden':'true'})], className='deliverable-row'),
                el('div', [el('span', '01', className='deliverable-number'), el('div', [el('h3', 'Long-form video'), el('p', 'For a story with room to unfold.')]), el('div', el('span','▶'), className='long-film-frame', **{'aria-hidden':'true'})], className='deliverable-row'),
            ], className='deliverables'),
            el('p', 'The minimum booking: 4 short videos + 1 long-form video.', className='package-footnote'),
        ], className='package-content'),
        el('aside', [
            el('p', 'YOUR INVESTMENT', className='pricing-kicker'),
            el('div', [el('span', '$350', className='package-price'), el('span', 'USD', className='currency-label')], className='price-line'),
            el('div', [el('span','or'), el('span', '₦450,000', className='naira-price'), el('span','NGN', className='currency-label')], className='alternate-price'),
            el('p', 'For the complete five-video package.', className='price-caption'),
            el('div', [
                el('a', [el('span', 'Start my retainer'), el('span','↗', **{'aria-hidden':'true'})], href='/checkout', className='pricing-cta'),
                el('a', [el('span', 'Book an intro call'), el('span','↗', **{'aria-hidden':'true'})], href='https://calendar.app.google/4Z1x1rKG1f6mJqTu9', target='_blank', rel='noopener noreferrer', className='pricing-cta pricing-cta-secondary'),
            ], className='pricing-actions'),
            el('p', 'One-time payment. Scope and delivery timeline agreed before we begin.', className='price-note'),
        ], className='package-investment'),
    ], className='pricing-package', **{'aria-label':'Starting video editing package'}),
    el('section', [
        el('div', [el('p','A FEW THINGS TO KNOW',className='pricing-kicker'),el('h2','Before we hit play.')],className='pricing-notes-heading'),
        el('div', [
            el('details', [el('summary','What’s the minimum package?'),el('p','Four short-form videos and one long-form video, for $350 USD or ₦450,000. Both prices cover the same five-video package.')]),
            el('details', [el('summary','What should I have ready?'),el('p','Your footage, an idea of what you want to make, and any references you love. Include your target platforms and preferred deadline so we can define the brief.')]),
            el('details', [el('summary','How do we decide the scope?'),el('p','We’ll agree on video lengths, the editing style, revisions, and the delivery timeline before work starts.')]),
        ],className='pricing-faq'),
    ],className='pricing-notes'),
    el('footer',[el('span','MULTIMUDIA'),el('span','Made to be watched.')],className='pricing-footer'),
], className='pricing-page')

rsc_path=ROOT/'pricing.rsc'
rsc=rsc_path.read_text()
rsc=re.sub(r'^1:.*$', lambda _: '1:'+json.dumps(main,separators=(',',':')).replace('"$350"', '"$$350"'),rsc,flags=re.M)
rsc=rsc.replace('Pricing — Deji Ajetomobi','Pricing — Multimudia').replace('Pricing details coming soon.','4 short videos and 1 long-form video. $350 USD or ₦450,000.')
rsc_path.write_text(rsc)
p=ROOT/'pricing/index.html'
page=p.read_text().split('<script>self.__VINEXT_RSC_CHUNKS__')[0]
page=re.sub(r'<main\b.*?</main>',lambda _:render(main),page,flags=re.S)
page=page.replace('Pricing — Deji Ajetomobi','Pricing — Multimudia').replace('Pricing details coming soon.','4 short videos and 1 long-form video. $350 USD or ₦450,000.')
page += '<script>self.__VINEXT_RSC_CHUNKS__=['+json.dumps(rsc).replace('<','\\u003c')+'];self.__VINEXT_RSC_DONE__=true</script>'
p.write_text(page)
print('Built Pricing HTML and RSC from the same content tree.')
