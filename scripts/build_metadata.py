"""Write the head metadata, structured data, robots and sitemap for every page.

Search engines and AI crawlers read the served HTML, not the client-side route
change, so this writes into each mirrored page's <head>. Run it after
build_pricing.py and before the site build.

Package prices appear here as well as in the page copy that build_pricing.py
owns. Change one, change the other.
"""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1] / 'mirror'
SITE = 'https://multimudia.studio'
EMAIL = 'create@multimudia.studio'
PHONE = '+2347030786526'

KEYWORDS = ('video editor in Nigeria, content editor in Nigeria, video editing Nigeria, '
            'video editor Lagos, video editor Abuja, short-form video editing, Reels editor, '
            'TikTok editor, YouTube editor Nigeria, social media video editing, '
            'long-form video editing, video production Nigeria, content creator editor, '
            'Mudia Imasuen, Multimudia')

# One business record, referenced by every page so a crawler reads it once.
BUSINESS = {
    '@type': 'ProfessionalService',
    '@id': SITE + '/#business',
    'name': 'Multimudia',
    'alternateName': 'Multimudia Studio',
    'url': SITE + '/',
    'image': SITE + '/assets/og-selected-work.png',
    'logo': SITE + '/icon-512.png',
    'email': EMAIL,
    'telephone': PHONE,
    'priceRange': '₦450,000 - ₦2,500,000',
    'currenciesAccepted': 'NGN',
    'description': ('Video editing and production in Nigeria. Short-form edits for Reels, Shorts '
                    'and TikTok, long-form films, and directed shoots, for founders, brands and creators.'),
    'founder': {'@type': 'Person', 'name': 'Mudia Imasuen', 'jobTitle': 'Video editor and producer'},
    'areaServed': {'@type': 'Country', 'name': 'Nigeria'},
    'serviceType': ['Video editing', 'Short-form video editing', 'Long-form video editing',
                    'Video production', 'Social media content editing'],
    'knowsAbout': ['video editing', 'short-form video', 'Reels', 'YouTube Shorts', 'TikTok',
                   'long-form video', 'subtitles and captions', 'colour grading', 'documentary production'],
    'contactPoint': [{
        '@type': 'ContactPoint', 'contactType': 'sales', 'email': EMAIL, 'telephone': PHONE,
        'areaServed': 'NG', 'availableLanguage': ['English'],
    }],
}

def offer(name, price, description, unit=None):
    item = {'@type': 'Offer', 'name': name, 'price': str(price), 'priceCurrency': 'NGN',
            'description': description, 'availability': 'https://schema.org/InStock',
            'url': SITE + '/pricing', 'seller': {'@id': SITE + '/#business'}}
    if unit:
        item['priceSpecification'] = {'@type': 'UnitPriceSpecification', 'price': str(price),
                                      'priceCurrency': 'NGN', 'unitText': unit}
    return item

PACKAGES = {
    '@type': 'OfferCatalog',
    'name': 'Video editing packages',
    'itemListElement': [
        offer('Starter', 450000, '7 short-form edits and 1 long-form edit. One-time, no subscription.'),
        offer('Growth', 680000, '14 short-form and 2 long-form edits a month, or 18 shorts if the long-form '
                                'is swapped out. Billed monthly across a 3-month season.', unit='MON'),
        offer('Studio', 2500000, 'Up to 2 directed shoot days, 1 hero film fully graded and sound-mixed, '
                                 'and 11 short-form cutdowns. Excludes travel.'),
    ],
}

PAGES = {
    'index.html': dict(
        path='/selected-work', index=False,
        title='Video Editor in Nigeria — Multimudia',
        description='Short-form and long-form video editing in Nigeria by Mudia Imasuen.',
        image='/assets/og-selected-work.png', alt='Multimudia, video editing in Nigeria'),
    'selected-work/index.html': dict(
        path='/selected-work', index=True,
        title='Selected Work — Video Editor in Nigeria | Multimudia',
        description='The work speaks. Short-form and long-form video editing in Nigeria by Mudia Imasuen: '
                    'Reels, Shorts and TikTok that get watched, and long-form that holds attention.',
        image='/assets/og-selected-work.png', alt='Multimudia selected video editing work',
        schema=[BUSINESS]),
    'pricing/index.html': dict(
        path='/pricing', index=True,
        title='Pricing — Video Editing Packages in Nigeria | Multimudia',
        description='Video editing packages in Nigeria, priced in the open. Starter ₦450,000 one-time, '
                    'Growth 16 videos a month, or a Studio shoot. Build your own package and see the price.',
        image='/assets/og-pricing.png', alt='Multimudia video editing packages and prices',
        schema=[BUSINESS, PACKAGES]),
    'book/index.html': dict(
        path='/book', index=True,
        title='Book an Intro Call — Multimudia | Video Editor in Nigeria',
        description='Fifteen minutes, no pitch. Tell me what you are making and I will tell you which '
                    'video editing package fits, or if none of them do.',
        image='/assets/og-pricing.png', alt='Book a call with Multimudia'),
    'checkout/index.html': dict(
        path='/checkout', index=False, noindex=True,
        title='Checkout — Multimudia',
        description='Secure checkout for Multimudia video editing packages.',
        image='/assets/og-pricing.png', alt='Multimudia checkout'),
}

STRIP = [
    r'<title>.*?</title>',
    r'<meta\s+name="(?:description|keywords|twitter:[^"]*)"[^>]*/?>',
    r'<meta\s+property="og:[^"]*"[^>]*/?>',
    r'<link\s+rel="canonical"[^>]*/?>',
    r'<script type="application/ld\+json">.*?</script>',
]

