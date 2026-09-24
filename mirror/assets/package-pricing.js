/**
 * Pricing for the "Build your own package" builder on /pricing.
 *
 * Every rate lives in RATES. Change a number there and the builder, the order
 * summary and the guardrail tests all move together. Nothing else should ever
 * hard-code a naira figure for a custom package.
 *
 * Imported by the browser (package-builder.js) and by the test suite, so it
 * stays free of DOM and Node APIs.
 */
export const RATES = Object.freeze({
  // Per-video list prices.
  shortForm: 90000,
  longForm: 180000,

  // Extras. Never discounted, never part of the batch or season maths.
  extraLanguagePerVideo: 15000,
  thumbnails: 12000,
  // The brief prices thumbnails as one flat line ("thumbnails x 12,000") while
  // the label reads "each". Flip this to charge per video instead.
  thumbnailsPerVideo: false,
  rushSurcharge: 0.35,

  // Exactly one discount ever applies: the larger of the two that qualify.
  batch: Object.freeze({rate: 0.10, minVideos: 6}),
  // minVideos on the season rate is a guardrail, not a sales rule. Without it a
  // 5-short season cart prices at 76,500 a video and undercuts Starter's
  // 90,000. See tests/package-pricing.test.mjs.
  season: Object.freeze({rate: 0.15, minVideos: 6, months: 3}),

  maxPerType: 20,

  // The packages the builder prices against.
  starter: Object.freeze({price: 450000, videos: 8}),
  growth: Object.freeze({oneTime: 800000, season: 680000, videos: 15, shortForm: 13, longForm: 2}),
  // Unused long-form allowance converts to shorts at this rate. One way only:
  // shorts never convert back, because a long-form edit is several times the work.
  swapRatio: 2,
  // What a video beyond the package costs, from the published add-on rates.
  addOns: Object.freeze({
    oneTime: Object.freeze({shortForm: 55000, longForm: 125000}),
    season: Object.freeze({shortForm: 47000, longForm: 106000}),
  }),
});

/** Whole videos only, clamped into range. Anything unparseable reads as zero. */
function count(value, max) {
  const parsed = Math.floor(Number(value));
  return Number.isFinite(parsed) ? Math.min(Math.max(parsed, 0), max) : 0;
}

export const clampCount = (value) => count(value, RATES.maxPerType);

/**
 * Price one cart.
 *
 * cart: {shorts, longForm, extraLanguage, thumbnails, rush, season}
 * In season mode every figure returned is ONE MONTH's, with seasonTotal the
 * three-month figure.
 *
 * Below 12 videos there is one route: a la carte. At 12 and above the Growth
 * package becomes a second route, and the cart is charged the lower of the two,
 * floored at the Growth price itself.
 */
export function pricePackage(cart = {}, options = {}) {
  const shorts = count(cart.shorts, RATES.maxPerType);
  const longForm = count(cart.longForm, RATES.maxPerType);
  const videos = shorts + longForm;
  const season = cart.season === true;

  // 1. Videos at list price.
  const videoSubtotal = shorts * RATES.shortForm + longForm * RATES.longForm;

  // 2. One discount on the videos only, the larger of the two that qualify.
  //    They must not stack: a 6+ video season cart gets 15%, not 25%.
  const offers = [];
  if (videos >= RATES.batch.minVideos) offers.push({rate: RATES.batch.rate, label: 'Batch rate applied'});
  if (season && videos >= RATES.season.minVideos) offers.push({rate: RATES.season.rate, label: 'Season rate applied'});
  const best = offers.reduce((a, b) => (b.rate > a.rate ? b : a), {rate: 0, label: null});
  const routeA = videoSubtotal - Math.round(videoSubtotal * best.rate);

  // 2b. Route B: the Growth base plus anything past what the package covers, at
  //     the published add-on rates. Long-form allowance the cart does not use
  //     converts to shorts at swapRatio.
  const base = season ? RATES.growth.season : RATES.growth.oneTime;
  const addOn = season ? RATES.addOns.season : RATES.addOns.oneTime;
  const coveredLongForm = Math.min(longForm, RATES.growth.longForm);
  const shortAllowance = RATES.growth.shortForm + (RATES.growth.longForm - coveredLongForm) * RATES.swapRatio;
  const extraShorts = Math.max(0, shorts - shortAllowance);
  const extraLongForm = Math.max(0, longForm - RATES.growth.longForm);
  const extraShortsAmount = extraShorts * addOn.shortForm;
  const extraLongFormAmount = extraLongForm * addOn.longForm;
  const routeB = base + extraShortsAmount + extraLongFormAmount;

  // Charge the lower route, and never less than the package itself.
  const isPackage = routeB <= routeA;
  const videosAfterDiscount = isPackage ? Math.max(routeB, base) : routeA;
  // The batch and season lines only describe route A; the package has its own.
  const discountRate = isPackage ? 0 : best.rate;
  const discountAmount = isPackage ? 0 : videoSubtotal - routeA;

  // 3. Extras sit outside both routes and outside the discount.
  const extrasSubtotal =
    (cart.extraLanguage ? RATES.extraLanguagePerVideo * videos : 0) +
    (cart.thumbnails ? RATES.thumbnails * (RATES.thumbnailsPerVideo ? videos : 1) : 0);

  // 4. Subtotal, then 5. rush as a surcharge on everything before it.
  const subtotal = videosAfterDiscount + extrasSubtotal;
  const rushAmount = cart.rush ? Math.round(subtotal * RATES.rushSurcharge) : 0;
  const total = subtotal + rushAmount;

  // One short-form edit away from a better rate, and only when it really is
  // better: for a long-form heavy cart the next video costs more, not less.
  let nudge = null;
  if (videos && shorts < RATES.maxPerType && !options.skipNudge) {
    const next = pricePackage({...cart, shorts: shorts + 1}, {skipNudge: true});
    if (next.total < total) nudge = {total: next.total, videos: next.videos, route: next.route};
  }

  return {
    nudge,
    shorts, longForm, videos, season,
    extraLanguage: cart.extraLanguage === true,
    thumbnails: cart.thumbnails === true,
    rush: cart.rush === true,
    videoSubtotal,
    discountRate,
    discountLabel: isPackage ? null : best.label,
    discountAmount,
    videosAfterDiscount,
    extrasSubtotal,
    subtotal,
    rushAmount,
    total,
    // 6. Season mode quotes a month; the season figure is that times three.
    seasonTotal: season ? total * RATES.season.months : null,
    // All-in rate, what the panel shows.
    perVideo: videos ? Math.round(total / videos) : 0,
    // Video-only rate, what the guardrails measure. Extras can only push the
    // all-in rate up, so this is the strictest floor to test against.
    videoRate: videos ? Math.round(videosAfterDiscount / videos) : 0,
    // How this cart was priced, and the parts the panel itemises.
    route: isPackage ? 'package' : 'alacarte',
    packageBase: isPackage ? base : 0,
    shortAllowance,
    extraShorts: isPackage ? extraShorts : 0,
    extraLongForm: isPackage ? extraLongForm : 0,
    extraShortsAmount: isPackage ? extraShortsAmount : 0,
    extraLongFormAmount: isPackage ? extraLongFormAmount : 0,
    // A shorts-only package cart has traded its long-form allowance away.
    swapped: isPackage && longForm === 0,
    swappedShorts: (RATES.growth.longForm) * RATES.swapRatio,
    empty: videos === 0,
  };
}

