/**
 * "Build your own package" — the modal on desktop, the bottom sheet on mobile.
 *
 * Lives outside <main> and owns only its own dialog, so React's hydration of
 * the mirrored page can never revert it (same reason as the disclosure script).
 * All money comes from package-pricing.js; nothing here invents a figure.
 */
import {RATES, pricePackage, lineItems, summarise, formatNaira} from './package-pricing.js';

const dialog = document.getElementById('builder');
const trigger = document.querySelector('[data-build-open]');
if (dialog && trigger) start();

function start() {
  const $ = (selector, root = dialog) => root.querySelector(selector);
  const $$ = (selector, root = dialog) => Array.prototype.slice.call(root.querySelectorAll(selector));
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const isSheet = () => window.matchMedia('(max-width: 767px)').matches;

  // The cart survives a close and reopen for as long as the page is open.
  const cart = {shorts: 0, longForm: 0, extraLanguage: false, thumbnails: false, rush: false, season: false};
  const EMPTY = Object.assign({}, cart);

  const totalNode = $('[data-total]');
  const live = $('[data-live]');
  let shownTotal = 0;
  let frame = 0;
  let liveTimer = 0;

  // --- rendering -----------------------------------------------------------

  function render() {
    const quote = pricePackage(cart);

    // Steppers and extras mirror the cart, so typing, clamping and reset all
    // land back in the same place.
    $$('[data-field]').forEach((node) => {
      const field = node.dataset.field;
      if (node.matches('input[type=checkbox]')) { node.checked = cart[field] === true; return; }
      if (node.matches('input')) { if (document.activeElement !== node) node.value = String(cart[field]); return; }
      if (node.matches('button')) {
        const next = cart[field] + Number(node.dataset.delta);
        node.disabled = next < 0 || next > RATES.maxPerType;
      }
    });
    $('#build-once').checked = !cart.season;
    $('#build-season').checked = cart.season;
    $('[data-qty-head]').textContent = cart.season ? 'How many videos a month' : 'How many videos';

    $('[data-actions=build]').hidden = step !== 'build';
    paintQuote(quote);
    if (step === 'book') $('[data-summary]').textContent = summarise(quote);
    if (step === 'checkout') paintOrder(quote);
    announce(quote);
    return quote;
  }

  function paintQuote(quote) {
    animate(quote.total);

    // From 12 videos up the package route is itemised: the base, then whatever
    // the base does not cover, at the add-on rates.
    const isPackage = quote.route === 'package';
    $('[data-package]').hidden = !isPackage;
    $('[data-package-note]').hidden = !isPackage;
    if (isPackage) {
      const perMonth = quote.season ? ' a month' : '';
      const lines = ['Growth — ' + RATES.growth.videos + ' videos · ' + formatNaira(quote.packageBase) + perMonth];
      if (quote.extraShorts) lines.push(quote.extraShorts + ' extra short-form · ' + formatNaira(quote.extraShortsAmount) + perMonth);
      if (quote.extraLongForm) lines.push(quote.extraLongForm + ' extra long-form · ' + formatNaira(quote.extraLongFormAmount) + perMonth);
      let html = lines.map((text) => '<p class="build-line">' + escape(text) + '</p>').join('');
      if (quote.swapped) {
        html += '<p class="build-line build-swap">' + escape('Your ' + RATES.growth.longForm +
          ' long-form edits swapped for ' + quote.swappedShorts + ' extra shorts.') + '</p>';
      }
      $('[data-package-lines]').innerHTML = html;
    }

    // One short-form edit away from a better rate, and only when it really is.
    const nudge = $('[data-nudge]');
    nudge.hidden = !quote.nudge;
    if (quote.nudge) {
      const perMonth = quote.season ? ' a month' : '';
      nudge.textContent = quote.nudge.route === 'package'
        ? 'Add one more video and the Growth package takes over — ' + RATES.growth.videos +
          ' videos for ' + formatNaira(quote.nudge.total) + perMonth + ', which is less than you’re paying now.'
        : 'Add one more video and the batch rate kicks in — ' + quote.nudge.videos +
          ' videos for ' + formatNaira(quote.nudge.total) + perMonth + ', which is less than you’re paying now.';
    }

    const seasonMeta = $('[data-season-meta]');
    seasonMeta.hidden = !quote.season || quote.empty;
    if (quote.season && !quote.empty) {
      seasonMeta.textContent = 'a month · ' + formatNaira(quote.seasonTotal) + ' across the season';
    }
    $('[data-meta]').textContent = quote.empty
      ? 'Add at least one video to see your price.'
      : quote.videos + (quote.videos === 1 ? ' video' : ' videos') + (quote.season ? ' a month' : '') +
        ' · ≈ ' + formatNaira(quote.perVideo) + ' per video';

    const saving = $('[data-saving]');
    saving.hidden = !quote.discountRate;
    if (quote.discountRate) saving.textContent = quote.discountLabel + ' — you save ' + formatNaira(quote.discountAmount);

    $('[data-go-checkout]').disabled = quote.empty;
    $('[data-go-book]').disabled = quote.empty;
    $('[data-checkout-label]').textContent = quote.empty ? 'Checkout' : 'Checkout — ' + formatNaira(quote.total);
  }

  /** The order summary that the customer reads before paying. */
  function paintOrder(quote) {
    const rows = lineItems(quote).map((item) => row(
      item.label + (item.qty ? ' × ' + item.qty : ''),
      item.amount === null ? 'included' : (item.amount < 0 ? '− ' : '') + formatNaira(Math.abs(item.amount)),
      item.amount === null || item.amount < 0 ? ' is-credit' : ''
    ));
    rows.push(row('Billing', quote.season ? 'Season, billed monthly for 3 months' : 'One-time payment', ''));
    rows.push(row(quote.season ? 'Total a month' : 'Total', formatNaira(quote.total), ' is-total'));
    if (quote.season) rows.push(row('Across the season', formatNaira(quote.seasonTotal), ' is-total'));
    $('[data-order]').innerHTML = rows.join('');
    $('[data-season-note]').hidden = !quote.season;
    $('[data-pay-label]').textContent = quote.empty ? 'Checkout' : 'Checkout — ' + formatNaira(quote.total);
  }

  const escape = (value) => String(value).replace(/[&<>"]/g, (c) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  const row = (label, value, extra) =>
    '<div class="build-order-row' + extra + '"><span>' + escape(label) + '</span><span>' + escape(value) + '</span></div>';

  /** Count the total up so a saving registers, unless motion is turned down. */
  function animate(to) {
    cancelAnimationFrame(frame);
    const from = shownTotal;
    shownTotal = to;
    if (reduceMotion.matches || from === to) { totalNode.textContent = formatNaira(to); return; }
    const started = performance.now();
    const tick = (now) => {
      const progress = Math.min((now - started) / 280, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      totalNode.textContent = formatNaira(from + (to - from) * eased);
      if (progress < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
  }

  /** One settled sentence for screen readers, not every frame of the count-up. */
  function announce(quote) {
    clearTimeout(liveTimer);
    liveTimer = setTimeout(() => {
      live.textContent = quote.empty
        ? 'Add at least one video to see your price.'
        : summarise(quote);
    }, 350);
  }

  // --- steps ---------------------------------------------------------------

  let step = 'build';
  function goto(next) {
    step = next;
    $$('[data-pane]').forEach((pane) => { pane.hidden = pane.dataset.pane !== next; });
    $$('[data-actions]').forEach((set) => { set.hidden = set.dataset.actions !== next; });
    $('[data-reset]').hidden = next !== 'build';
    $('.builder-body').scrollTop = 0;
    render();
    const focus = $('[data-pane=' + next + '] h3, [data-pane=' + next + '] .build-summary, [data-pane=' + next + '] input');
    if (focus && next !== 'build') focus.focus({preventScroll: true});
  }

  // --- open and close ------------------------------------------------------

  let scrollLock = '';
  function open() {
    scrollLock = document.documentElement.style.overflow;
    document.documentElement.style.overflow = 'hidden';
    dialog.showModal();
    sizeToViewport();
    goto('build');
  }
  function close() { dialog.close(); }

  dialog.addEventListener('close', () => {
    document.documentElement.style.overflow = scrollLock;
    dialog.style.transform = '';
    dialog.style.maxHeight = '';
    trigger.focus({preventScroll: true});   // belt and braces; the dialog does this too
  });

  trigger.addEventListener('click', open);
  dialog.addEventListener('click', (event) => { if (event.target === dialog) close(); });
  $$('[data-close]').forEach((node) => node.addEventListener('click', close));

  // --- input ---------------------------------------------------------------

  dialog.addEventListener('click', (event) => {
    const stepper = event.target.closest('[data-delta]');
    if (!stepper) return;
    const field = stepper.dataset.field;
    cart[field] = Math.min(Math.max(cart[field] + Number(stepper.dataset.delta), 0), RATES.maxPerType);
    render();
  });

  $$('input[data-field]').forEach((input) => {
    if (input.type === 'checkbox') {
      input.addEventListener('change', () => { cart[input.dataset.field] = input.checked; render(); });
      return;
    }
    // Typed quantities: allow a half-finished value while typing, clamp on blur.
    input.addEventListener('input', () => {
      const digits = input.value.replace(/[^0-9]/g, '');
      if (digits !== input.value) input.value = digits;
      cart[input.dataset.field] = Math.min(Number(digits || 0), RATES.maxPerType);
      render();
    });
    input.addEventListener('blur', () => { input.value = String(cart[input.dataset.field]); });
    input.addEventListener('keydown', (event) => {
      const by = event.key === 'ArrowUp' ? 1 : event.key === 'ArrowDown' ? -1 : 0;
      if (!by) return;
      event.preventDefault();
      cart[input.dataset.field] = Math.min(Math.max(cart[input.dataset.field] + by, 0), RATES.maxPerType);
      input.value = String(cart[input.dataset.field]);
      render();
    });
  });

  $$('input[name=build-billing]').forEach((input) => input.addEventListener('change', () => {
    cart.season = input.id === 'build-season';   // quantities stay, the price moves
    render();
  }));

  $('[data-reset]').addEventListener('click', () => { Object.assign(cart, EMPTY); shownTotal = 0; render(); });

  // --- the Growth card ---------------------------------------------------

  $('[data-see-growth]').addEventListener('click', () => {
    const card = document.querySelector('.tier-growth');
    close();
    if (!card) return;
    card.scrollIntoView({behavior: reduceMotion.matches ? 'auto' : 'smooth', block: 'center'});
    card.classList.remove('tier-flash');
    void card.offsetWidth;                      // restart the animation on a repeat visit
    card.classList.add('tier-flash');
    setTimeout(() => card.classList.remove('tier-flash'), 1800);
  });

  // --- finishing -----------------------------------------------------------

  $('[data-go-book]').addEventListener('click', () => goto('book'));
  $('[data-go-checkout]').addEventListener('click', () => goto('checkout'));
  $$('[data-back]').forEach((node) => node.addEventListener('click', () => goto('build')));

  const apple = /Mac|iPhone|iPad|iPod/.test(navigator.platform || navigator.userAgent);
  let copyTimer = 0;

  $('[data-copy]').addEventListener('click', async (event) => {
    const button = event.currentTarget;
    const label = $('[data-copy-label]', button);
    const copied = await copy(summarise(pricePackage(cart)));
    button.toggleAttribute('data-copied', copied);
    label.textContent = copied ? 'Copied' : (apple ? 'Press ⌘C to copy' : 'Press Ctrl+C to copy');
    clearTimeout(copyTimer);
    copyTimer = setTimeout(() => {
      button.removeAttribute('data-copied');
      label.textContent = 'Copy details';
    }, 2400);
  });

  /**
   * The async clipboard is the good path but needs a secure context and
   * permission. Selecting the box and asking the document to copy needs
   * neither, and leaves the text selected to copy by hand if even that fails.
   */
  async function copy(text) {
    try { await navigator.clipboard.writeText(text); return true; } catch (error) { /* fall through */ }
    selectSummary();
    try { return document.execCommand('copy'); } catch (error) { return false; }
  }

  function selectSummary() {
    const range = document.createRange();
    range.selectNodeContents($('[data-summary]'));
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
  }

  // --- the sheet: drag to dismiss, and staying clear of the keyboard --------

  const grab = $('.builder-grab');
  let dragFrom = null;
  grab.addEventListener('pointerdown', (event) => {
    if (!isSheet()) return;
    dragFrom = event.clientY;
    grab.setPointerCapture(event.pointerId);
  });
  grab.addEventListener('pointermove', (event) => {
    if (dragFrom === null) return;
    const dy = Math.max(event.clientY - dragFrom, 0);
    dialog.style.transform = 'translateY(' + dy + 'px)';
  });
  grab.addEventListener('pointerup', (event) => {
    if (dragFrom === null) return;
    const dy = event.clientY - dragFrom;
    dragFrom = null;
    dialog.style.transform = '';
    if (dy > 90) close();
  });
  grab.addEventListener('keydown', (event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); close(); } });

  // When the on-screen keyboard opens, shrink the sheet to what is still
  // visible so the price panel and the field stay above it.
  function sizeToViewport() {
    const viewport = window.visualViewport;
    if (!viewport || !dialog.open) return;
    dialog.style.maxHeight = isSheet() ? Math.round(viewport.height * 0.92) + 'px' : '';
  }
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', sizeToViewport);
    window.visualViewport.addEventListener('scroll', sizeToViewport);
  }
  window.addEventListener('resize', sizeToViewport);

  render();
}
