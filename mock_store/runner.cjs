const fs=require('node:fs');
const shop=require('./engine.js');
try {
  const input=JSON.parse(fs.readFileSync(0,'utf8'));
  const state=input.state||shop.setup(input.catalog);
  shop.expireDue(state);
  const result=input.action?shop.run(state,input.action):null;
  process.stdout.write(JSON.stringify({state,result:result??null}));
} catch(error) {
  process.stdout.write(JSON.stringify({error:error.message}));
}