export function formatNaira(amount) {
  return '₦' + Math.round(amount).toLocaleString('en-NG');
}

const plural = (count, word) => count + ' ' + word + (count === 1 ? '' : 's');

/**
 * The line items shown in the order summary, and later sent with the payment.
 * A row with a null amount is a note, not a charge.
 */
export function lineItems(quote) {
  const items = [];
  if (quote.route === 'package') {
    items.push({label: 'Growth package, ' + RATES.growth.videos + ' videos', qty: null, amount: quote.packageBase});
    if (quote.swapped) items.push({label: 'Long-form allowance swapped for ' + quote.swappedShorts + ' extra shorts', qty: null, amount: null});
    if (quote.extraShorts) items.push({label: 'Extra short-form edits', qty: quote.extraShorts, amount: quote.extraShortsAmount});
    if (quote.extraLongForm) items.push({label: 'Extra long-form edits', qty: quote.extraLongForm, amount: quote.extraLongFormAmount});
  } else {
    if (quote.shorts) items.push({label: 'Short-form edits, 15 to 90s', qty: quote.shorts, amount: quote.shorts * RATES.shortForm});
    if (quote.longForm) items.push({label: 'Long-form edits, up to 20 min', qty: quote.longForm, amount: quote.longForm * RATES.longForm});
    if (quote.discountRate) items.push({label: quote.discountLabel + ' (' + Math.round(quote.discountRate * 100) + '% off the videos)', qty: null, amount: -quote.discountAmount});
  }
  if (quote.extraLanguage) items.push({label: 'Subtitles in an extra language', qty: quote.videos, amount: RATES.extraLanguagePerVideo * quote.videos});
  if (quote.thumbnails) items.push({label: 'Custom thumbnails', qty: RATES.thumbnailsPerVideo ? quote.videos : 1, amount: RATES.thumbnails * (RATES.thumbnailsPerVideo ? quote.videos : 1)});
  if (quote.rush) items.push({label: 'Rush 48-hour delivery, 35%', qty: null, amount: quote.rushAmount});
  return items;
}

/** One line to paste into the booking notes, itemised the way the panel is. */
export function summarise(quote) {
  let head;
  if (quote.route === 'package') {
    const base = quote.swapped
      ? 'Growth package (' + plural(quote.shortAllowance, 'short-form edit') + ', long-form swapped)'
      : 'Growth package (' + RATES.growth.videos + ' videos)';
    const beyond = [];
    if (quote.extraShorts) beyond.push(plural(quote.extraShorts, 'extra short-form edit'));
    if (quote.extraLongForm) beyond.push(plural(quote.extraLongForm, 'extra long-form edit'));
    head = beyond.length ? base + ' + ' + beyond.join(', ') : base;
  } else {
    const videos = [];
    if (quote.shorts) videos.push(plural(quote.shorts, 'short-form edit'));
    if (quote.longForm) videos.push(plural(quote.longForm, 'long-form edit'));
    head = 'Custom package — ' + videos.join(', ');
  }
  const addOns = [];
  if (quote.extraLanguage) addOns.push('extra-language subtitles');
  if (quote.thumbnails) addOns.push('custom thumbnails');
  if (quote.rush) addOns.push('rush 48-hour delivery');
  const total = quote.season
    ? formatNaira(quote.total) + ' a month, ' + formatNaira(quote.seasonTotal) + ' across the season'
    : formatNaira(quote.total);
  return head + (addOns.length ? ', ' + addOns.join(', ') : '') + '. ' +
    (quote.season ? 'Season, 3 months' : 'One-time') + '. Total ' + total + '.';
}
