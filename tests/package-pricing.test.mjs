import test from 'node:test';
import assert from 'node:assert/strict';
import {RATES, pricePackage, lineItems, summarise, formatNaira} from '../mirror/assets/package-pricing.js';

const GROWTH_PER_VIDEO = {
  oneTime: RATES.growth.oneTime / RATES.growth.videos,   // 66,666.67
  season: RATES.growth.season / RATES.growth.videos,     // 56,666.67
};
const STARTER_PER_VIDEO = RATES.starter.price / RATES.starter.videos; // 90,000

/** Every cart the builder can produce, extras and rush included. */
function* everyCart({maxVideos = 20} = {}) {
  for (let shorts = 0; shorts <= RATES.maxPerType; shorts++) {
    for (let longForm = 0; longForm <= RATES.maxPerType; longForm++) {
      const videos = shorts + longForm;
      if (videos === 0 || videos > maxVideos) continue;
      for (const season of [false, true]) {
        for (const extraLanguage of [false, true]) {
          for (const thumbnails of [false, true]) {
            for (const rush of [false, true]) {
              yield {shorts, longForm, season, extraLanguage, thumbnails, rush};
            }
          }
        }
      }
    }
  }
}

const describe = (cart) =>
  `${cart.shorts}s+${cart.longForm}L ${cart.season ? 'season' : 'one-time'}` +
  `${cart.extraLanguage ? ' +subs' : ''}${cart.thumbnails ? ' +thumbs' : ''}${cart.rush ? ' +rush' : ''}`;

// --- Guardrails ------------------------------------------------------------
// videoRate is the video-only rate. Extras and rush can only push the all-in
// rate up, so measuring the video rate is the strictest form of each floor.

test('guardrail: no cart of 5 videos or fewer prices below Starter at 90,000 a video', () => {
  let checked = 0;
  for (const cart of everyCart({maxVideos: 5})) {
    const quote = pricePackage(cart);
    assert.ok(quote.videoRate >= STARTER_PER_VIDEO,
      `${describe(cart)} priced at ${quote.videoRate} a video, under Starter's ${STARTER_PER_VIDEO}`);
    checked++;
  }
  assert.ok(checked > 0);
});

test('guardrail: no cart of 11 videos or fewer beats Growth per video, in either mode', () => {
  for (const cart of everyCart({maxVideos: 11})) {
    const quote = pricePackage(cart);
    const floor = cart.season ? GROWTH_PER_VIDEO.season : GROWTH_PER_VIDEO.oneTime;
    assert.ok(quote.videoRate > floor,
      `${describe(cart)} priced at ${quote.videoRate} a video, at or under Growth's ${Math.round(floor)}`);
  }
});

test('guardrail: season carts under 12 videos are never cheaper per video than the Growth season', () => {
  for (const cart of everyCart({maxVideos: 11})) {
    if (!cart.season) continue;
    const quote = pricePackage(cart);
    assert.ok(quote.videoRate >= 57000, `${describe(cart)} priced at ${quote.videoRate} a video, under 57,000`);
    assert.ok(quote.videoRate > GROWTH_PER_VIDEO.season, `${describe(cart)} undercuts the Growth season rate`);
  }
});

test('guardrail: the cheapest possible rate in each mode, under 12 videos', () => {
  let cheapest = {oneTime: Infinity, season: Infinity};
  for (const cart of everyCart({maxVideos: 11})) {
    const quote = pricePackage(cart);
    const mode = cart.season ? 'season' : 'oneTime';
    cheapest[mode] = Math.min(cheapest[mode], quote.videoRate);
  }
  // Shorts-only at the batch rate, and shorts-only at the season rate.
  assert.equal(cheapest.oneTime, 81000);
  assert.equal(cheapest.season, 76500);
});

// --- Discounts -------------------------------------------------------------

test('batch and season never stack: a 6+ video season cart gets 15%, not 25%', () => {
  const quote = pricePackage({shorts: 6, season: true});
  assert.equal(quote.discountRate, 0.15);
  assert.equal(quote.discountLabel, 'Season rate applied');
  assert.equal(quote.videoSubtotal, 540000);
  assert.equal(quote.discountAmount, 81000);
  assert.equal(quote.total, 459000);
});

test('batch alone at 6 videos one-time', () => {
  const quote = pricePackage({shorts: 6});
  assert.equal(quote.discountRate, 0.10);
  assert.equal(quote.discountLabel, 'Batch rate applied');
  assert.equal(quote.total, 486000);
});

test('no discount below the 6-video threshold, in either mode', () => {
  for (let videos = 1; videos <= 5; videos++) {
    assert.equal(pricePackage({shorts: videos}).discountRate, 0);
    assert.equal(pricePackage({shorts: videos, season: true}).discountRate, 0);
  }
});

