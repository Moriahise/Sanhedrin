import { Catalogue, searchTokens, shard } from "./catalog-data.js";

export function groupsFor(query, config) {
  const stop = new Set(config.stopwords.split(/\s+/)), lookup = new Map();
  for (const group of config.groups) for (const term of group) lookup.set(term, group);
  const seen = new Set(), groups = [];
  for (let term of searchTokens(query)) {
    if (term.length < 2 || stop.has(term)) continue;
    if (!lookup.has(term) && term.length > 3 && "והשבלמכ".includes(term[0]) && lookup.has(term.slice(1))) term = term.slice(1);
    const group = lookup.get(term) || [term], key = group.join("|");
    if (!seen.has(key)) { seen.add(key); groups.push(group); }
  }
  return groups.slice(0, 24);
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
    const words = new Set(searchTokens(part)), score = groups.filter(g => g.some(t => words.has(t))).length;
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
  const score = text => { const words = new Set(searchTokens(text)); return groups.filter(g => g.some(t => words.has(t))).length; };
  answers.sort((a,b) => score(b.text) - score(a.text));
  return { id: record.id, title: record.title, provider: record.provider, language: record.language,
    url: record.url, license: record.license, author: answers[0].author, answer_id: answers[0].answer_id,
    ...excerpt(answers[0].text, groups) };
}

export async function retrieve(cat, query, config, maxSources = 6) {
  await cat.init();
  const groups = groupsFor(query, config);
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
  const ranked = [...ranks].sort((a,b) => b[1].coverage - a[1].coverage || b[1].score - a[1].score || a[0]-b[0]);
  const cards = await cat.metadata(ranked.slice(0, 80).map(([n]) => n));
  // Include both languages when each has an equally complete topic match.
  const coverage = ranked[0]?.[1].coverage || 0;
  const bilingual = ["he", "en"].map(language => cards.find(c => c.language === language && ranks.get(c.n)?.coverage === coverage)).filter(Boolean);
  const ordered = [...new Map([cards[0], ...bilingual, ...cards].filter(Boolean).map(c => [c.id,c])).values()];
  const sources = [], failures = [];
  for (let i = 0; i < ordered.length && sources.length < maxSources; i += 6) {
    const values = await Promise.allSettled(ordered.slice(i, i + 6).map(c => cat.detail(c.id)));
    for (const value of values) {
      if (value.status !== "fulfilled") { failures.push(value.reason); continue; }
      const source = sourceFrom(value.value, groups);
      if (source && sources.length < maxSources) sources.push(source);
    }
  }
  if (!sources.length && failures.length) throw failures[0];
  return { sources, groups, candidates: ranked.length, partial: failures.length > 0 };
}

export function buildRequest({questionHtml, keywords, language, profileId, useOpenai, sources}) {
  const safe = cleanEditor(questionHtml), text = plain(safe);
  if (text.length < 8 || text.length > 8000 || safe.length > 20000) throw new Error("Question must contain 8–8000 characters.");
  if (!sources.length || sources.length > 8) throw new Error("Choose 1–8 sources with saved text.");
  return {schema: 1, question_html: safe, keywords: keywords.trim(), language, profile_id: profileId, use_openai: useOpenai, source_ids: sources.map(s => s.id)};
}

export function submission(request, repository = "Moriahise/Sanhedrin") {
  const body = "<!-- sanhedrin-teshuva:v1 -->\n```json\n" + JSON.stringify(request, null, 2) + "\n```";
  const title = "[Teshuva] " + plain(request.question_html).slice(0, 90);
  const url = `https://github.com/${repository}/issues/new?title=${encodeURIComponent(title)}&body=${encodeURIComponent(body)}`;
  return {body, title, url, long: url.length > 7500, shortUrl: `https://github.com/${repository}/issues/new?title=${encodeURIComponent(title)}`};
}

export { Catalogue };
