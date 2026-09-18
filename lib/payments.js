import {randomBytes} from 'node:crypto';
export const PACKAGE_ID = 'multimudia-five-video-v1';
export const PRICES = Object.freeze({NGN:45000000, USD:35000});
export class PaymentError extends Error {
  constructor(message, status = 400) { super(message); this.status = status; }
}
export function settings(env = process.env) {
  const billing = 'one_time';
  const currencies = ['NGN', ...(env.PAYSTACK_USD_ENABLED === 'true' ? ['USD'] : [])];
  const hasKey = /^sk_(test|live)_/.test(env.PAYSTACK_SECRET_KEY || '');
  const enabled = hasKey;
  let bookingUrl = null;
  try { const url = new URL(env.BOOKING_URL || 'https://calendar.app.google/4Z1x1rKG1f6mJqTu9'); if (url.protocol === 'https:' && !url.username && !url.password) bookingUrl = url.href; } catch {}
  return {enabled, billing, currencies, prices: PRICES, bookingUrl};
}
export async function paystack(path, payload, env = process.env, fetcher = fetch) {
  if (!/^sk_(test|live)_/.test(env.PAYSTACK_SECRET_KEY || '')) throw new PaymentError('Payments are not available yet. Please book an intro call instead.',503);
  let response, body;
  try {
    response = await fetcher('https://api.paystack.co' + path, {
      method: payload ? 'POST' : 'GET',
      headers: {Authorization: `Bearer ${env.PAYSTACK_SECRET_KEY}`, 'Content-Type':'application/json'},
      ...(payload ? {body:JSON.stringify(payload)} : {}),
      signal: AbortSignal.timeout(12000)
    });
    body = await response.json();
  } catch { throw new PaymentError('The payment provider is temporarily unavailable. Please try again.',502); }
  if (!response.ok || body.status !== true) throw new PaymentError('Paystack could not complete this request. Please try again or book an intro call.',502);
  return body.data;
}
export async function initialize(input, origin, env = process.env, fetcher = fetch) {
  const config = settings(env);
  if (!config.enabled) throw new PaymentError('Payments are not available yet. Please book an intro call instead.',503);
  const email = typeof input.email === 'string' ? input.email.trim() : '';
  const name = typeof input.name === 'string' ? input.name.trim() : '';
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || email.length > 254) throw new PaymentError('Enter a valid email address.');
  if (!name || name.length > 120) throw new PaymentError('Enter your name (up to 120 characters).');
  const currency = input.currency || 'NGN';
  if (!config.currencies.includes(currency)) throw new PaymentError('This payment currency is not enabled.');
  if (input.accepted !== true) throw new PaymentError('Please confirm the package and payment terms.');
  const amount = PRICES[currency];
  const reference = 'mf-' + randomBytes(20).toString('hex');
  const result = await paystack('/transaction/initialize', {
    email, amount, currency, reference,
    callback_url: origin + '/checkout?reference=' + reference,
    metadata: {package_id:PACKAGE_ID, customer_name:name, billing:config.billing}
  },env,fetcher);
  let redirect;
  try { redirect = new URL(result.authorization_url); } catch { throw new PaymentError('Invalid checkout response.',502); }
  if (redirect.protocol !== 'https:' || redirect.hostname !== 'checkout.paystack.com' || result.reference !== reference) throw new PaymentError('Invalid checkout response.',502);
  return {url:redirect.href,reference};
}
export async function verify(reference, env = process.env, fetcher = fetch) {
  if (!/^mf-[a-f0-9]{40}$/.test(reference || '')) throw new PaymentError('Invalid payment reference.');
  const data = await paystack('/transaction/verify/' + reference, null, env, fetcher);
  let metadata = data.metadata;
  if (typeof metadata === 'string') { try { metadata = JSON.parse(metadata); } catch { metadata = {}; } }
  const matches = data.reference === reference && metadata?.package_id === PACKAGE_ID && Object.hasOwn(PRICES,data.currency) && Number(data.amount) === PRICES[data.currency];
  if (!matches) throw new PaymentError('This transaction does not match your package. Please contact Multimudia with your reference.',409);
  return {paid:data.status === 'success',status:data.status,currency:data.currency,amount:PRICES[data.currency],reference,billing:metadata.billing};
}
export function siteOrigin(req, env = process.env) {
  let origin = env.SITE_URL;
  if (!origin && env.VERCEL_PROJECT_PRODUCTION_URL) origin = 'https://' + env.VERCEL_PROJECT_PRODUCTION_URL;
  if (!origin && env.VERCEL_URL) origin = 'https://' + env.VERCEL_URL;
  if (!origin && /^localhost:\d+$|^127\.0\.0\.1:\d+$/.test(req.headers.host || '')) origin = 'http://' + req.headers.host;
  try {
    const url = new URL(origin);
    if (url.protocol !== 'https:' && !['localhost','127.0.0.1'].includes(url.hostname)) throw new Error();
    return url.origin;
  } catch { throw new PaymentError('The checkout address is not configured.',503); }
}
export function respondError(res,error) {
  const status = error instanceof PaymentError ? error.status : 500;
  if (status >= 500) console.error('Payment request failed', {status,kind:error.name});
  return res.status(status).json({error:error instanceof PaymentError ? error.message : 'Could not complete this request. Please try again.'});
}
export function noCache(res) { res.setHeader('Cache-Control','no-store'); res.setHeader('X-Content-Type-Options','nosniff'); }
