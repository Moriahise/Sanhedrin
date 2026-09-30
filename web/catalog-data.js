export class SnapshotChanged extends Error {}
export class AmbiguousID extends Error {constructor(ids){super('Historical ID has several source-specific matches');this.ids=ids;}}
export function normalizeSearch(value){return String(value||'').normalize('NFKC').toLowerCase().replace(/[\u0591-\u05bd\u05bf-\u05c7]/g,'').replace(/[׳’]/g,"'").replace(/״/g,'"');}
export function searchTokens(value){return normalizeSearch(value).match(/[\p{L}\p{N}]+(?:['"][\p{L}\p{N}]+)*/gu)||[];}
export async function shard(value,length=3){const hash=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value));return [...new Uint8Array(hash)].map(b=>b.toString(16).padStart(2,'0')).join('').slice(0,length);}
function validContext(value){let v=String(value||'').replace(/\\/g,'/');while(v.startsWith('./'))v=v.slice(2);if(v.startsWith('/')||v.includes(':')||v.split('/').includes('..'))throw new Error('Invalid historical source path');return v;}
export class Catalogue {
  constructor(base='./'){this.base=new URL(base,location.href);this.manifest=null;this.cache=new Map();}
  async init(force=false){
    if(!this.manifest||force){const r=await fetch(new URL('catalog/manifest.json',this.base),{cache:'no-store'});if(!r.ok)throw new Error('Catalogue unavailable');const m=await r.json();
      if(m.schema!==1||!/^releases\/v1-[a-f0-9]{24}\/$/.test(m.data_base)||!Number.isSafeInteger(m.total))throw new Error('Invalid catalogue version');this.manifest=m;this.cache.clear();}
    return this.manifest;
  }
  async json(relative,optional=false){
    await this.init();if(!/^[a-zA-Z0-9_./-]+$/.test(relative)||relative.includes('..')||relative.startsWith('/'))throw new Error('Invalid catalogue path');
    const requestedRelease=this.manifest.release,url=new URL(this.manifest.data_base+relative,this.base).href;
    if(!this.cache.has(url)){
      const promise=(async()=>{const r=await fetch(url,{cache:'force-cache'});if(!r.ok){if(r.status===404){await this.init(true);if(this.manifest.release!==requestedRelease)throw new SnapshotChanged();if(optional)return null;}throw new Error('Catalogue data unavailable');}return r.json();})();
      this.cache.set(url,promise);promise.catch(()=>this.cache.delete(url));if(this.cache.size>128)this.cache.delete(this.cache.keys().next().value);
    }
    return this.cache.get(url);
  }
  async locate(id){const p=await this.json(`catalog/locator/${await shard(id,2)}.json`,true);return p?.[id]||null;}
  async aliases(id,context=''){const key=String(id)+'\0'+validContext(context);const p=await this.json(`catalog/aliases/${await shard(key)}.json`,true);return p?.[key]||[];}
  async resolve(id,context=''){await this.init();if(context){const contextual=await this.aliases(id,context);if(contextual.length)return contextual;}if(await this.locate(id))return [id];return this.aliases(id);}
  async detail(id,context=''){const ids=await this.resolve(id,context);if(!ids.length)throw new Error('Item not found');if(ids.length>1)throw new AmbiguousID(ids);const ref=await this.locate(ids[0]);if(!ref)throw new Error('Item not found');return this.json(ref.file);}
  async metadata(ordinals){await this.init();const size=this.manifest.page_size;const pages=[...new Set(ordinals.map(n=>Math.floor(n/size)))];const values=await Promise.all(pages.map(p=>this.json(`catalog/pages/${String(p).padStart(5,'0')}.json`)));const map=new Map(values.flat().map(c=>[c.n,c]));return ordinals.map(n=>map.get(n)).filter(Boolean);}
  async search(query,filters={},page=0,pageSize=48){
    await this.init();let candidates=null,scores=new Map();const terms=[...new Set(searchTokens(query).map(t=>this.manifest.synonyms[t]||t).filter(t=>t.length>=2&&!this.manifest.stopwords.includes(t)))];
    if(query.trim()&&/^(?:\d+|(?:my|ye|up|yeshiva|din|aish|chabad|doc)-[\w-]+|\w+:\d+)$/.test(query.trim())){const ids=await this.resolve(query.trim());if(ids.length){const refs=await Promise.all(ids.map(id=>this.locate(id)));candidates=refs.filter(Boolean).map(r=>r.n);scores=new Map(candidates.map(n=>[n,100]));}}
    if(candidates===null&&terms.length){const parts=await Promise.all(terms.map(async t=>(await this.json(`search/${await shard(t)}.json`,true))?.[t]||[]));const maps=parts.map(list=>{const m=new Map();for(let i=0;i<list.length;i+=2)m.set(list[i],list[i+1]);return m;}).sort((a,b)=>a.size-b.size);candidates=[...maps[0].keys()].filter(n=>maps.every(m=>m.has(n)));scores=new Map(candidates.map(n=>[n,maps.reduce((s,m)=>s+m.get(n),0)]));}
    else if(candidates===null&&query.trim())candidates=[];
    if(candidates===null)candidates=Array.from({length:this.manifest.total},(_,n)=>n);
    const sets=await Promise.all(Object.entries(filters).filter(([,v])=>v&&v!=='all').map(async([field,value])=>{const spec=this.manifest.facets[field]?.[value];return spec?new Set(await this.json(spec.file)):new Set();}));
    candidates=candidates.filter(n=>sets.every(s=>s.has(n)));if(scores.size)candidates.sort((a,b)=>(scores.get(b)||0)-(scores.get(a)||0)||a-b);
    const total=candidates.length,maxPage=Math.max(0,Math.ceil(total/pageSize)-1);page=Math.min(Math.max(0,page),maxPage);
    return {total,page,pageSize,items:await this.metadata(candidates.slice(page*pageSize,(page+1)*pageSize))};
  }
}
