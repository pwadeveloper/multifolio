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

def head(label, heading, lead=None):
    parts = [kicker(label), el('h2', heading)]
    if lead: parts.append(el('p', lead, className='section-lead'))
    return el('div', parts, className='section-head')

def cta(label, href, className='pricing-cta', glyph='↗', **extra):
    return el('a', [el('span', label), el('span', glyph, **{'aria-hidden': 'true'})], href=href, className=className, **extra)

def book(label='Book a free 15-min call', className='pricing-cta'):
    return cta(label, BOOKING, className, target='_blank', rel='noopener noreferrer')

def price(amount, unit, caption, variant=None, prefix=None, compare=None):
    line = ([el('span', prefix, className='tier-prefix')] if prefix else []) + [el('span', amount, className='tier-amount')]
    parts = [el('div', line, className='tier-price-line'), el('span', unit, className='tier-unit'), el('p', caption, className='tier-caption')]
    if compare: parts.append(el('p', compare, className='tier-compare'))
    return el('div', parts, className='tier-price' + (f' {variant}' if variant else ''))

def specs(rows):
    return el('dl', [node for term, detail in rows for node in (el('dt', term), el('dd', detail))], className='tier-specs')

def tier(key, name, term, outcome, prices, action, note, gets, rows, badge=None, extra=()):
    top = [el('span', name, className='tier-name')]
    if badge: top.append(el('span', badge, className='tier-badge'))
    top.append(el('span', term, className='tier-term'))
    body = [el('div', top, className='tier-top'), el('p', outcome, className='tier-outcome'), el('div', prices, className='tier-prices')]
    body += list(extra)
    body += [action, el('p', note, className='tier-note'),
             el('div', [el('p', 'You get', className='tier-gets-head'), el('ul', [el('li', item) for item in gets], className='tier-list')], className='tier-gets'),
             specs(rows)]
    return el('article', body, className='tier tier-' + key + (' tier-featured' if badge else ''), **{'aria-label': name + ' package'})

def turnaround(tier, metrics):
    cols = [el('span', tier, className='turnaround-tier')]
    for number, unit, label in metrics:
        cols.append(el('div', [el('span', number, className='turnaround-number'), el('span', unit, className='turnaround-unit'), el('p', label, className='turnaround-label')], className='turnaround-metric'))
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
    'See exactly what I do with your footage, before you commit to anything.',
    [price('₦450,000', 'NGN · one-time', 'A complete five-video set, delivered and ready to post.')],
    cta('Start with Starter', '/checkout', 'pricing-cta pricing-cta-secondary'),
    'One-time payment. No subscription, no auto-renewal.',
    ['4 short-form edits for Reels, Shorts and TikTok', '1 long-form edit', 'Burned-in captions on all shorts',
     'Colour and sound pass on every video', 'Platform-correct exports, named and organised'],
    [('Lengths', 'Shorts 15–90s (9:16) · Long-form up to 20 minutes (16:9)'),
     ('Revisions', '2 rounds per video'),
     ('Turnaround', 'First cuts in 7 working days, everything by day 10'),
     ('Best for', 'First-time clients who want proof before a retainer.')],
    extra=[el('p', 'Starter is always one-time — it’s the no-commitment way in.', className='tier-only-note when-monthly')])

GROWTH = tier(
    'growth', 'GROWTH', 'monthly',
    'A full month of content, delivered on schedule, without you chasing anyone.',
    [price('₦680,000', 'NGN · per month', 'Twelve videos a month, delivered on schedule, without you having to chase me for any of them.',
           variant='when-monthly', compare='₦800,000 as a one-off — you save ₦120,000 a month on retainer.'),
     price('₦800,000', 'NGN · one-time', 'The same twelve-video scope as a single project, with no ongoing commitment.',
           variant='when-once', compare='₦680,000 a month on retainer — 15% less for the same work.')],
    book(),
    'Monthly billing. Cancel with 30 days’ notice — no lock-in.',
    ['10 short-form edits a month', '2 long-form edits a month',
     'Burned-in captions plus .srt subtitle files', 'Subtitles in 1 extra language: Hausa, Yoruba, Igbo or Pidgin',
     '2 custom thumbnails per long-form video', 'Priority turnaround, ahead of one-off projects', 'A 30-minute check-in call each month'],
    [('Lengths', 'Shorts 15s–5 minutes (9:16) · Long-form up to 35 minutes (16:9)'),
     ('Revisions', '3 rounds per video'),
     ('Turnaround', 'First cut within 5 working days · revisions back within 48 hours'),
     ('Best for', 'Founders, brands and creators posting every week.')],
    badge='MOST POPULAR')

