// Isolated browser-only demonstration. No real users, credentials, or API requests.
type Material = {
  id:number; company_id:number; name:string; category:string; quantity:number; unit:'t'|'kg';
  description:string; chemical_properties:string; hazard_class:string; lab_verified:boolean;
  price_per_unit:number|null; status:string; is_demo:boolean;
};
type Request = {id:number; material_id:number; requested_quantity:number; unit:string; status:string; message:string};
type State = {materials:Material[]; requests:Request[]; nextMaterial:number; nextRequest:number};
const KEY='qm_public_demo_v1';
const samples:Material[] = [
  ['Металл сынықтары','metal',10,1],['Металлургиялық қож','slag',25,2],
  ['Гипс','gypsum',15,2],['Минералдық материал','mineral',12000,2],
].map(([name,category,quantity,company_id],i)=>({
  id:i+1, company_id:Number(company_id), name:String(name), category:String(category), quantity:Number(quantity),
  unit:i===3?'kg':'t', description:'Демонстрациялық материал / Демонстрационный материал / Synthetic demo material',
  chemical_properties:'', hazard_class:'unknown', lab_verified:false, price_per_unit:null,
  status:'insufficient_data', is_demo:true,
}));

export function createDemoApi(storage:Pick<Storage,'getItem'|'setItem'>) {
  let state:State;
  try {
    const saved=JSON.parse(storage.getItem(KEY)||'null');
    if (!saved || !Array.isArray(saved.materials) || !Array.isArray(saved.requests) ||
        !Number.isInteger(saved.nextMaterial) || !Number.isInteger(saved.nextRequest)) throw Error();
    state=saved;
  } catch {state={materials:samples.map(m=>({...m})),requests:[],nextMaterial:5,nextRequest:1};}
  const save=()=>{try {storage.setItem(KEY,JSON.stringify(state));} catch {/* In-memory demo remains usable if storage is disabled. */}};
  return async (path:string,options:RequestInit={}):Promise<unknown> => {
    const url=new URL(path,'https://demo.invalid'); const route=url.pathname; const method=options.method||'GET';
    const body=JSON.parse(String(options.body||'{}'));
    if(route==='/me') return {id:1,name:'Demo',email:'',role:'factory',company_id:1};
    if(route==='/dashboard') {
      const categories:Record<string,number>={};
      for(const m of state.materials) categories[m.category]=(categories[m.category]||0)+m.quantity*(m.unit==='kg'?.001:1);
      return {material_count:state.materials.length,total_quantity_t:Object.values(categories).reduce((a,b)=>a+b,0),
        request_count:state.requests.length,category_quantities:categories,demo_records:state.materials.length,note:'Local demonstration only'};
    }
    if(route==='/materials' && method==='GET') {
      const offset=Number(url.searchParams.get('offset')||0),limit=Number(url.searchParams.get('limit')||100);
      return state.materials.slice().sort((a,b)=>b.id-a.id).slice(offset,offset+limit).map(m=>({...m}));
    }
    if(route==='/materials' && method==='POST') {
      if(!body.name?.trim() || !body.category || !(body.quantity>0) || !['t','kg'].includes(body.unit)) throw Error('Invalid material');
      const m:Material={...samples[0],...body,id:state.nextMaterial++,company_id:1,is_demo:true};
      state.materials.push(m);save();return {...m};
    }
    const match=route.match(/^\/materials\/(\d+)(\/analysis)?$/);
    if(match) {
      const m=state.materials.find(m=>m.id===Number(match[1]));if(!m) throw Error('Material not found');
      if(match[2]) {
        const missing=[];
        if(!m.chemical_properties.trim())missing.push('chemical composition and impurities');
        if(['unknown','','неизвестен'].includes(m.hazard_class.toLowerCase()))missing.push('hazard classification');
        if(!m.lab_verified)missing.push('verified laboratory results');
        if(m.category==='phosphogypsum'||/фосф|phosph/i.test(m.name))missing.push('radiological screening','applicable regulatory review');
        const pathways:Record<string,string[]>={
          metal:['Metal recycling after sorting'],scrap:['Metal recycling after sorting'],slag:['Aggregate processing'],
          gypsum:['Construction gypsum products (subject to testing)','Industrial mineral filler (subject to testing)'],
          phosphogypsum:['Construction gypsum products (subject to testing)','Industrial mineral filler (subject to testing)'],
          mineral:['Industrial mineral filler (subject to testing)'],
        };
        return {material_id:m.id,verification_status:'requires_verification',missing_information:missing,
          recommendations:(pathways[m.category]||[]).map(use_case=>({use_case,matching_score:0,status:'requires_verification',reason:'Local category rule; verification required'})),
          warning:'Demonstration only; independent verification required',model:'Category rules (local demo)'};
      }
      if(method==='GET')return {...m};
      if(m.company_id!==1)throw Error('Access denied');
      if(method==='PATCH') {
        if(body.quantity!==undefined && !(body.quantity>0))throw Error('Invalid quantity');
        if(state.requests.some(r=>r.material_id===m.id) && ['quantity','unit'].some(k=>k in body && body[k]!==m[k as 'quantity'|'unit']))throw Error('Material has related requests');
        const {id,company_id,is_demo,...fields}=body;Object.assign(m,fields);save();return {...m};
      }
      if(method==='DELETE') {
        if(state.requests.some(r=>r.material_id===m.id))throw Error('Material has related requests');
        state.materials=state.materials.filter(row=>row.id!==m.id);save();return {deleted:true};
      }
    }
    if(route==='/requests') {
      if(method==='GET')return state.requests.map(r=>({...r}));
      const m=state.materials.find(m=>m.id===body.material_id);
      if(!m||m.company_id===1||!(body.requested_quantity>0)||body.requested_quantity>m.quantity)throw Error('Invalid request');
      const r:Request={id:state.nextRequest++,material_id:m.id,requested_quantity:body.requested_quantity,unit:m.unit,status:'new',message:body.message||''};
      state.requests.push(r);save();return {...r};
    }
    if(route==='/economy') {
      const names=['quantity','sale_price_per_unit','processing_per_unit','transport_per_unit','storage_per_unit','other_cost'];
      if(names.some(k=>!Number.isFinite(body[k])||body[k]<0))throw Error('Invalid economic inputs');
      const revenue=body.quantity*body.sale_price_per_unit,processing=body.quantity*body.processing_per_unit,
        transport=body.quantity*body.transport_per_unit,storageCost=body.quantity*body.storage_per_unit;
      return {revenue,processing,transport,storage:storageCost,other:body.other_cost,
        net:revenue-processing-transport-storageCost-body.other_cost,formula:'Q×P − Q×Processing − Q×Transport − Q×Storage − Other',status:'scenario_estimate'};
    }
    if(route==='/ai/status')return {configured:false};
    if(route==='/ai/history')return method==='DELETE'?{deleted:0}:[];
    throw Error('This feature is unavailable in the local demo');
  };
}
let instance:ReturnType<typeof createDemoApi>|undefined;
export function demoApi(path:string,options:RequestInit={}) {
  if(!instance) {
    let storage:Pick<Storage,'getItem'|'setItem'>;
    try {storage=window.localStorage;} catch {storage={getItem:()=>null,setItem:()=>{}};}
    instance=createDemoApi(storage);
  }
  return instance(path,options);
}
