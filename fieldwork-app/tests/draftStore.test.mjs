import test from 'node:test';
import assert from 'node:assert/strict';
import { createDraftStore } from '../lib/draftStore.ts';

function storageFixture() {
  const values = new Map();
  return { values, storage: () => ({ getItem: key => values.get(key) ?? null, setItem: (key,value) => values.set(key,value) }) };
}

test('messages and unsent text survive leaving a route and returning', () => {
  const {storage}=storageFixture(); const store=createDraftStore(storage);
  const unsubscribe=store.subscribe('buy.log',[],()=>{});
  store.set('buy.log',[],[{kind:'you',text:'Lower under ₹400'}]);
  store.set('buy.text','','Is the pocket damaged?'); unsubscribe();
  assert.equal(store.get('buy.log',[])[0].text,'Lower under ₹400');
  assert.equal(store.get('buy.text',''),'Is the pocket damaged?');
});

test('serialized drafts survive a fresh page instance', () => {
  const {storage}=storageFixture(); const first=createDraftStore(storage);
  first.set('buy.session','','session-123');first.set('seller.tee.price','','400');
  const reloaded=createDraftStore(storage);
  assert.equal(reloaded.get('buy.session',''),'session-123');
  assert.equal(reloaded.get('seller.tee.price',''),'400');
});

test('pending response is retained after its original route unsubscribes', async () => {
  const store=createDraftStore();let calls=0;
  const unsubscribe=store.subscribe('buy.log',[],()=>calls++,false);
  unsubscribe();
  await Promise.resolve();
  store.set('buy.log',[],current=>[...current,{kind:'ai',text:'Here are the options.'}],false);
  assert.equal(calls,0);assert.equal(store.get('buy.log',[],false)[0].kind,'ai');
});

test('selected files survive navigation without being serialized', () => {
  const {values,storage}=storageFixture();const store=createDraftStore(storage);
  const file=new File(['garment evidence'],'front.jpg',{type:'image/jpeg'});
  store.set('sell.photos',[],[file],false);
  const unsubscribe=store.subscribe('sell.photos',[],()=>{},false);unsubscribe();
  assert.equal(store.get('sell.photos',[],false)[0],file);assert.equal(values.size,0);
});

test('credentials, private minimums and busy flags can remain memory only', () => {
  const {values,storage}=storageFixture();const first=createDraftStore(storage);
  first.set('reviewer.token','','test-only',false);first.set('seller.minimum','','300',false);
  first.set('buy.busy',false,true,false);
  const reloaded=createDraftStore(storage);
  assert.equal(values.size,0);assert.equal(reloaded.get('reviewer.token','',false),'');
  assert.equal(reloaded.get('buy.busy',false,false),false);
});

test('independent garments and functional updates do not overwrite each other', () => {
  const store=createDraftStore();store.set('seller.a.issues',[],['stain'],false);
  store.set('seller.b.issues',[],['hole'],false);
  store.set('seller.a.issues',[],previous=>[...previous,'tear'],false);
  assert.deepEqual(store.get('seller.a.issues',[],false),['stain','tear']);
  assert.deepEqual(store.get('seller.b.issues',[],false),['hole']);
});

test('blocked storage and corrupted storage do not discard in-memory work', () => {
  const unavailable=createDraftStore(()=>{throw new Error('storage disabled');});
  unavailable.set('text','','retained');assert.equal(unavailable.get('text',''),'retained');
  const corrupt=createDraftStore(()=>({getItem:()=>'{broken',setItem:()=>{throw new Error('quota');}}));
  assert.equal(corrupt.get('text','fallback'),'fallback');corrupt.set('text','','draft');
  assert.equal(corrupt.get('text',''),'draft');
});
