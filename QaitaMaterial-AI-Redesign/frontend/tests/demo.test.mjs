import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import ts from 'typescript';
const source=await readFile(new URL('../src/demo.ts',import.meta.url),'utf8');
const {outputText}=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}});
const {createDemoApi}=await import('data:text/javascript;base64,'+Buffer.from(outputText).toString('base64'));
const setup=()=>{let saved=null;const storage={getItem:()=>saved,setItem:(_,v)=>{saved=v}};return {api:createDemoApi(storage),storage}};
const post=body=>({method:'POST',body:JSON.stringify(body)});
test('public demo opens with synthetic data and normalizes units',async()=>{
 const {api}=setup();assert.equal((await api('/me')).role,'factory');
 const d=await api('/dashboard');assert.equal(d.material_count,4);assert.equal(d.total_quantity_t,62);
 assert.equal(d.demo_records,4);assert.equal((await api('/ai/status')).configured,false);
});
test('local material edits persist; another browser has independent data',async()=>{
 const {api,storage}=setup();const created=await api('/materials',post({name:'Demo test',category:'metal',quantity:2,unit:'t'}));
 await api(`/materials/${created.id}`,{method:'PATCH',body:JSON.stringify({quantity:3})});
 const restored=createDemoApi(storage);assert.equal((await restored(`/materials/${created.id}`)).quantity,3);
 assert.equal((await restored('/dashboard')).material_count,5);assert.equal((await setup().api('/dashboard')).material_count,4);
 await api(`/materials/${created.id}`,{method:'DELETE'});assert.equal((await api('/dashboard')).material_count,4);
});
test('marketplace validates requests and preserves quantities and units',async()=>{
 const {api,storage}=setup();await assert.rejects(api('/requests',post({material_id:1,requested_quantity:1})),/Invalid/);
 await assert.rejects(api('/requests',post({material_id:4,requested_quantity:13000})),/Invalid/);
 const r=await api('/requests',post({material_id:4,requested_quantity:1000}));assert.equal(r.unit,'kg');
 assert.equal((await createDemoApi(storage)('/requests')).length,1);
 await assert.rejects(api('/materials/2',{method:'DELETE'}),/Access denied/);
});
test('category analysis is labeled honestly and economics computes inputs',async()=>{
 const {api}=setup();const a=await api('/materials/1/analysis');assert.equal(a.model,'Category rules (local demo)');
 assert.equal(a.recommendations[0].status,'requires_verification');assert(a.missing_information.includes('verified laboratory results'));
 const r=await api('/economy',post({quantity:10,sale_price_per_unit:100,processing_per_unit:10,transport_per_unit:5,storage_per_unit:2,other_cost:20}));
 assert.equal(r.net,810);await assert.rejects(api('/economy',post({quantity:-1})),/Invalid/);
 await assert.rejects(api('/ai/chat',post({message:'hello'})),/unavailable/);
});
test('demo remains usable without browser storage access',async()=>{
 const api=createDemoApi({getItem:()=>{throw Error('blocked')},setItem:()=>{throw Error('blocked')}});
 await api('/materials',post({name:'Memory demo',category:'slag',quantity:1,unit:'t'}));
 assert.equal((await api('/dashboard')).material_count,5);
});