test('the discount never touches extras or rush', () => {
  const plain = pricePackage({shorts: 6});
  const withExtras = pricePackage({shorts: 6, extraLanguage: true, thumbnails: true});
  // 6 videos x 15,000 subtitles + 12,000 thumbnails, all at full price.
  assert.equal(withExtras.extrasSubtotal, 90000 + 12000);
  assert.equal(withExtras.total - plain.total, 102000);
  assert.equal(withExtras.discountAmount, plain.discountAmount);
});

test('rush is 35% applied last, over the discounted videos plus extras', () => {
  const quote = pricePackage({shorts: 6, extraLanguage: true, rush: true});
  assert.equal(quote.subtotal, 486000 + 90000);
  assert.equal(quote.rushAmount, Math.round(576000 * 0.35));
  assert.equal(quote.total, 576000 + 201600);
});

// --- Modes and shapes ------------------------------------------------------

test('season mode quotes a month and a season total', () => {
  const quote = pricePackage({shorts: 6, longForm: 2, season: true});
  assert.equal(quote.total, 765000);
  assert.equal(quote.seasonTotal, 2295000);
});

test('one-time mode has no season total', () => {
  assert.equal(pricePackage({shorts: 3}).seasonTotal, null);
});

test('shorts-only, long-form-only and mixed carts all price', () => {
  assert.equal(pricePackage({shorts: 4}).total, 360000);
  assert.equal(pricePackage({longForm: 3}).total, 540000);
  assert.equal(pricePackage({shorts: 4, longForm: 1}).total, 540000);
});

test('switching billing keeps quantities and re-prices', () => {
  const cart = {shorts: 8, longForm: 1};
  const once = pricePackage(cart);
  const season = pricePackage({...cart, season: true});
  assert.equal(once.videos, season.videos);
  assert.equal(once.discountRate, 0.10);
  assert.equal(season.discountRate, 0.15);
});

// --- Handover --------------------------------------------------------------

test('12+ carts are charged the lower of the two routes', () => {
  assert.equal(pricePackage({shorts: 11}).route, 'alacarte');
  // Shorts are cheaper through the package.
  assert.equal(pricePackage({shorts: 12}).route, 'package');
  assert.equal(pricePackage({shorts: 12}).total, RATES.growth.oneTime);
  // Long-form only is cheaper a la carte one-time, and through the package in a
  // season, because the season add-on rate undercuts the 15% discount.
  assert.equal(pricePackage({longForm: 12}).route, 'alacarte');
  assert.equal(pricePackage({longForm: 12}).total, 1944000);
  assert.equal(pricePackage({longForm: 12, season: true}).route, 'package');
  assert.equal(pricePackage({longForm: 12, season: true}).total, 1740000);
});

test('14 shorts is exactly the Growth price, with the long-form swapped out', () => {
  const once = pricePackage({shorts: 14});
  assert.equal(once.total, RATES.growth.oneTime);
  assert.equal(once.extraShorts, 0);
  assert.equal(once.extraLongForm, 0);
  assert.equal(once.swapped, true);
  assert.equal(once.shortAllowance, 14);
  assert.equal(pricePackage({shorts: 14, season: true}).total, RATES.growth.season);
});

test('unused long-form allowance converts, and only one way', () => {
  assert.equal(pricePackage({shorts: 14}).shortAllowance, 14);            // 0 long-form used
  assert.equal(pricePackage({shorts: 12, longForm: 1}).shortAllowance, 12); // 1 used
  assert.equal(pricePackage({shorts: 10, longForm: 2}).shortAllowance, 10); // both used
  // Shorts never buy long-form: 20 shorts still pays full price for each long.
  assert.equal(pricePackage({shorts: 20, longForm: 3}).extraLongForm, 1);
});

test('videos past the package price at the published add-on rates', () => {
  const once = pricePackage({shorts: 16, longForm: 2});
  assert.equal(once.extraShorts, 6);
  assert.equal(once.extraShortsAmount, 6 * RATES.addOns.oneTime.shortForm);
  assert.equal(once.total, RATES.growth.oneTime + 330000);
  const season = pricePackage({shorts: 16, longForm: 2, season: true});
  assert.equal(season.extraShortsAmount, 6 * RATES.addOns.season.shortForm);
  assert.equal(season.total, RATES.growth.season + 282000);
});

test('the maximum cart prices through the package', () => {
  assert.equal(pricePackage({shorts: 20, longForm: 20}).total, 3600000);
  assert.equal(pricePackage({shorts: 20, longForm: 20, season: true}).total, 3058000);
});

