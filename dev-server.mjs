import http from 'node:http';
import {readFile,stat} from 'node:fs/promises';
import path from 'node:path';
import checkout from './api/checkout.js';
import config from './api/payment-config.js';
import verify from './api/verify-payment.js';
const root=path.resolve('mirror'),port=Number(process.env.PORT||8778);
const routes={'/api/checkout':checkout,'/api/payment-config':config,'/api/verify-payment':verify};
// Mirror the production redirects so retired routes do not 404 only in dev.
const redirects=new Map(JSON.parse(await readFile('vercel.json','utf8')).redirects.filter(r=>!/[(:*]/.test(r.source)).map(r=>[r.source,{to:r.destination,code:r.permanent?308:307}]));
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript','.css':'text/css','.json':'application/json','.rsc':'text/x-component; charset=utf-8','.woff2':'font/woff2','.svg':'image/svg+xml','.png':'image/png','.webp':'image/webp','.ico':'image/x-icon','.wav':'audio/wav'};
http.createServer(async(req,res)=>{
 res.setHeader('Cache-Control','no-store');res.setHeader('X-Content-Type-Options','nosniff');
 try{
 const url=new URL(req.url,'http://localhost:'+port);
 if(routes[url.pathname]){
   let body='';for await(const chunk of req){body+=chunk;if(body.length>4096){res.writeHead(413);res.end();return;}}
   req.body=body;req.query=Object.fromEntries(url.searchParams);res.status=code=>{res.statusCode=code;return res;};res.json=data=>{res.setHeader('Content-Type','application/json');res.end(JSON.stringify(data));};
   await routes[url.pathname](req,res);return;
 }
 if(!['GET','HEAD'].includes(req.method)){res.writeHead(405,{'Content-Type':'text/plain; charset=utf-8'});res.end('Method not allowed.');return;}
 const hit=redirects.get(url.pathname);
 if(hit){res.writeHead(hit.code,{Location:hit.to,'Content-Type':'text/plain; charset=utf-8'});res.end('Redirecting to '+hit.to);return;}
 if(url.pathname==='/gtag/js'){res.setHeader('Content-Type','text/javascript');res.end('window.dataLayer=window.dataLayer||[];');return;}
 let file=path.resolve(root,'.'+decodeURIComponent(url.pathname));
 if(!file.startsWith(root+path.sep)&&file!==root){res.writeHead(403);res.end();return;}
 if((await stat(file)).isDirectory())file=path.join(file,'index.html');
 const bytes=await readFile(file);res.setHeader('Content-Type',mime[path.extname(file)]||'application/octet-stream');res.end(req.method==='HEAD'?undefined:bytes);
 }catch(error){res.writeHead(error.code==='ENOENT'?404:500,{'Content-Type':'text/plain; charset=utf-8'});res.end('Page unavailable.');}
}).listen(port,'127.0.0.1',()=>console.log(`Portfolio and payment API: http://localhost:${port}`));
