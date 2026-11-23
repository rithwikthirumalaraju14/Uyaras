/* Shared simulation rules. All prices are fixture rupees; all stock belongs to this rehearsal. */
const Shop = (() => {
  const roles = ['Shopper','Owner','Catalog','Operations','Support','Analyst'];
  const levels = {catalog:['Owner','Catalog'],stock:['Owner','Catalog','Operations'],fulfil:['Owner','Operations'],returns:['Owner','Operations','Support'],rules:['Owner'],read:['Owner','Catalog','Operations','Support','Analyst']};
  const test = (condition,message) => {if(!condition) throw Error(message)};
  const integer = (value,min,max) => Number.isSafeInteger(value)&&value>=min&&value<=max;
  const label = (value,max=80) => typeof value==='string' && value.trim().length>0 && value.length<=max;
  const id = prefix => prefix+'-'+globalThis.crypto.randomUUID().slice(0,12);
  const timestamp = () => new Date().toISOString();
  function setup(data) {
    const products = structuredClone(data.products);
    const stock = {};
    products.forEach(p=>{p.published=true;p.variants.forEach(v=>{stock[v.sku]={onHand:3,reserved:0}})});
    return {products,stock,role:'Shopper',customer:null,profiles:{demo:{name:'Demo shopper',addresses:['Studio Lane, sample address']}},bags:{guest:{}},orders:[],events:[],requests:{},
      rules:[{code:'AP-DEMO',name:'Andhra Pradesh fixture',fee:30,cod:true,active:true},{code:'TG-DEMO',name:'Telangana fixture',fee:40,cod:false,active:true}],
      promos:[{code:'TEE10',percent:10,active:true}],staff:{Owner:true,Catalog:true,Operations:true,Support:true,Analyst:true}};
  }
  function can(s,area){return levels[area].includes(s.role)}
  function allowed(s,area){test(can(s,area),'This staff role does not have permission.')}
  function audit(s,action,target,detail){s.events.unshift({at:timestamp(),actor:s.role==='Shopper'?s.customer||'Guest':s.role,action,target,detail})}
  function event(o,text){o.timeline.push({at:timestamp(),text})}
  function bag(s){const key=s.customer||'guest';return s.bags[key]??=( {})}
  function lookup(s,sku){for(const p of s.products){const v=p.variants.find(x=>x.sku===sku);if(v)return {p,v}}throw Error('Unknown size or colour.')}
  function available(s,sku){const b=s.stock[sku];return b.onHand-b.reserved}
  function quote(s,a) {
    const rule=s.rules.find(r=>r.code===a.pin&&r.active);test(rule,'Choose an enabled test delivery area.');
    test(a.method==='Prepaid'||(a.method==='COD'&&rule.cod),'Payment method unavailable in this test area.');
    const lines=Object.entries(bag(s)).map(([sku,qty])=>{const {p,v}=lookup(s,sku);test(p.published&&qty<=available(s,sku),'Bag availability changed. Update the bag.');return {sku,name:p.name,colour:v.colour,size:v.size,price:p.example_price,qty}});
    test(lines.length,'Your bag is empty.');
    const subtotal=lines.reduce((sum,l)=>sum+l.qty*l.price,0);
    const code=String(a.coupon||'').trim().toUpperCase();const promo=s.promos.find(p=>p.code===code&&p.active);test(!code||promo,'Unknown or inactive demo coupon.');
    if(promo){
      const today=timestamp().slice(0,10);
      test((!promo.start||today>=promo.start)&&(!promo.end||today<=promo.end),'Demo coupon outside its validity window.');
      test(!promo.limit||s.orders.filter(o=>o.code===code&&!['Cancelled','Payment failed','Payment expired'].includes(o.status)).length<promo.limit,'Demo coupon usage limit reached.');
      test(subtotal>=(promo.minimum||0),'Demo coupon minimum spend not reached.');
    }
    if(a.method==='COD')test(!rule.codMax||subtotal<=rule.codMax,'Demo order exceeds the COD value limit.');
    const fee=rule.freeOver&&subtotal>=rule.freeOver?0:rule.fee;
    const shipping=fee+(a.method==='COD'?(rule.codFee||0):0);
    const discount=promo?Math.floor(subtotal*promo.percent/100):0;
    return {lines,subtotal,discount,shipping,tax:0,total:subtotal-discount+shipping,area:rule.name,code};
  }
  function release(s,o){if(!o.held)return;for(const l of o.lines)s.stock[l.sku].reserved-=l.qty;o.held=false}
  function pay(o,state){o.payment=state;event(o,state)}
  function run(s,a){
    const type=a.type;
    if(type==='role'){test(roles.includes(a.value)&&(a.value==='Shopper'||s.staff[a.value]),'Role unavailable.');s.role=a.value;return}
    if(type==='signin'||type==='register'){
      test(s.role==='Shopper','Choose shopper view.');const key=String(a.key||'').trim().toLowerCase();test(/^[a-z0-9-]{1,32}$/.test(key)&&!Object.prototype.hasOwnProperty.call(Object.prototype,key),'Use a short demo alias.');
      if(type==='register'){test(!Object.hasOwn(s.profiles,key)&&label(a.name),'Choose an unused alias and a display name.');s.profiles[key]={name:a.name,addresses:[]}}
      test(Object.hasOwn(s.profiles,key),'Demo account not found.');s.customer=key;const dest=bag(s);for(const [sku,q] of Object.entries(s.bags.guest)){const n=Math.min((dest[sku]||0)+q,available(s,sku));if(n)dest[sku]=n;else delete dest[sku]}s.bags.guest={};return;
    }
    if(type==='logout'){s.customer=null;s.role='Shopper';return}
    if(type==='address'||type==='removeAddress'||type==='profile'||type==='reset'){
      test(s.customer&&s.role==='Shopper','Select your demo account first.');const p=s.profiles[s.customer];
      if(type==='address'){test(label(a.value,160)&&p.addresses.length<12,'Enter a sample address (maximum 12).');if(!p.addresses.includes(a.value))p.addresses.push(a.value)}
      if(type==='removeAddress')p.addresses=p.addresses.filter(v=>v!==a.value);
      if(type==='profile'){test(label(a.value),'Enter a display name.');p.name=a.value}
      if(type==='reset')audit(s,'Mock recovery completed',s.customer,'No email sent');return;
    }
    if(type==='bag'){test(s.role==='Shopper','Select shopper mode.');const {p}=lookup(s,a.sku);test(integer(a.qty,0,99),'Invalid quantity.');const b=bag(s);if(a.qty){test(p.published&&available(s,a.sku)>=a.qty,'Insufficient simulated stock.');b[a.sku]=a.qty}else delete b[a.sku];return}
    if(type==='receipt'||type==='expire'){
      const o=s.orders.find(x=>x.id===a.id);
      test(o&&s.role==='Shopper'&&o.customer===s.customer,'Order unavailable.');
      if(type==='receipt'){
        test(label(a.event)&&a.amount===o.total&&a.currency==='INR','Payment details do not match.');
        o.receipts??=[];if(o.receipts.includes(a.event))return;
        if(o.status==='Pending payment'){o.status='Confirmed';pay(o,'Paid')}
        else if(o.status==='Payment expired'){event(o,'Late receipt queued for refund review');o.reconcile=true}
        o.receipts.push(a.event);
      } else {test(o.status==='Pending payment','Only a pending hold can expire.');release(s,o);o.status='Payment expired';pay(o,'Failed')}
      return
    }
    if(type==='order'){
      test(s.customer&&s.role==='Shopper','Select a demo account at checkout.');test(label(a.key),'Missing checkout reference.');
      const requestKey=s.customer+':'+a.key;const fingerprint=JSON.stringify([a.pin,a.method,a.coupon||'',a.address,a.outcome,a.expected]);
      if(s.requests[requestKey]){test(s.requests[requestKey].fingerprint===fingerprint,'Checkout reference already used.');return s.requests[requestKey].order}
      test(s.profiles[s.customer].addresses.includes(a.address),'Select a saved sample address.');
      const q=quote(s,a);test(a.expected===JSON.stringify(q),'Your quote changed. Review the new total.');
      const o={id:id('DEMO'),customer:s.customer,address:a.address,method:a.method,...q,status:'Confirmed',payment:'COD due',shipment:'Not created',held:true,timeline:[],refund:0,returns:[],created:timestamp(),tracking:'',remitted:false};
      for(const l of o.lines)s.stock[l.sku].reserved+=l.qty;
      event(o,'Mock order created');
      if(a.method==='Prepaid'){if(a.outcome==='pending'){o.status='Pending payment';o.expiresAt=Date.now()+15*60*1000;pay(o,'Pending')}else if(a.outcome==='fail'){release(s,o);o.status='Payment failed';pay(o,'Failed')}else pay(o,'Paid')}
      s.orders.unshift(o);s.bags[s.customer]={};s.requests[requestKey]={fingerprint,order:o.id};return o.id
    }
    if(type==='product'||type==='newProduct'){
      allowed(s,'catalog');test(label(a.name)&&integer(a.price,1,1000000),'Enter a name and a positive whole-rupee sample price.');
      if(type==='newProduct'){const src=s.products.find(p=>p.id===a.template);test(src,'Choose a template.');const p=structuredClone(src);p.artId=src.artId||src.id;p.id=id('STYLE');p.variants.forEach(v=>{v.sku=p.id+'-'+v.colour+'-'+v.size;s.stock[v.sku]={onHand:0,reserved:0}});p.name=a.name;p.example_price=a.price;p.published=false;s.products.push(p);audit(s,type,p.id,'Draft created');return}
      const p=s.products.find(p=>p.id===a.product);test(p,'Unknown product.');const before=p.name+' / ₹'+p.example_price+' / '+p.published;p.name=a.name;p.example_price=a.price;p.published=!!a.published;if(label(a.description,400))p.note=a.description;if(label(a.care,200))p.care=a.care;if(label(a.guide,240))p.guide=a.guide;audit(s,type,p.id,before+' → '+p.name+' / ₹'+p.example_price+' / '+p.published);return
    }
    if(type==='variant'){allowed(s,'catalog');const p=s.products.find(p=>p.id===a.product);test(p&&label(a.size,12)&&label(a.colour,24)&&/^#[0-9a-f]{6}$/i.test(a.hex),'Enter a size, colour and six-digit colour code.');test(/^[a-zA-Z0-9 -]+$/.test(a.size+' '+a.colour),'Use plain size and colour labels.');const sku=[p.id,a.colour,a.size].join('-').toUpperCase();test(!s.stock[sku]&&!p.variants.some(v=>v.size===a.size&&v.colour===a.colour),'Variant exists.');if(!p.colours.some(c=>c[0]===a.colour))p.colours.push([a.colour,a.hex]);p.variants.push({sku,size:a.size,colour:a.colour,stock:0});s.stock[sku]={onHand:0,reserved:0};audit(s,type,p.id,sku);return}
    if(type==='media'){allowed(s,'catalog');const p=s.products.find(p=>p.id===a.product);test(p&&label(a.asset)&&label(a.alt),'Choose a demo asset and alt text.');const assets=['M01-pine','M01-chalk','W01-terracotta','W01-ink','M02-atlantic','M02-slate','W02-cocoa','W02-moss'];test(assets.includes(a.asset),'Unknown demo asset.');p.heroAsset=a.asset;p.heroAlt=a.alt;audit(s,type,p.id,a.asset);return}
    if(type==='stock'){allowed(s,'stock');lookup(s,a.sku);const b=s.stock[a.sku];test(integer(a.delta,-999,999)&&a.delta!==0&&b.onHand+a.delta>=b.reserved&&label(a.reason),'Adjustment requires a reason and sufficient free stock.');const before=b.onHand;b.onHand+=a.delta;audit(s,'Stock adjustment',a.sku,before+' → '+b.onHand+' · '+a.reason);return}
    if(type==='rule'){allowed(s,'rules');test(/^[A-Z][A-Z0-9-]{1,19}$/.test(a.code)&&label(a.name)&&integer(a.fee,0,10000),'Enter an alphanumeric test-area code, label and valid fee.');for(const n of [a.codFee??0,a.codMax??0,a.freeOver??0])test(integer(n,0,1000000),'Invalid demo rate limit.');const r={code:a.code,name:a.name,fee:a.fee,codFee:a.codFee||0,codMax:a.codMax||0,freeOver:a.freeOver||0,cod:!!a.cod,active:!!a.active};s.rules=s.rules.filter(x=>x.code!==a.code).concat(r);audit(s,type,a.code,JSON.stringify(r));return}
    if(type==='collection'){allowed(s,'catalog');test(label(a.name)&&Array.isArray(a.ids)&&a.ids.every(k=>s.products.some(p=>p.id===k)),'Choose an existing style.');s.collections??=[];s.collections=s.collections.filter(c=>c.name!==a.name);if(a.active)s.collections.push({name:a.name,ids:[...new Set(a.ids)]});audit(s,'Collection',a.name,a.active?'Published':'Archived');return}
    if(type==='promo'){allowed(s,'rules');test(integer(a.minimum||0,0,1000000)&&integer(a.limit||0,0,100000)&&(!a.start||!a.end||a.end>=a.start),'Invalid coupon limits or dates.');test(/^[A-Z0-9]{2,16}$/.test(a.code)&&integer(a.percent,1,100),'Enter a test coupon and percentage from 1 to 100.');s.promos=s.promos.filter(p=>p.code!==a.code).concat({code:a.code,percent:a.percent,active:!!a.active,minimum:a.minimum||0,limit:a.limit||0,start:a.start||'',end:a.end||''});audit(s,type,a.code,a.percent+'% · '+!!a.active);return}
    if(type==='staff'){allowed(s,'rules');test(['Catalog','Operations','Support','Analyst'].includes(a.role),'Choose a staff role.');s.staff[a.role]=!!a.enabled;audit(s,type,a.role,a.enabled?'enabled':'disabled');return}
    const o=s.orders.find(o=>o.id===a.id);test(o,'Order not found.');
    if(type==='reconcile'){allowed(s,'fulfil');test(o.reconcile,'No late receipt to reconcile.');o.reconcile=false;o.refund=o.total;pay(o,'Refunded');audit(s,'Late payment refund',o.id,o.total);return}
    if(['retry','cancel','return','exchange'].includes(type))test(s.role==='Shopper'&&o.customer===s.customer,'Order unavailable to this shopper.');
    if(type==='retry'){test(o.status==='Payment failed'||(o.status==='Payment expired'&&!o.reconcile&&o.payment!=='Refunded'),'Retry unavailable.');test(o.lines.every(l=>available(s,l.sku)>=l.qty),'Simulated stock is unavailable.');for(const l of o.lines)s.stock[l.sku].reserved+=l.qty;o.held=true;o.status='Confirmed';pay(o,'Paid');return}
    if(type==='cancel'){test(['Confirmed','Processing','Packed','Payment failed'].includes(o.status),'Cancellation unavailable after dispatch.');release(s,o);o.status='Cancelled';if(o.payment==='Paid'){o.refund=o.total;pay(o,'Refunded')}else if(o.payment==='COD due')pay(o,'Not due');event(o,'Cancellation confirmed');return}
    if(type==='return'||type==='exchange'){test(o.status==='Delivered'&&label(a.reason),'Choose a delivered order and give a reason.');const l=o.lines.find(x=>x.sku===a.sku);test(l,'Unknown item.');const claimed=o.returns.filter(r=>r.sku===l.sku&&r.state!=='Rejected');const remaining=l.qty-claimed.reduce((sum,r)=>sum+r.qty,0);test(!claimed.some(r=>r.state!=='Closed'),'This item already has an open request.');const qty=a.qty??remaining;test(integer(qty,1,remaining),'Quantity exceeds the remaining returnable units.');o.returns.push({sku:l.sku,qty,reason:a.reason,kind:type,state:'Requested'});event(o,type+' requested · '+l.name);return}
    if(type==='review'){allowed(s,'returns');const r=o.returns.find(r=>r.sku===a.sku&&!['Closed','Rejected'].includes(r.state));test(r,'Request unavailable.');
      const next={Requested:['Approved','Rejected'],Approved:['Received'],Received:['Closed']}[r.state]||[];test(next.includes(a.next),'Invalid return transition.');
      if(a.next==='Closed'){const l=o.lines.find(l=>l.sku===r.sku);if(r.kind==='return'){test(['Paid','Collected','Partially refunded'].includes(o.payment),'Record payment collection before refund.');const returnedLines=o.returns.filter(x=>x.kind==='return'&&(x===r||x.state==='Closed'));const gross=returnedLines.reduce((n,x)=>{const item=o.lines.find(z=>z.sku===x.sku);return n+item.price*x.qty},0);o.refund=Math.min(o.total,Math.round(gross*(o.subtotal-o.discount)/o.subtotal));pay(o,o.refund===o.total?'Refunded':'Partially refunded')}
        if(a.restock)s.stock[l.sku].onHand+=r.qty;
        if(r.kind==='exchange')event(o,'Manual exchange resolution recorded')}
      r.state=a.next;event(o,r.kind+' '+a.next+' · '+r.sku);audit(s,'Return review',o.id,a.next);return}
    allowed(s,'fulfil');
    if(type==='advance'){const next={Confirmed:'Processing',Processing:'Packed',Packed:'Shipped',Shipped:'Delivered'}[o.status];test(next,'No next fulfilment step.');if(next==='Shipped'){release(s,o);for(const l of o.lines)s.stock[l.sku].onHand-=l.qty;o.tracking='SIM-'+o.id;o.shipment='In transit'}if(next==='Delivered')o.shipment='Delivered';o.status=next;event(o,next)}
    else if(type==='rto'){test(o.status==='Shipped','Shipment must be in transit.');o.status='RTO in transit';o.shipment='RTO in transit';event(o,'Delivery failed · return to origin')}
    else if(type==='receiveRto'){test(o.status==='RTO in transit','No RTO inbound.');o.status='Returned to origin';o.shipment=o.status;for(const l of o.lines)s.stock[l.sku].onHand+=l.qty;if(o.payment==='Paid'){o.refund=o.total;pay(o,'Refunded')}else pay(o,'Not due');event(o,'RTO inspected and restocked')}
    else if(type==='collect'){test(o.status==='Delivered'&&o.payment==='COD due','Collection unavailable.');pay(o,'Collected')}
    else if(type==='remit'){test(o.method==='COD'&&['Collected','Partially refunded','Refunded'].includes(o.payment)&&!o.remitted,'Remittance unavailable.');o.remitted=true;event(o,'COD remittance reconciled')}
    else throw Error('Unknown action.');
    audit(s,type,o.id,o.status+' · '+o.payment)
  }
  function expireDue(s){for(const o of s.orders)if(o.status==='Pending payment'&&Date.now()>=o.expiresAt){release(s,o);o.status='Payment expired';pay(o,'Failed')}}
  return {setup,run,quote,can,lookup,available,roles,expireDue};
})();
if(typeof module!=='undefined')module.exports=Shop;
