"""Build the Pricing page and matching RSC payload from one content tree."""
from pathlib import Path
import html
import json
import re

ROOT = Path(__file__).resolve().parents[1] / 'mirror'
BOOKING = 'https://calendar.app.google/4Z1x1rKG1f6mJqTu9'
VOID = ('br', 'hr', 'input', 'img')
ATTR = {'className': 'class', 'htmlFor': 'for', 'defaultChecked': 'checked'}

def el(tag, children='', **props):
    return ['$', tag, None, props if tag in VOID else {**props, 'children': children}]

def attribute(key, value):
    name = ATTR.get(key, key)
    if value is True: return f' {name}'
    if value is False or value is None: return ''
    return f' {name}="{html.escape(str(value))}"'

def render(node):
    if isinstance(node, str):
        return html.escape(node)
    _, tag, _, props = node
    attrs = ''.join(attribute(key, value) for key, value in props.items() if key != 'children')
    if tag in VOID: return f'<{tag}{attrs}/>'
    children = props['children']
    inner = ''.join(render(child) for child in children) if isinstance(children, list) and (not children or children[0] != '$') else render(children)
    return f'<{tag}{attrs}>{inner}</{tag}>'

# --- content helpers -------------------------------------------------------

def kicker(text):
    return el('p', text, className='pricing-kicker')

def head(label, heading, lead=None, center=False):
    parts = [kicker(label), el('h2', heading)]
    if lead: parts.append(el('p', lead, className='section-lead'))
    return el('div', parts, className='section-head' + (' section-head-center' if center else ''))

def cta(label, href, className='pricing-cta', glyph='↗', **extra):
    return el('a', [el('span', label), el('span', glyph, **{'aria-hidden': 'true'})], href=href, className=className, **extra)

def book(label='Book a free 15-min call', className='pricing-cta'):
    return cta(label, BOOKING, className, target='_blank', rel='noopener noreferrer')

def price(amount, unit, caption=None, variant=None, prefix=None, compare=None, per=None):
    line = ([el('span', prefix, className='tier-prefix')] if prefix else [])
    line += [el('span', '₦', className='tier-currency'), el('span', amount, className='tier-amount'),
             el('span', unit, className='tier-unit')]
    parts = [el('div', line, className='tier-price-line')]
    if per: parts.append(el('p', per, className='tier-per'))
    if caption: parts.append(el('p', caption, className='tier-caption'))
    if compare: parts.append(el('p', compare, className='tier-compare'))
    return el('div', parts, className='tier-price' + (f' {variant}' if variant else ''))

def dual(value, tag, className=''):
    """A string renders once. A (one-time, season) pair renders both, toggled by the billing radios."""
    def node(text, variant):
        classes = ' '.join(c for c in (className, variant) if c)
        return el(tag, text, className=classes) if classes else el(tag, text)
    if isinstance(value, tuple):
        return [node(value[0], 'when-once'), node(value[1], 'when-monthly')]
    return [node(value, '')]

def specs(rows):
    return el('dl', [node for term, detail in rows for node in ([el('dt', term)] + dual(detail, 'dd'))], className='tier-specs')

def get_item(item):
    return el('li', item[0], className=item[1]) if isinstance(item, tuple) else el('li', item)

def compare_box(once, season):
    """Comparison boxes live in the expanded panel but still follow the billing toggle."""
    return [el('p', once, className='tier-compare when-once'), el('p', season, className='tier-compare when-monthly')]

def more_button(panel_id, label='See more'):
    return el('button', [el('span', label, className='more-label'), el('span', '', className='more-chevron', **{'aria-hidden': 'true'})],
              type='button', className='more-toggle',
              **{'aria-expanded': 'false', 'aria-controls': panel_id, 'data-more': label, 'data-less': label.replace('See more', 'See less').replace('See what’s included', 'Hide what’s included')})

def panel(panel_id, children):
    # inert both hides it from assistive tech and keyboard, and doubles as the
    # style hook for the height transition (display:none could not animate).
    return el('div', el('div', children, className='panel-inner'), className='more-panel', id=panel_id, inert=True)

