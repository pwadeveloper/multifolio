const $=id=>document.getElementById(id);
let config;
const reference=new URLSearchParams(location.search).get('reference') || new URLSearchParams(location.search).get('trxref');
function status(text,error=false){$('status').hidden=false;$('status').textContent=text;$('status').dataset.error=error;}
async function request(path,options){const response=await fetch(path,{cache:'no-store',...options});let data;try{data=await response.json();}catch{throw new Error('Checkout is temporarily unavailable. Please try again later.');}if(!response.ok)throw new Error(data.error||'Could not complete this request.');return data;}
function updatePrice(){const amount=$('currency').value==='USD'?'$350 USD':'₦450,000 NGN';$('price').textContent=amount;$('billing').textContent=config.billing==='monthly'?'Billed monthly':'One-time payment';$('consent-text').textContent=config.billing==='monthly'?`I authorize ${amount} now and every month for this five-video package until I cancel the subscription through Paystack.`:`I confirm this five-video package and the one-time payment of ${amount}.`;}
async function verify(){
 $('retry').hidden=true;status('Verifying your payment with Paystack…');
 try{const data=await request('/api/verify-payment?reference='+encodeURIComponent(reference));$('reference').hidden=false;$('reference').textContent='Payment reference: '+data.reference;
 if(data.paid){$('heading').textContent='Payment confirmed.';$('intro').textContent='Thank you. Your payment for the content package has been verified.';status('Keep your payment reference and share it with Multimudia when arranging your project brief.');$('price').textContent=data.currency==='USD'?'$350 USD':'₦450,000 NGN';$('billing').textContent=data.billing==='monthly'?'Monthly retainer':'One-time payment';}
 else{status('Your payment has not been confirmed yet. If you completed checkout, check again before making another payment.',true);$('retry').hidden=false;}
 }catch(error){status(error.message,true);$('retry').hidden=false;}
}
$('retry').onclick=verify;
$('currency').onchange=updatePrice;
$('checkout-form').onsubmit=async event=>{event.preventDefault();$('pay').disabled=true;status('Opening secure checkout…');try{const result=await request('/api/checkout',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:$('name').value,email:$('email').value,currency:$('currency').value,accepted:$('accepted').checked})});location.assign(result.url);}catch(error){status(error.message,true);$('pay').disabled=false;}};
(async()=>{if(reference){await verify();return;}try{config=await request('/api/payment-config');if(!config.enabled){status('Online payment is not open yet. Please book an intro call to discuss your project.');return;}$('checkout-form').hidden=false;$('status').hidden=true;$('currency-field').hidden=!config.currencies.includes('USD');updatePrice();}catch(error){status(error.message,true);}})();