STUDIO = tier(
    'studio', 'STUDIO', 'shoot + edit',
    'I come to you, film it properly, and turn it into a story worth keeping.',
    [price('₦2,125,000', 'NGN · per month · excludes travel', 'One shoot day and a full edit package every month, filmed and cut by me and a small crew.',
           variant='when-monthly', prefix='from', compare='Saves ₦375,000 against booking each production separately.'),
     price('₦2,500,000', 'NGN · per production · excludes travel', 'A directed shoot and a finished film, plus a month of social cutdowns from the same footage.',
           variant='when-once', prefix='from', compare='From ₦2,125,000 a month if you film with us regularly.')],
    book(className='pricing-cta pricing-cta-secondary'),
    'Price excludes travel cost. Travel, accommodation and permits are quoted separately and approved by you before I book anything.',
    ['1–2 filming days with me and a small crew, anywhere in Nigeria', 'Documentary storytelling — I find the story on the day',
     '1 hero film, fully graded and sound-mixed', '8 short-form cutdowns from the same shoot',
     'Licensed music and a full caption and subtitle package', 'Thumbnail pack for the hero film',
     'A 60-minute strategy call before I roll', 'Your raw footage, organised and handed over'],
    [('Lengths', 'Hero film 5–35 minutes · Shorts 15s–5 minutes'),
     ('Revisions', '3 rounds on the hero film, 2 on each cutdown'),
     ('Turnaround', 'Shoot booked within 3 weeks · first cut 10 working days after wrap'),
     ('Best for', 'Organisations, agencies and brands with a story that deserves to be filmed, not just edited.')])

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
    head('01 / PACKAGES', 'Pick the rhythm you need.', 'Every package starts with a call and a written scope. Nothing begins until you approve it.'),
    el('input', type='radio', name='billing', id='bill-once', className='bill-input', **{'aria-describedby': 'billing-note'}),
    el('input', type='radio', name='billing', id='bill-month', className='bill-input', defaultChecked=True, **{'aria-describedby': 'billing-note'}),
    el('div', [
      el('label', 'One-time', htmlFor='bill-once'),
      el('label', ['Monthly', el('span', 'save 15%', className='toggle-save')], htmlFor='bill-month'),
    ], className='billing-toggle'),
    el('p', 'The same scope costs 15% less on a monthly retainer than it does as one-off projects. Starter is always one-time.', className='billing-note', id='billing-note'),
    el('div', [STARTER, GROWTH, STUDIO], className='pricing-tiers'),
    el('p', 'Not sure which fits? Book the call — I’ll tell you honestly, even if the answer is Starter.', className='tiers-footnote'),
  ], className='pricing-section pricing-section-packages', id='packages'),


  el('section', [
    head('02 / ADD-ONS', 'Bolt any of these onto any package.'),
    el('div', [
      addon('Extra short-form edit', 'Same style, same turnaround as the rest of your batch.', '₦80,000 each · ₦65,000 on a retainer'),
      addon('Extra long-form edit', 'Beyond what your package already includes.', '₦180,000 each'),
      addon('Rush 48-hour delivery', 'Subject to availability — I will tell you before you pay.', '+35% of the project fee'),
    ], className='addons'),
    el('p', 'Add-ons are quoted and approved before I start them. Nothing reaches an invoice you have not seen first.', className='addons-note'),
  ], className='pricing-section', id='add-ons'),

  el('section', [
    head('03 / TURNAROUND', 'How fast you get your videos.'),
    el('div', [
      turnaround('STARTER', [('7', 'working days', 'to your first cuts'), ('10', 'working days', 'to everything delivered')]),
      turnaround('GROWTH', [('5', 'working days', 'to your first cut'), ('48', 'hours', 'to revisions coming back')]),
      turnaround('STUDIO', [('3', 'weeks', 'to your shoot date'), ('10', 'working days', 'to first cut after wrap')]),
    ], className='turnaround'),
    el('p', 'The clock starts when your footage and brief are both in — not before.', className='turnaround-note'),
  ], className='pricing-section', id='turnaround'),

  el('section', [
    head('04 / HOW IT WORKS', 'Four steps, start to posted.'),
    el('ol', [
      step('01', 'Book a call', 'Fifteen minutes. I learn what you are making, who it is for, and what is currently in the way.'),
      step('02', 'Brief & scope', 'You get it in writing: deliverables, lengths, revision rounds, dates, price. Nothing starts until you approve it.'),
      step('03', 'Edit & review', 'First cuts arrive on the agreed date. You review, I revise — within the rounds your package includes.'),
      step('04', 'Deliver & post', 'Final files land organised and platform-ready. Shorts sized per platform, captions burned in, thumbnails attached.'),
    ], className='process'),
  ], className='pricing-section', id='process'),




  el('section', [
    el('div', [kicker('05 / QUESTIONS'), el('h2', 'Before we hit play.')], className='pricing-notes-heading'),
    el('div', [
      faq('What footage do you need from me?', 'Whatever you have — phone, camera, screen recordings. Send the highest quality version you have, unedited, via Google Drive, WeTransfer or a shared folder. I will tell you on the call if there is a gap, before you pay anything.'),
      faq('What if I have no footage at all?', 'Then Starter and Growth are not for you yet — Studio is. I come and film it. If a full production is more than you need right now, book the call anyway and I will map out the cheapest way to get usable footage, even if that is you and a phone on a tripod.'),
      faq('How do I pay?', 'Starter: 70% to start and 30% on delivery, or pay in full online by card or transfer. Growth: billed monthly, on the same date each month. Studio: 70% before the shoot, 30% on final delivery. Bank transfer and card both work. Invoices and receipts for organisations and agencies, and I can work with your procurement process.'),
      faq('How many revisions do I get?', 'Starter 2 rounds per video, Growth 3, Studio 3 on the hero film and 2 per cutdown. A round is one consolidated set of notes. And if the first cut misses the approved brief, I recut it free and that round does not count against your total.'),
      faq('Who owns the final files?', 'Client reserves the right to all agreed upon deliverables.'),
      faq('Can I cancel a retainer?', 'Yes. 30 days’ notice, any month, no exit fee. You keep everything delivered and paid for up to that point. There is no lock-in contract — the work should be the reason you stay.'),
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

DESC = 'Video packages for Nigerian founders, brands and organisations. Starter ₦450,000 one-time, Growth from ₦680,000 a month, Studio shoot and edit.'
DESC_RE = r'(?:Pricing details coming soon\.|4 short videos and 1 long-form video\.[^"]*|Video packages for Nigerian founders[^"]*)'

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
p.write_text(page)
print('Built Pricing HTML and RSC from the same content tree.')