def tier(key, name, term, outcome, prices, action, note, gets, rows, badge=None, extra=(), compares=(), visible=5):
    top = dual(name, 'span', 'tier-name')
    if badge: top.append(el('span', badge, className='tier-badge'))
    top += dual(term, 'span', 'tier-term')
    head_parts = [el('div', top, className='tier-top')] + dual(outcome, 'p', 'tier-outcome') + [el('div', prices, className='tier-prices')] + list(extra)
    shown, rest = gets[:visible], gets[visible:]
    panel_id = 'more-' + key
    hidden = ([el('ul', [get_item(i) for i in rest], className='tier-list')] if rest else []) + [specs(rows)] + list(compares)
    foot = [action] + dual(note, 'p', 'tier-note') + [more_button(panel_id)]
    body = [el('div', [el('p', 'You get', className='tier-gets-head'), el('ul', [get_item(i) for i in shown], className='tier-list')], className='tier-gets'),
            el('div', foot, className='tier-foot'),
            panel(panel_id, hidden)]
    label = name[1] if isinstance(name, tuple) else name
    return el('article', [el('div', head_parts, className='tier-head'), el('div', body, className='tier-body')],
              className='tier tier-' + key + (' tier-featured' if badge else ''), **{'aria-label': label + ' package'})

def band(heading, description, price_line, action, gets, rows, note):
    hidden = [el('p', 'You get', className='tier-gets-head'), el('ul', [get_item(i) for i in gets], className='tier-list'), specs(rows), el('p', note, className='band-note')]
    return el('section', [
        el('div', [el('h3', heading), el('p', description, className='band-description'), el('p', price_line, className='band-price')], className='band-main'),
        el('div', [action, more_button('more-studio', 'See what’s included')], className='band-actions'),
        panel('more-studio', hidden),
    ], className='studio-band', **{'aria-label': 'Studio production'})

def turnaround(tier, metrics, note=None):
    cols = [el('span', tier, className='turnaround-tier')]
    for number, unit, label in metrics:
        cols.append(el('div', [el('span', number, className='turnaround-number'), el('span', unit, className='turnaround-unit'), el('p', label, className='turnaround-label')], className='turnaround-metric'))
    if note: cols.append(el('p', note, className='turnaround-col-note'))
    return el('div', cols, className='turnaround-col')

def addon(name, detail, cost):
    return el('div', [el('div', [el('h3', name), el('p', detail)], className='addon-text'), el('span', cost, className='addon-price')], className='addon-row')

def step(number, title, body):
    return el('li', [el('span', number, className='step-number'), el('div', [el('h3', title), el('p', body)], className='step-text')], className='step')

def faq(question, answer):
    return el('details', [el('summary', question), el('p', answer)])

# --- page ------------------------------------------------------------------

STARTER = tier(
    'starter', 'STARTER', 'one-time',
    'A complete five-video set, delivered and ready to post.',
    [price('450,000', 'NGN / one-time', per='≈ ₦90,000 per video')],
    cta('Start with Starter', '/checkout', 'pricing-cta pricing-cta-secondary'),
    'One-time payment. No subscription, no auto-renewal.',
    ['4 short-form edits for Reels, Shorts and TikTok', '1 long-form edit', 'Burned-in captions on all shorts',
     'Colour and sound pass on every video', 'Platform-correct exports, named and organised'],
    [('Lengths', 'Shorts 15–90s (9:16) · Long-form up to 20 minutes (16:9)'),
     ('Revisions', '2 rounds per video'),
     ('Turnaround', 'First cuts in 7 working days, everything by day 10'),
     ('Best for', 'First-time clients who want proof before committing to a season.')],
    extra=[el('p', 'No commitment. Upgrade to a Growth season within 14 days and your Starter fee is credited toward month one.', className='tier-only-note when-monthly')])

