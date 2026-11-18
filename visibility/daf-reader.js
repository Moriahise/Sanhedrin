import { Catalogue } from "/catalog-data.js";

const en = document.documentElement.lang === "en";
const t = (english, hebrew) => en ? english : hebrew;
const lang = en ? "en" : "he";
const other = en ? "he" : "en";
const base = "https://moriahise.github.io/Daf-Yomi/";
const panel = document.querySelector("#study");
const dayInput = document.querySelector("#day");
const catalogue = new Catalogue("/");
const previous = document.querySelector("#previous");
const next = document.querySelector("#next");
const tractate = document.querySelector("#tractate");
const folio = document.querySelector("#folio");
const volumes = new Map();
let entries, dates, active;
const permanent = jsonSheets();
async function jsonSheets() {
  try { return new Set(await (await fetch("/learn/daf-sheets.json")).json()); }
  catch { return new Set(); }
}
const json = async url => {
  const response = await fetch(url, {cache:"no-cache"});
  if (!response.ok) throw Error("Unavailable");
  return response.json();
};
const el = (tag, text) => {
  const node = document.createElement(tag);
  if (text) node.textContent = text;
  return node;
};
function anchor(url, label) {
  const node = el("a", label);
  node.href = url;
  return node;
}
function today() {
  const parts = new Intl.DateTimeFormat("en", {timeZone:"Asia/Jerusalem", year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(new Date());
  const date = Object.fromEntries(parts.map(p => [p.type,p.value]));
  return [date.year,date.month,date.day].join("-");
}
function plain(html) {
  const template = document.createElement("template");
  template.innerHTML = html || "";
  return template.content.textContent.replace(/\s+/g," ").trim();
}
function excerpt(text, limit, focus="") {
  const at=focus ? text.toLowerCase().indexOf(focus.toLowerCase()) : -1;
  if (at>limit/2 && text.length>limit) {
    const start=Math.max(0,at-Math.floor(limit/3));
    return "…"+excerpt(text.slice(start).replace(/^\S*\s+/,""),limit);
  }
  return text.length <= limit ? text : text.slice(0,limit).replace(/\s+\S*$/,"")+"…";
}
async function lesson(url, target) {
  try {
    const response = await fetch(url);
    if (!response.ok) throw Error("Unavailable");
    const doc = new DOMParser().parseFromString(await response.text(),"text/html");
    const find = selector => doc.querySelector(selector+'[lang="'+lang+'"]')?.textContent.trim();
    const question = find(".guiding-question p");
    const body = find(".paragraph-pair p");
    if (!question || !body) throw Error("Missing text");
    const group = el("section");
    group.append(el("h3",question),el("p",body));
    const points = [...doc.querySelectorAll('section.discussion li [lang="'+lang+'"]')];
    if (points.length) {
      group.append(el("h3",t("Discuss with your chavruta","שאלות לחברותא")));
      const list=el("ol");
      for(const point of points.slice(0,4)) list.append(el("li",point.textContent.trim()));
      group.append(list);
    }
    target.replaceChildren(group);
  } catch {
    target.textContent=t("Open the full shiur below to read the study and questions.","אפשר לעיין בשיעור ובשאלות דרך הקישור לשיעור המלא.");
  }
}
let relationRequest;
async function related(slug, target) {
  try {
    relationRequest ??= json("/learn/daf-related.json").catch(error => { relationRequest=undefined; throw error; });
    const key = slug.replace(/^cycle-\d+-/,"");
    const hits = [...((await relationRequest)[key] || [])];
    hits.sort((a,b)=>Number(b[3])-Number(a[3]) || Number(b[2]===lang)-Number(a[2]===lang));
    const result = await Promise.all(hits.map(async ([id,reason,language,citation,answerIndex,focus]) => {
      const source = "/qa.html?id="+encodeURIComponent(id);
      const card = el("article"); card.className="qa-entry";
      try {
        const q = await catalogue.detail(id);
        const answer = q.answers[answerIndex] || q.answers.find(a => plain(a.html).length>=25);
        if (!answer || q.kind!=="qa") return null;
        const heading = el("h3"); heading.dir="auto";heading.lang=language;
        heading.append(anchor(source,q.title));
        const why = el("small");
        why.append(document.createTextNode(citation ? t("Cites this daf · ","מצטט את הדף · ") : t("Shared topic · ","נושא משותף · ")), el("bdi",reason));
        const answerText = el("p",excerpt(plain(answer.html),430,focus)); answerText.dir="auto"; answerText.lang=language;
        const questionText = plain(q.question_html);
        card.append(heading,why);
        if(questionText && questionText!==q.title){
          const prompt=el("p",excerpt(questionText,240));prompt.dir="auto";prompt.lang=language;card.append(prompt);
        }
        card.append(el("h4",t("From the answer","מתוך התשובה")),answerText);
        const author=answer.author||answer.owner;
        const by=typeof author==="string"?author:author?.display_name||author?.name;
        const credit=el("small",[by,q.provider,answer.license||answer.content_license||q.license].filter(Boolean).join(" · ")); credit.dir="auto";
        card.append(credit,el("br"),anchor(source,t("Read the full question and answers","לשאלה ולתשובות המלאות")));
      } catch {
        card.append(el("bdi",reason),document.createTextNode(" · "),anchor(source,t("Open the library record","לרשומה בספרייה")));
      }
      return card;
    }));
    const cards = result.filter(Boolean);
    target.replaceChildren(...(cards.length ? cards : [el("p",t("No answered record matching this daf or its theme was found in the library.","לא נמצאה בספרייה שאלה עם תשובה התואמת לדף או לנושאו."))]));
  } catch {
    target.replaceChildren(el("p",t("Library matches could not be loaded.","טעינת ההתאמות מהספרייה נכשלה.")),anchor("/",t("Open the library","לספרייה")));
  }
}
function volumeOf(row) {
  // Keep separate cycles separate if the same tractate is published twice.
  return row[0].slice(0,row[0].lastIndexOf("-"));
}
function folios(volume, selected) {
  folio.replaceChildren();
  for (const date of volumes.get(volume) || []) {
    const row=entries[date];
    folio.add(new Option((en ? row[1] : row[2])+" · "+date,date,false,date===selected));
  }
}
function show(date, push=false) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) date=today();
  active=date;dayInput.value=date;
  const url=new URL(location.href);url.searchParams.set("date",date);
  if(push && url.href!==location.href) history.pushState(null,"",url);
  const alternate=document.querySelector('nav a[hreflang="'+other+'"]');
  alternate.href="/learn/"+other+"/daf-yomi/?date="+date;
  previous.disabled=!dates.some(d=>d<date);next.disabled=!dates.some(d=>d>date);
  const row=entries[date];
  const stamp=el("time",date);stamp.dateTime=date;
  panel.replaceChildren(stamp);
  if(!row){
    document.title=t("Daf Yomi chavruta","חברותא לדף היומי")+" · Shekhina";
    tractate.value="";folio.replaceChildren();
    panel.append(el("p",t("There is no published shiur for this date in the collection.","אין באוסף שיעור שפורסם לתאריך זה.")),anchor(base+"#calendar",t("Open the Daf Yomi calendar","ללוח הדף היומי")));
    return;
  }
  const [slug,enDaf,heDaf,enTitle,heTitle]=row;
  tractate.value=volumeOf(row);folios(tractate.value,date);
  const source=base+"shiur/"+slug+"/";
  const title=en?enTitle:heTitle;
  document.title=title+" · "+t("Daf Yomi chavruta","חברותא לדף היומי")+" · Shekhina";
  panel.append(el("h2",title),el("small",en?enDaf:heDaf));
  const study=el("div",t("Loading the shiur…","השיעור בטעינה…"));
  const controls=el("p");controls.append(anchor(source,t("Full Daf Yomi shiur","שיעור הדף היומי המלא")),document.createTextNode(" · "),anchor(source+"sources/",t("Source sheet","דף מקורות")),document.createTextNode(" · "),anchor(url.href,t("Link to this daf","קישור לדף זה")));
  permanent.then(ids => {
    if (ids.has(slug)) controls.lastElementChild.href="/learn/"+lang+"/daf-yomi/"+slug+"/";
  });
  const group=el("section");group.append(el("h2",t("From the library","מתוך הספרייה")));
  const matches=el("div",t("Loading questions and answers…","השאלות והתשובות בטעינה…"));group.append(matches);
  panel.append(study,controls,group);
  // Each selection has fresh containers. Slow responses cannot overwrite a later date.
  lesson(source,study);related(slug,matches);
}
async function start(){
  entries=await json("/learn/daf-catalogue.json");dates=Object.keys(entries).sort();
  for(const date of dates){
    const row=entries[date],key=volumeOf(row);
    if(!volumes.has(key)){
      volumes.set(key,[]);
      const name=(en?row[1]:row[2]).replace(/(?: דף)? \d+$/,"");
      tractate.add(new Option(name+" · "+t("Cycle ","מחזור ")+row[0].split("-")[1],key));
    }
    volumes.get(key).push(date);
  }
  tractate.addEventListener("change",()=>show(volumes.get(tractate.value)[0],true));
  folio.addEventListener("change",()=>show(folio.value,true));
  const current=()=>new URL(location.href).searchParams.get("date")||today();
  show(current());
  document.querySelector("#dates").addEventListener("submit",e=>{e.preventDefault();show(dayInput.value,true);});
  previous.addEventListener("click",()=>show(dates.filter(d=>d<active).at(-1),true));
  next.addEventListener("click",()=>show(dates.find(d=>d>active),true));
  document.querySelector("#today").addEventListener("click",()=>show(today(),true));
  window.addEventListener("popstate",()=>show(current()));
}
start().catch(()=>{panel.textContent=t("Use the printable edition or the Daf Yomi library below.","אפשר לפתוח את המהדורה להדפסה או את ספריית הדף היומי למטה.");});
