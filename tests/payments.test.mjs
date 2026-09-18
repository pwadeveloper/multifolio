import {test} from 'node:test';
import assert from 'node:assert/strict';
import {initialize,verify,settings,PACKAGE_ID,siteOrigin} from '../lib/payments.js';
import checkout from '../api/checkout.js';
const env={PAYSTACK_SECRET_KEY:'sk_test_fixture',PAYSTACK_USD_ENABLED:'true'};
const input={name:'Test customer',email:'customer@example.com',currency:'NGN',accepted:true};
const ref='mf-'+'a'.repeat(40);
function ok(data){return {ok:true,json:async()=>({status:true,data})};}
test('checkout pins amount, creates reference, and uses no subscription plan',async()=>{
 let sent;
 const result=await initialize({...input,amount:1,callback_url:'https://evil.example'},'https://multifolio.example',env,async(url,options)=>{
  assert.equal(url,'https://api.paystack.co/transaction/initialize');sent=JSON.parse(options.body);return ok({authorization_url:'https://checkout.paystack.com/fixture',reference:sent.reference});
 });
 assert.equal(sent.amount,45000000);assert.equal(sent.currency,'NGN');assert.equal(sent.metadata.billing,'one_time');assert.equal(sent.plan,undefined);
 assert.match(sent.callback_url,/^https:\/\/multifolio\.example\/checkout\?reference=mf-/);assert.equal(result.url,'https://checkout.paystack.com/fixture');
});
test('USD uses fixed $350 and must be enabled explicitly',async()=>{
 await assert.rejects(()=>initialize({...input,currency:'USD'},'https://site.test',{PAYSTACK_SECRET_KEY:'sk_test_fixture'}),/not enabled/);
 await initialize({...input,currency:'USD'},'https://site.test',env,async(_,options)=>{const body=JSON.parse(options.body);assert.equal(body.amount,35000);return ok({authorization_url:'https://checkout.paystack.com/test',reference:body.reference});});
});
test('invalid email, consent and currency are rejected before contacting Paystack',async()=>{
 for(const data of [{...input,email:'bad'},{...input,accepted:false},{...input,currency:'XXX'}])await assert.rejects(()=>initialize(data,'https://site.test',env,()=>{throw Error('must not call');}));
});
test('missing key disables payments without leaking credentials',()=>{
 assert.equal(settings({}).enabled,false);assert.equal(settings(env).enabled,true);assert.equal(settings(env).billing,'one_time');assert.ok(!JSON.stringify(settings(env)).includes('sk_test'));
});
test('payment verification requires successful status and exact package, amount, currency and reference',async()=>{
 const data={status:'success',reference:ref,amount:45000000,currency:'NGN',metadata:{package_id:PACKAGE_ID,billing:'one_time'}};
 assert.equal((await verify(ref,env,async()=>ok(data))).paid,true);
 assert.equal((await verify(ref,env,async()=>ok({...data,status:'pending'}))).paid,false);
 for(const patch of [{amount:1},{currency:'EUR'},{reference:'other'},{metadata:{package_id:'other'}}])await assert.rejects(()=>verify(ref,env,async()=>ok({...data,...patch})),/does not match/);
});
test('malformed references and untrusted provider redirects are rejected',async()=>{
 await assert.rejects(()=>verify('../secret',env),/Invalid payment reference/);
 await assert.rejects(()=>initialize(input,'https://site.test',env,async(_,options)=>ok({authorization_url:'https://evil.example',reference:JSON.parse(options.body).reference})),/Invalid checkout/);
});
test('same-origin check blocks cross-site initialization',async()=>{
 const res={headers:{},setHeader(k,v){this.headers[k]=v;},status(code){this.code=code;return this;},json(data){this.data=data;}};
 await checkout({method:'POST',headers:{host:'localhost:8778',origin:'https://evil.example','content-type':'application/json'},body:input},res);
 assert.equal(res.code,403);
});
test('production origin comes from config, never an arbitrary Host header',()=>{
 assert.equal(siteOrigin({headers:{host:'evil.example'}},{SITE_URL:'https://multifolio.example'}),'https://multifolio.example');
 assert.throws(()=>siteOrigin({headers:{host:'evil.example'}},{}),/not configured/);
});
