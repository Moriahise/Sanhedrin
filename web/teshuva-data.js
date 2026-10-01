import { Catalogue, searchTokens, shard } from "./catalog-data.js";

export function searchText(value) {
  return String(value || "").replace(/https?:\/\/[^\s<>]+/g," ").replace(/([A-Za-z])[’'`‘](?=[A-Za-z])/g,"$1");
}
export function questionTitle(value) {
  const doc=new DOMParser().parseFromString(String(value||""),"text/html");
  for(const node of doc.querySelectorAll("p,div,br,h1,h2,h3,li"))node.after(doc.createTextNode("\n"));
  return (doc.body.textContent.split(/\n/).map(s=>s.trim()).find(Boolean)||"").slice(0,200);
}
export function titleAffinity(title, question, config) {
  const stop=new Set(config.stopwords.split(/\s+/));
  const words=text=>new Set(searchTokens(searchText(text)).filter(w=>w.length>1&&!stop.has(w)));
  const a=words(title), b=words(question), common=[...a].filter(w=>b.has(w)).length;
  return common>=Math.min(2,a.size,b.size)&&common ? common/Math.max(a.size,b.size) : 0;
}
export function groupsFor(query, config) {
  const stop = new Set(config.stopwords.split(/\s+/)), lookup = new Map();
  for (const group of config.groups) for (const term of group) lookup.set(term, group);
  const seen = new Set(), groups = [];
  for (let term of searchTokens(searchText(query))) {
    if (term.length < 2 || stop.has(term)) continue;
    for(const count of [1,2])if(!lookup.has(term)&&term.length>count+2&&[...term.slice(0,count)].every(c=>"והשבלמכ".includes(c))&&lookup.has(term.slice(count))){term=term.slice(count);break;}
    const group = lookup.get(term) || [term], key = group.join("|");
    if (!seen.has(key)) { seen.add(key); groups.push(group); }
  }
  return groups.slice(0, 24);
}

function matchingWords(text, groups) {
  const words=new Set(searchTokens(searchText(text))), wanted=new Set(groups.flat());
  for(const word of [...words])for(const count of [1,2])if(word.length>count+2&&[...word.slice(0,count)].every(c=>"והשבלמכ".includes(c))&&wanted.has(word.slice(count)))words.add(word.slice(count));
  return words;
}

export function plain(value) {
  const doc = new DOMParser().parseFromString(String(value || ""), "text/html");
  for (const node of doc.querySelectorAll("script,style,template,svg,math")) node.remove();
  for (const node of doc.querySelectorAll("p,div,li,br,h1,h2,h3,h4,blockquote,tr")) node.after(doc.createTextNode(" "));
  return doc.body.textContent.replace(/\s+/g, " ").trim();
}

export function cleanEditor(value) {
  const doc = new DOMParser().parseFromString(String(value || ""), "text/html");
  for (const node of doc.querySelectorAll("script,style,template,svg,math,iframe,object,embed,form,input,button,link,meta")) node.remove();
  const allowed = new Set(["P", "DIV", "BR", "STRONG", "B", "EM", "I", "U", "BLOCKQUOTE", "UL", "OL", "LI", "H2", "H3"]);
  for (const node of [...doc.body.querySelectorAll("*")].reverse()) {
    if (!allowed.has(node.tagName)) { node.replaceWith(...node.childNodes); continue; }
    const dir = node.getAttribute("dir");
    for (const attr of [...node.attributes]) node.removeAttribute(attr.name);
    if (["auto", "ltr", "rtl"].includes(dir)) node.setAttribute("dir", dir);
  }
  return doc.body.innerHTML;
}

export function excerpt(text, groups, limit = 2200) {
  if (text.length <= limit) return { text, excerpt: false };
  const parts = text.split(/(?<=[.!?׃])\s+/u);
  let best = 0, max = -1, offset = 0, chosen = 0;
  parts.forEach((part, i) => {
    const words = matchingWords(part,groups), score = groups.filter(g => g.some(t => words.has(t))).length;
    if (score > max) { max = score; best = i; chosen = offset; }
    offset += part.length + 1;
  });
  let start = Math.max(0, chosen - 250), end;
  if (start) start = Math.max(start, text.indexOf(" ", start) + 1);
  end = Math.min(text.length, start + limit);
  if (end < text.length) { const cut = text.lastIndexOf(" ", end); if (cut > start) end = cut; }
  return { text: (start ? "… " : "") + text.slice(start, end) + (end < text.length ? " …" : ""), excerpt: true };
}

export function sourceFrom(record, groups) {
  let answers = [...(record.answers || [])].sort((a, b) => Number(Boolean(b.accepted && b.accepted_verified)) - Number(Boolean(a.accepted && a.accepted_verified)))
    .map(a => ({ text: plain(a.html), author: a.author, answer_id: a.answer_id })).filter(a => a.text.length >= 25);
  if (!answers.length && ["article", "document"].includes(record.kind)) {
    const text = plain(record.question_html); if (text.length >= 25) answers = [{ text, author: record.author }];
  }
  if (!answers.length) return null;
  const score = text => { const words = matchingWords(text,groups); return groups.filter(g => g.some(t => words.has(t))).length; };
  answers.sort((a,b) => score(b.text) - score(a.text));
  return { id: record.id, title: record.title, provider: record.provider, language: record.language,
    url: record.url, license: record.license, author: answers[0].author, answer_id: answers[0].answer_id,
    question_context: ["article","document"].includes(record.kind)?"":plain(record.question_html).slice(0,2500),
    kind:record.kind, ...excerpt(answers.slice(0,3).map((a,i)=>`${answers.length>1?`Answer ${i+1}: `:""}${a.text}`).join("\n\n"), groups, 6000) };
}

export async function retrieve(cat, query, config, maxSources = 6, questionHtml = query) {
  await cat.init();
  const title=questionTitle(questionHtml), groups = groupsFor(query === plain(questionHtml) ? title : query, config);
  if (!groups.length) return { sources: [], groups, candidates: 0 };
  const allowedSpec = cat.manifest.facets.evidence?.available;
  const allowed = allowedSpec ? new Set(await cat.json(allowedSpec.file)) : null;
  const terms = [...new Set(groups.flat().map(t => cat.manifest.synonyms[t] || t))];
  const parts = await Promise.all([...new Set(await Promise.all(terms.map(t => shard(t))))].map(async key => [key, await cat.json(`search/${key}.json`, true)]));
  const byShard = new Map(parts), termParts = new Map(await Promise.all(terms.map(async t => [t, byShard.get(await shard(t))?.[t] || []])));
  const ranks = new Map();
  for (const group of groups) {
    const best = new Map();
    for (let term of group) {
      term = cat.manifest.synonyms[term] || term;
      const list = termParts.get(term) || [];
      const rarity = Math.log(2 + cat.manifest.total / Math.max(1, list.length / 2));
      for (let i = 0; i < list.length; i += 2) {
        const n = list[i]; if (allowed && !allowed.has(n)) continue;
        best.set(n, Math.max(best.get(n) || 0, (1 + list[i + 1]) * rarity));
      }
    }
    for (const [n, score] of best) { const old = ranks.get(n) || { coverage: 0, score: 0 }; ranks.set(n, { coverage: old.coverage + 1, score: old.score + score }); }
  }
  const ranked = [...ranks].sort((a,b) => b[1].score - a[1].score || a[0]-b[0]);
  const cards = await cat.metadata(ranked.slice(0, config.candidate_limit || 160).map(([n]) => n));
  const affinity=new Map(cards.map(c=>[c.id,titleAffinity(c.title,title,config)]));
  const ordered=cards.sort((a,b)=>(ranks.get(b.n).score+50*affinity.get(b.id))-(ranks.get(a.n).score+50*affinity.get(a.id)));
  const sources = [], failures = [];
  for (let i = 0; i < Math.min(60, ordered.length); i += 6) {
    const values = await Promise.allSettled(ordered.slice(i, i + 6).map(c => cat.detail(c.id)));
    for (const value of values) {
      if (value.status !== "fulfilled") { failures.push(value.reason); continue; }
      const source = sourceFrom(value.value, groups);
      if (source) {
        const words = matchingWords(source.text,groups), matched = groups.filter(g => g.some(t => words.has(t)));
        const titleWords=matchingWords(source.title,groups), titleScore=groups.filter(g=>g.some(t=>titleWords.has(t))).length;
        const similarity=titleAffinity(source.title,title,config);
        const lengthPenalty=1+.23*Math.log1p(Math.max(0,source.text.length-1800)/1800);
        const score=(ranks.get(value.value.n)?.score||matched.length)/lengthPenalty+2*titleScore+(similarity>=.45?50:8)*similarity;
        if (matched.length) sources.push({...source, coverage: matched.length, score, document: value.value.kind === "document"});
      }
    }
  }
  if (!sources.length && failures.length) throw failures[0];
  sources.sort((a,b) => b.score-a.score);
  const minimum = Math.max(1, Math.min(3, sources[0]?.coverage || 1) - ((sources[0]?.coverage || 0)>=3?1:0));
  const selected = sources.filter(s => s.coverage >= minimum && s.score >= .15*sources[0].score).slice(0,maxSources);
  const doc = sources.find(s => s.document && s.score >= .6*(sources[0]?.score || 0));
  if(doc && !selected.some(s => s.document)) { if(selected.length===maxSources)selected.pop();selected.push(doc); }
  return { sources:selected, groups, candidates: ranked.length, partial: failures.length > 0 };
}

export function buildRequest({questionHtml, keywords, language, profileId = "auto", useOpenai, externalResearch = false, sourceUrls = [], sources}) {
  const safe = cleanEditor(questionHtml), text = plain(safe);
  if (text.length < 8 || text.length > 8000 || safe.length > 20000) throw new Error("Question must contain 8–8000 characters.");
  if ((!sources.length && !useOpenai) || sources.length > 20) throw new Error("Choose sources or enable OpenAI research.");
  if(sourceUrls.length > 10)throw new Error("Use up to 10 source URLs.");
  for(const value of sourceUrls) { const url=new URL(value); if(url.protocol!=="https:"||url.username||url.password||url.port&&url.port!=="443")throw new Error("Use public HTTPS source URLs."); }
  if(externalResearch && !useOpenai)throw new Error("External research requires OpenAI.");
  return {schema: 1, question_html: safe, keywords: keywords.trim(), language, profile_id: profileId, use_openai: useOpenai, search_version:2, external_research:externalResearch, source_urls:sourceUrls, source_ids: sources.map(s => s.id)};
}

export function submission(request, repository = "Moriahise/Sanhedrin") {
  const body = "<!-- sanhedrin-teshuva:v1 -->\n```json\n" + JSON.stringify(request, null, 2) + "\n```";
  const title = "[Teshuva] " + plain(request.question_html).slice(0, 90);
  const url = `https://github.com/${repository}/issues/new?title=${encodeURIComponent(title)}&body=${encodeURIComponent(body)}`;
  return {body, title, url, long: url.length > 7500, shortUrl: `https://github.com/${repository}/issues/new?title=${encodeURIComponent(title)}`};
}

export { Catalogue };
