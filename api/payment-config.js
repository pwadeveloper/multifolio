import {settings,noCache} from '../lib/payments.js';
export default function handler(req,res) {
  noCache(res);
  if (req.method !== 'GET') return res.status(405).json({error:'Method not allowed.'});
  res.status(200).json(settings());
}
