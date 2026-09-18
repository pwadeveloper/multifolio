import {verify,respondError,noCache} from '../lib/payments.js';
export default async function handler(req,res) {
  noCache(res);
  if (req.method !== 'GET') return res.status(405).json({error:'Method not allowed.'});
  try { res.status(200).json(await verify(req.query.reference)); }
  catch(error) { respondError(res,error); }
}