def esc(value):
    return (str(value).replace('&', '&amp;').replace('"', '&quot;')
            .replace('<', '&lt;').replace('>', '&gt;'))

def head_for(page):
    url = SITE + page['path']
    image = SITE + page['image']
    tags = [
        '<title>' + esc(page['title']) + '</title>',
        '<meta name="description" content="' + esc(page['description']) + '"/>',
        '<meta name="keywords" content="' + esc(KEYWORDS) + '"/>',
        '<link rel="canonical" href="' + esc(url) + '"/>',
        '<meta property="og:site_name" content="Multimudia"/>',
        '<meta property="og:type" content="website"/>',
        '<meta property="og:locale" content="en_NG"/>',
        '<meta property="og:url" content="' + esc(url) + '"/>',
        '<meta property="og:title" content="' + esc(page['title']) + '"/>',
        '<meta property="og:description" content="' + esc(page['description']) + '"/>',
        '<meta property="og:image" content="' + esc(image) + '"/>',
        '<meta property="og:image:type" content="image/png"/>',
        '<meta property="og:image:width" content="1200"/>',
        '<meta property="og:image:height" content="630"/>',
        '<meta property="og:image:alt" content="' + esc(page['alt']) + '"/>',
        '<meta name="twitter:card" content="summary_large_image"/>',
        '<meta name="twitter:title" content="' + esc(page['title']) + '"/>',
        '<meta name="twitter:description" content="' + esc(page['description']) + '"/>',
        '<meta name="twitter:image" content="' + esc(image) + '"/>',
        '<meta name="twitter:image:alt" content="' + esc(page['alt']) + '"/>',
    ]
    for node in page.get('schema', []):
        data = dict(node)
        data['@context'] = 'https://schema.org'
        tags.append('<script type="application/ld+json">' +
                    json.dumps(data, separators=(',', ':')).replace('<', '\\u003c') + '</script>')
    return ''.join(tags)

def jesc(value):
    assert '"' not in value and '\\' not in value, value
    return value

def patch_payload(text, page):
    """The RSC payload carries its own metadata for client-side navigation. It
    exists twice: as the .rsc file, and JSON-escaped inside each page's
    __VINEXT_RSC_CHUNKS__ script, so both quote styles are rewritten."""
    url, image = SITE + page['path'], SITE + page['image']
    pairs = [('name', 'description', page['description']),
             ('property', 'og:title', page['title']),
             ('property', 'og:description', page['description']),
             ('property', 'og:url', url),
             ('property', 'og:site_name', 'Multimudia'),
             ('property', 'og:image', image),
             ('property', 'og:image:alt', page['alt']),
             ('name', 'twitter:title', page['title']),
             ('name', 'twitter:description', page['description']),
             ('name', 'twitter:image', image)]
    hits = 0
    for q in ('"', '\\"'):
        for attr, key, value in pairs:
            head = '{' + q + attr + q + ':' + q + key + q + ',' + q + 'content' + q + ':' + q
            text, n = re.subn(re.escape(head) + r'[^"\\]*' + re.escape(q),
                              lambda m, h=head, v=value, e=q: h + jesc(v) + e, text)
            hits += n
        for head in ('[' + q + '$' + q + ',' + q + 'title' + q + ',',):
            text, n = re.subn(re.escape(head) + r'(' + re.escape(q) + r'\d+' + re.escape(q) + r',\{'
                              + re.escape(q) + 'children' + re.escape(q) + ':' + re.escape(q) + r')[^"\\]*'
                              + re.escape(q),
                              lambda m, h=head, e=q: h + m.group(1) + jesc(page['title']) + e, text)
            hits += n
        canonical = '{' + q + 'rel' + q + ':' + q + 'canonical' + q + ',' + q + 'href' + q + ':' + q
        text, n = re.subn(re.escape(canonical) + r'[^"\\]*' + re.escape(q),
                          lambda m, h=canonical, e=q: h + jesc(url) + e, text)
        hits += n
    return text, hits

written = []
for name, page in PAGES.items():
    target = ROOT / name
    if not target.exists():
        continue
    html = target.read_text()
    head_end = html.index('</head>')
    head, rest = html[:head_end], html[head_end:]
    for pattern in STRIP:
        head = re.sub(pattern, '', head, flags=re.S)
    rest, _ = patch_payload(rest, page)
    target.write_text(head + head_for(page) + rest)
    written.append(name)

# Absolute URLs: a sitemap with relative locations is ignored.
(ROOT / 'robots.txt').write_text(
    'User-agent: *\nAllow: /\n'
    'Disallow: /checkout\nDisallow: /case-study-modal-preview\n'
    'Disallow: /engineering-2\nDisallow: /work-modal-preview\n\n'
    'Sitemap: ' + SITE + '/sitemap.xml\n')
urls = [p['path'] for p in PAGES.values() if p.get('index')]
(ROOT / 'sitemap.xml').write_text(
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
    ''.join('  <url><loc>' + SITE + u + '</loc></url>\n' for u in dict.fromkeys(urls)) +
    '</urlset>\n')
rsc = 0
for payload, key in (('pricing.rsc', 'pricing/index.html'), ('selected-work.rsc', 'selected-work/index.html'),
                     ('.rsc', 'index.html')):
    f = ROOT / payload
    if not f.exists():
        continue
    text, n = patch_payload(f.read_text(), PAGES[key])
    f.write_text(text)
    rsc += n
print('Wrote metadata for ' + str(len(written)) + ' pages and ' + str(rsc) +
      ' payload tags, plus robots.txt and sitemap.xml.')