GROWTH = tier(
    'growth', 'GROWTH', ('single project', '3-month season'),
    ('Twelve videos, one project, no ongoing commitment.',
     'Twelve videos every month for three months, delivered on schedule, without you having to chase me for any of them.'),
    [price('680,000', 'NGN / month · 3-month season',
           variant='when-monthly', per='≈ ₦57,000 per video'),
     price('800,000', 'NGN / one-time', 'A full batch of 12 videos — 10 short-form and 2 long-form — scoped, edited and delivered as one project.',
           variant='when-once', per='≈ ₦67,000 per video')],
    book(),
    ('One-time payment. No subscription, no auto-renewal.',
     'Billed monthly across a 3-month season. Nothing auto-renewal'),
    ['10 short-form edits a month', '2 long-form edits a month',
     'Burned-in captions plus .srt subtitle files', 'Subtitles in 1 extra language: Hausa, Yoruba, Igbo or Pidgin',
     '2 custom thumbnails per long-form video',
     ('12 videos delivered across roughly a month, on a schedule we agree upfront.', 'when-once'),
     'Priority turnaround, ahead of one-off projects', 'A 30-minute check-in call each month'],
    [('Lengths', 'Shorts 15s–5 minutes (9:16) · Long-form up to 35 minutes (16:9)'),
     ('Revisions', '3 rounds per video'),
     ('Turnaround', 'First cut within 5 working days · revisions back within 48 hours'),
     ('Best for', ('Brands with a campaign, launch or backlog to clear in one go.',
                   'Founders, brands and creators posting every week.'))],
    badge='MOST POPULAR',
    compares=compare_box('₦680,000 a month inside a 3-month season — 15% less for the same work.',
                         '₦800,000 as a one-off — you save ₦360,000 across the season.'))

STUDIO = band(
    'Studio — I come to you and film it',
    'Excludes travel. Up to two directed shoot days at your location, one hero film fully graded and sound-mixed, and 8 short-form cutdowns from the same footage.',
    'from ₦2,500,000 per production · or ₦2,125,000 a month in a 3-month season',
    book(className='pricing-cta pricing-cta-secondary band-cta'),
    ['Up to 2 filming days with me and a small crew, anywhere in Nigeria', 'Documentary storytelling — I find the story on the day',
     '1 hero film, fully graded and sound-mixed', '8 short-form cutdowns from the same shoot',
     'Licensed music and a full caption and subtitle package', 'Thumbnail pack for the hero film',
     'A 60-minute strategy call before I roll', 'Your raw footage, organised and handed over'],
    [('Lengths', 'Hero film 5–35 minutes · Shorts 15s–5 minutes'),
     ('Revisions', '3 rounds on the hero film, 2 on each cutdown'),
     ('Turnaround', 'Shoot booked within 3 weeks · first cut 10 working days after wrap'),
     ('Best for', 'Organisations and brands with a story worth filming properly, not just edited.')],
    'Price excludes travel cost. Travel, accommodation and permits are quoted separately and approved by you before I book anything.')