test('no 12+ cart prices below the Growth floor', () => {
  for (const cart of everyCart()) {
    if (cart.shorts + cart.longForm < RATES.packageVideos) continue;
    const quote = pricePackage(cart);
    const floor = cart.season ? RATES.growth.season : RATES.growth.oneTime;
    assert.ok(quote.videosAfterDiscount >= floor, `${describe(cart)} priced videos at ${quote.videosAfterDiscount}, under the ${floor} floor`);
    assert.ok(quote.total >= floor, `${describe(cart)} totalled ${quote.total}, under the ${floor} floor`);
  }
});

test('adding a video only ever lowers the total at a threshold', () => {
  // Two thresholds unlock a better rate, so the cart one video short of each can
  // cost more than the cart that crosses it. 6 is the batch discount, which has
  // behaved this way since the builder shipped; 12 is the package taking over.
  const drops = {};
  for (const cart of everyCart()) {
    const quote = pricePackage(cart);
    for (const field of ['shorts', 'longForm']) {
      if (cart[field] >= RATES.maxPerType) continue;
      const bigger = pricePackage({...cart, [field]: cart[field] + 1});
      if (bigger.total >= quote.total) continue;
      assert.ok(quote.videos === 5 || quote.videos === RATES.packageVideos - 1,
        `${describe(cart)} at ${quote.total} drops to ${bigger.total} on one more ${field}, away from a threshold`);
      drops[quote.videos] = (drops[quote.videos] || 0) + 1;
    }
  }
  assert.deepEqual(Object.keys(drops).sort(), ['11', '5']);
  assert.ok(drops[5] > 0 && drops[11] > 0);
});

test('the 11-video nudge only appears when the 12th video actually costs less', () => {
  // Shorts-heavy: the package takes over at exactly the Growth price.
  const shortsHeavy = pricePackage({shorts: 11});
  assert.equal(shortsHeavy.nudge.total, RATES.growth.oneTime);
  assert.equal(pricePackage({shorts: 9, longForm: 2}).nudge.total, RATES.growth.oneTime);
  // Long-form heavy: a 12th video costs more, so there is nothing to nudge about.
  assert.equal(pricePackage({longForm: 11}).nudge, null);
  assert.equal(pricePackage({shorts: 1, longForm: 10}).nudge, null);
  // And the nudge never appears away from 11 videos.
  assert.equal(pricePackage({shorts: 10}).nudge, null);
  assert.equal(pricePackage({shorts: 12}).nudge, null);
});

test('every nudge it shows is true', () => {
  for (const cart of everyCart({maxVideos: 11})) {
    const quote = pricePackage(cart);
    if (quote.videos !== 11 || !quote.nudge) continue;
    assert.ok(quote.nudge.total < quote.total, `${describe(cart)} nudges to a higher price`);
  }
});

// --- Input handling --------------------------------------------------------

test('quantities are clamped to 0 and the per-type maximum', () => {
  assert.equal(pricePackage({shorts: -5}).shorts, 0);
  assert.equal(pricePackage({shorts: 99}).shorts, RATES.maxPerType);
  assert.equal(pricePackage({shorts: 3.9}).shorts, 3);
  assert.equal(pricePackage({shorts: 'abc'}).shorts, 0);
  assert.equal(pricePackage({shorts: ''}).shorts, 0);
  assert.equal(pricePackage({shorts: null}).shorts, 0);
});

test('an empty cart is empty and free', () => {
  const quote = pricePackage({});
  assert.equal(quote.empty, true);
  assert.equal(quote.total, 0);
  assert.equal(quote.perVideo, 0);
});

test('a single video is a valid cart', () => {
  const quote = pricePackage({shorts: 1});
  assert.equal(quote.empty, false);
  assert.equal(quote.total, 90000);
});

// --- Output ----------------------------------------------------------------

test('naira is formatted with the symbol and separators', () => {
  assert.equal(formatNaira(2040000), '₦2,040,000');
  assert.equal(formatNaira(90000), '₦90,000');
});

test('the booking summary reads as one pasteable line', () => {
  const quote = pricePackage({shorts: 6, longForm: 2, extraLanguage: true});
  assert.equal(summarise(quote),
    'Custom package — 6 short-form edits, 2 long-form edits, extra-language subtitles. One-time. Total ₦930,000.');
});

test('the season summary states the monthly and season figures', () => {
  const line = summarise(pricePackage({shorts: 6, season: true}));
  assert.match(line, /Season, 3 months/);
  assert.match(line, /₦459,000 a month, ₦1,377,000 across the season/);
});

test('line items carry the discount as a negative line', () => {
  const items = lineItems(pricePackage({shorts: 6, longForm: 2, season: true, rush: true}));
  const discount = items.find((item) => item.amount < 0);
  assert.equal(discount.amount, -135000);
  assert.match(discount.label, /Season rate applied \(15% off the videos\)/);
  assert.ok(items.some((item) => /Rush/.test(item.label)));
});
