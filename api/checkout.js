import {initialize,siteOrigin,respondError,noCache,PaymentError} from '../lib/payments.js';
export default async function handler(req,res) {
  noCache(res);
  if (req.method !== 'POST') return res.status(405).json({error:'Method not allowed.'});
  try {
    const origin=siteOrigin(req);
    if (req.headers.origin !== origin) throw new PaymentError('Open checkout on the portfolio website to continue.',403);
    if (!req.headers['content-type']?.startsWith('application/json')) throw new PaymentError('Expected JSON.',415);
    if (Number(req.headers['content-length'] || 0) > 4096) throw new PaymentError('Request too large.',413);
    let body=req.body;
    if(typeof body==='string') { try { body=JSON.parse(body); } catch { throw new PaymentError('Invalid request.'); } }
    if (!body || typeof body !== 'object' || Array.isArray(body)) throw new PaymentError('Invalid request.');
    res.status(200).json(await initialize(body,origin));
  } catch(error) { respondError(res,error); }
}