main = el('main', [
  el('section', [
    kicker('MULTIMUDIA / PACKAGES'),
    el('div', [
      el('h1', ['Show up every week.', el('br'), el('span', 'Without living in the edit.')]),
      el('div', [
        cta('See the packages', '#packages', 'pricing-cta pricing-cta-secondary hero-cta', '↓'),
      ], className='pricing-hero-aside'),
    ], className='pricing-heading-row'),
  ], className='pricing-hero'),


  el('section', [
    head('01 / PACKAGES', 'Pick the rhythm you need.', 'Every package starts with a call and a written scope. Nothing begins until you approve it.', center=True),
    el('input', type='radio', name='billing', id='bill-once', className='bill-input', **{'aria-describedby': 'billing-note'}),
    el('input', type='radio', name='billing', id='bill-month', className='bill-input', defaultChecked=True, **{'aria-describedby': 'billing-note'}),
    el('div', [
      el('label', 'One-time', htmlFor='bill-once'),
      el('label', ['Season · 3 months', el('span', 'save 15%', className='toggle-save')], htmlFor='bill-month'),
    ], className='billing-toggle'),
    el('p', 'The same scope costs 15% less inside a 3-month season than it does as one-off projects. Starter is always one-time.', className='billing-note', id='billing-note'),
    el('div', [STARTER, GROWTH], className='pricing-tiers'),
    STUDIO,
    el('p', 'I take on 5 new Growth clients a month. Next opening: [FILL: MONTH]. Not sure which fits? Book the call — I’ll tell you honestly, even if the answer is Starter.', className='tiers-footnote'),
  ], className='pricing-section pricing-section-packages', id='packages'),


  el('section', [
    head('02 / GUARANTEE', 'Month one is on me to get right.',
         'Every season starts with a written brief. If month one misses that brief, you can end the season there and owe nothing more.'),
  ], className='pricing-section pricing-guarantee', id='guarantee'),

  el('section', [
    head('03 / ADD-ONS', 'Bolt any of these onto any package.'),
    el('div', [
      addon('Extra short-form edit', 'Same style, same turnaround as the rest of your batch.', '₦55,000 each · ₦47,000 in a season'),
      addon('Extra long-form edit', 'Beyond what your package already includes.', '₦125,000 each · ₦106,000 in a season'),
      addon('Rush 48-hour delivery', 'Subject to availability — I will tell you before you pay.', '+35% of the project fee'),
    ], className='addons'),
    el('p', 'Add-ons build on a brief and editing style we’ve already set up, so each one costs less than starting fresh. Quoted and approved before I start them. Nothing reaches an invoice you have not seen first.', className='addons-note'),
  ], className='pricing-section', id='add-ons'),

  el('section', [
    head('04 / TURNAROUND', 'How fast you get your videos.'),
    el('div', [
      turnaround('STARTER', [('7', 'working days', 'to your first cut'), ('10', 'working days', 'to everything delivered')]),
      turnaround('GROWTH', [('5', 'working days', 'to your first cut'), ('14', 'working days', 'to everything delivered')]),
      turnaround('STUDIO', [('10', 'working days', 'to your first cut, after wrap'), ('20', 'working days', 'to everything delivered, after wrap')], note='Shoot booked within 3 weeks.'),
    ], className='turnaround'),
    el('p', 'The clock starts when your footage and brief are both in — not before.', className='turnaround-note'),
  ], className='pricing-section', id='turnaround'),

  el('section', [
    head('05 / HOW IT WORKS', 'Four steps, start to posted.'),
    el('ol', [
      step('01', 'Book a call', 'Fifteen minutes. I learn what you are making, who it is for, and what is currently in the way.'),
      step('02', 'Brief & scope', 'You get it in writing: deliverables, lengths, revision rounds, dates, price. Nothing starts until you approve it.'),
      step('03', 'Edit & review', 'First cuts arrive on the agreed date. You review, I revise — within the rounds your package includes.'),
      step('04', 'Deliver & post', 'Final files land organised and platform-ready. Shorts sized per platform, captions burned in, thumbnails attached.'),
    ], className='process'),
  ], className='pricing-section', id='process'),




  el('section', [
    el('div', [kicker('06 / QUESTIONS'), el('h2', 'Before we hit play.')], className='pricing-notes-heading'),
    el('div', [
      faq('What footage do you need from me?', 'Whatever you have — phone, camera, screen recordings. Send the highest quality version you have, unedited, via Google Drive, WeTransfer or a shared folder. I will tell you on the call if there is a gap, before you pay anything.'),
      faq('What if I have no footage at all?', 'Then Starter and Growth are not for you yet — Studio is. I come and film it. If a full production is more than you need right now, book the call anyway and I will map out the cheapest way to get usable footage, even if that is you and a phone on a tripod.'),
      faq('How do I pay?', [el('strong', 'Starter:'), ' Full payment immediately. ', el('strong', 'Growth:'), ' billed monthly, on the same date each month. ', el('strong', 'Studio:'), ' 70% before the shoot, 30% on final delivery. Bank transfer and card both work. Invoices and receipts for organisations and agencies, and I can work with your procurement process.']),
      faq('How many revisions do I get?', 'Starter 2 rounds per video, Growth 3, Studio 3 on the hero film and 2 per cutdown. A round is one consolidated set of notes. And if the first cut misses the approved brief, I recut it free and that round does not count against your total.'),
      faq('Who owns the final files?', 'Client reserves the right to all agreed upon deliverables.'),
      faq('Is there a minimum commitment?', 'Growth and Studio run in 3-month seasons, because content compounds: your audience and the algorithm need about 90 days of consistent posting before the results show. You’re billed monthly, and nothing renews automatically — at the end of the season, you choose whether to continue. And if month one misses the brief we agreed in writing, you can end the season there and owe nothing more. Starter is always one-time, with no commitment at all.'),
      faq('Do you work outside Lagos and Abuja?', 'Yes, anywhere in Nigeria. For Studio shoots, travel, accommodation and permits are quoted separately and approved by you before anything is booked.'),
    ], className='pricing-faq'),
  ], className='pricing-notes', id='faq'),

  el('section', [
    el('h2', 'Let’s work out what you actually need.'),
    el('p', 'Fifteen minutes, no pitch. Tell me what you are making and I’ll tell you which package fits — or if none of them do.', className='final-cta-lead'),
    el('div', [book(), cta('Start with Starter — ₦450,000', '/checkout', 'pricing-cta pricing-cta-secondary')], className='pricing-actions final-cta-actions'),
  ], className='pricing-section final-cta', id='start'),

  el('footer', [el('span', 'MULTIMUDIA'), el('span', 'God Revealed in Many Media Forms')], className='pricing-footer'),
], className='pricing-page')

# Disclosure behaviour. Delegated from document and appended outside <main>, so
# React never owns it and hydration cannot revert it.
TOGGLE_JS = (
    "<script>(function(){"
    "function setLabel(b,open){var s=b.querySelector('.more-label');"
    "if(s)s.textContent=open?b.getAttribute('data-less'):b.getAttribute('data-more');}"
    "document.addEventListener('click',function(e){"
    "var b=e.target&&e.target.closest?e.target.closest('.more-toggle'):null;if(!b)return;"
    "var p=document.getElementById(b.getAttribute('aria-controls'));if(!p)return;"
    "var g=document.querySelector('.pricing-tiers');"
    "var inGrid=!!(g&&g.contains(b));"
    "var cards=g?[].slice.call(g.querySelectorAll('.tier')):[];"
    "if(inGrid&&!g.classList.contains('is-expanded')){"
    "cards.forEach(function(c){c.style.minHeight=Math.round(c.getBoundingClientRect().height)+'px';});}"
    "var open=b.getAttribute('aria-expanded')!=='true';"
    "b.setAttribute('aria-expanded',open?'true':'false');"
    "if(open){p.removeAttribute('inert');}else{p.setAttribute('inert','');}"
    "setLabel(b,open);"
    "if(inGrid){var any=!!g.querySelector('.more-toggle[aria-expanded=\"true\"]');"
    "g.classList.toggle('is-expanded',any);"
    "if(!any)cards.forEach(function(c){c.style.minHeight='';});}"
    "});})()</script>"
)

DESC = 'Video editing and production packages from Multimudia: one-time Starter from ₦450,000, or 3-month Growth and Studio seasons.'
DESC_RE = r'(?:Pricing details coming soon\.|4 short videos and 1 long-form video\.[^"]*|Video packages for Nigerian founders[^"]*|Video editing and production packages from Multimudia[^"]*)'

rsc_path = ROOT / 'pricing.rsc'
rsc = rsc_path.read_text()
rsc = re.sub(r'^1:.*$', lambda _: '1:' + json.dumps(main, separators=(',', ':')), rsc, flags=re.M)
rsc = rsc.replace('Pricing — Deji Ajetomobi', 'Pricing — Multimudia')
rsc = re.sub(DESC_RE, DESC, rsc)
rsc_path.write_text(rsc)
p = ROOT / 'pricing/index.html'
page = p.read_text().split('<script>self.__VINEXT_RSC_CHUNKS__')[0]
page = re.sub(r'<main\b.*?</main>', lambda _: render(main), page, flags=re.S)
page = page.replace('Pricing — Deji Ajetomobi', 'Pricing — Multimudia')
page = re.sub(DESC_RE, DESC, page)
page += '<script>self.__VINEXT_RSC_CHUNKS__=[' + json.dumps(rsc).replace('<', '\\u003c') + '];self.__VINEXT_RSC_DONE__=true</script>'
page += TOGGLE_JS
p.write_text(page)
print('Built Pricing HTML and RSC from the same content tree.')
