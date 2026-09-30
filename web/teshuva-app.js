import { Catalogue, retrieve, plain, cleanEditor, buildRequest, submission } from "./teshuva-data.js";
const $ = id => document.getElementById(id), cat = new Catalogue();
const words = {
 en: {library:"Library",eyebrow:"A question. Sources. A considered draft.",heading:"Formulate your question",intro:"Find relevant saved answers across the Hebrew and English library. Works without an API.",question:"Your question",clear:"Clear draft",keywords:"Search words (optional)",keywordHelp:"Use specific words if the question is long. Common topics are linked across Hebrew and English.",generate:"Find a source-based answer",profile:"Presentation profile",chooseProfile:"Choose a rabbi portrait",profileHelp:"The profile accompanies the draft. Source authors are credited separately.",api:"Add an OpenAI formulation",apiHelp:"Only Moriahise can use OpenAI. Select this for your own GitHub submission; otherwise the saved sources are used.",sourceCount:"Number of sources",answer:"Source-based draft",draftNotice:"These are relevant source passages, not an independently issued ruling. Read the complete sources and check how they apply to your situation.",save:"Save in GitHub / Sanhedrin",saveHelp:"Review the prepared GitHub issue and submit it. The workflow stores the finished HTML and JSON. Public submissions require repository approval.",submission:"Prepared submission",copy:"Copy request",open:"Open GitHub submission",issueNumber:"GitHub issue number",track:"Check saved answer",archive:"Saved Teshuvot",loading:"Searching saved answer texts…",empty:"No matching saved answer text was found. Try specific search words. Link placeholders are excluded.",ready:"Library ready",error:"The library could not be loaded. Please refresh and try again.",sourceSummary:"Relevant source passages",full:"Complete saved text",original:"Original source",excerpt:"Excerpt from a longer source",none:"No Teshuvot have been saved yet.",copied:"Request copied. Open GitHub, paste it into the issue body and choose Submit new issue.",copyFailed:"Select and copy the request from the text field, then paste it into GitHub.",submitted:"On GitHub, review the request and choose Submit new issue. Return here with its issue number to check the saved answer.",long:"This question is long. Copy the request, open GitHub and paste it into the issue body.",saved:"Saved in GitHub. Publication may take a few minutes.",pending:"The workflow is processing the request, or it is waiting for repository approval. Check the issue for details.",changed:"The question changed. Generate an updated source-based answer before saving.",partial:"Some sources could not be loaded. Refresh before relying on this selection.",noProfiles:"No portraits are available in Rav yet."},
 he: {library:"הספרייה",eyebrow:"שאלה. מקורות. טיוטה לעיון.",heading:"נסחו את שאלתכם",intro:"איתור תשובות שמורות מתוך המאגר בעברית ובאנגלית. פועל גם ללא API.",question:"השאלה שלכם",clear:"ניקוי הטיוטה",keywords:"מילות חיפוש (רשות)",keywordHelp:"בשאלה ארוכה אפשר לציין מילים ממוקדות. נושאים נפוצים מקושרים בין עברית לאנגלית.",generate:"איתור תשובה מבוססת מקורות",profile:"פרופיל תצוגה",chooseProfile:"בחירת תמונת רב",profileHelp:"הפרופיל מלווה את הטיוטה. מחברי המקורות מוצגים בנפרד.",api:"הוספת ניסוח באמצעות OpenAI",apiHelp:"OpenAI זמין רק ל-Moriahise. סמנו אפשרות זו לפנייה שלכם ב-GitHub; אחרת יישמרו המקורות מהמאגר.",sourceCount:"מספר מקורות",answer:"טיוטה מבוססת מקורות",draftNotice:"אלה קטעי מקורות רלוונטיים, ולא פסק עצמאי. יש לקרוא את המקורות בשלמותם ולבדוק את התאמתם למקרה שלכם.",save:"שמירה ב-GitHub / Sanhedrin",saveHelp:"בדקו את הפנייה המוכנה ב-GitHub והגישו אותה. התהליך ישמור HTML ו-JSON. פניות ציבוריות טעונות אישור מנהל המאגר.",submission:"פנייה מוכנה",copy:"העתקת הפנייה",open:"פתיחת הפנייה ב-GitHub",issueNumber:"מספר הפנייה ב-GitHub",track:"בדיקת התשובה השמורה",archive:"תשובות שנשמרו",loading:"חיפוש בטקסט של תשובות שמורות…",empty:"לא נמצא טקסט של תשובות התואמות לחיפוש. נסו מילות חיפוש ממוקדות. קישורים ללא תוכן אינם נכללים.",ready:"המאגר מוכן",error:"לא ניתן לטעון את המאגר. רעננו ונסו שוב.",sourceSummary:"קטעי מקורות רלוונטיים",full:"הטקסט השמור המלא",original:"למקור המקורי",excerpt:"קטע ממקור ארוך יותר",none:"טרם נשמרו תשובות.",copied:"הפנייה הועתקה. פתחו GitHub, הדביקו בגוף הפנייה ובחרו Submit new issue.",copyFailed:"בחרו והעתיקו את הפנייה מהשדה, והדביקו אותה ב-GitHub.",submitted:"ב-GitHub בדקו את הפנייה ובחרו Submit new issue. חזרו לכאן עם מספר הפנייה כדי לבדוק את התשובה השמורה.",long:"השאלה ארוכה. העתיקו את הפנייה, פתחו GitHub והדביקו בגוף הפנייה.",saved:"התשובה נשמרה ב-GitHub. הפרסום עשוי להימשך כמה דקות.",pending:"התהליך מטפל בפנייה, או ממתין לאישור מנהל המאגר. בדקו את הפנייה לפרטים.",changed:"השאלה השתנתה. יש ליצור טיוטה מעודכנת לפני השמירה.",partial:"חלק מהמקורות לא נטענו. יש לרענן לפני הסתמכות על הרשימה.",noProfiles:"טרם הועלו תמונות לתיקיית Rav."}
};
let language = "en", profiles = [], config, answer = null, ready = false, generation = 0, draftLoaded = false;
const t = key => words[language][key];
function element(tag, text, cls) { const e = document.createElement(tag); if(text!==undefined)e.textContent=text; if(cls)e.className=cls; return e; }
function link(label,url) { const a=element("a",label);a.href=url;a.rel="noopener noreferrer";return a; }
function persist() { if(!draftLoaded)return;try { localStorage.setItem("sanhedrin-teshuva-draft",JSON.stringify({question:cleanEditor($("question-editor").innerHTML),keywords:$("keywords").value,profile:$("rav-select").value,language,issue:$("issue-number").value})); } catch {} }
function translate() {
 document.documentElement.lang=language;document.documentElement.dir=language==="he"?"rtl":"ltr";
 for(const node of document.querySelectorAll("[data-t]"))node.textContent=t(node.dataset.t);
 $("language").textContent=language==="he"?"English":"עברית";
 document.title="Sanhedrin · "+t("heading");
 if(answer)renderAnswer();persist();
}
function updateInput() { const count=plain($("question-editor").innerHTML).length;$("character-count").textContent=`${count} / 8000`;$("generate").disabled=!ready||count<8||count>8000;persist(); }
function invalidate() { generation++;answer=null;$("answer-panel").hidden=true;$("submission-panel").hidden=true;$("track-form").hidden=true;updateInput(); }
function profileChanged() {
 const p=profiles.find(p=>p.id===$("rav-select").value);if(!p)return;
 $("rav-image").src=p.image;$("rav-image").alt=p.name;$("rav-image").hidden=false;$("rav-name").textContent=p.name;
 if(answer)renderAnswer();persist();
}
function renderAnswer() {
 const p=profiles.find(p=>p.id===$("rav-select").value);if(!p||!answer)return;
 $("answer-image").src=p.image;$("answer-image").alt=p.name;$("answer-name").textContent=p.name;
 $("answer-question").innerHTML=cleanEditor(answer.questionHtml);
 $("answer-summary").textContent=`${t("sourceSummary")} · ${answer.sources.length}`;
 $("answer-sources").replaceChildren();
 answer.sources.forEach((s,i)=>{
   const section=element("section",undefined,"source"),title=element("h3",`[${i+1}] ${s.title}`);title.dir="auto";
   const meta=element("p",[s.provider,s.language,s.author].filter(Boolean).join(" · "),"source-meta"),quote=element("blockquote",s.text);quote.dir="auto";
   const links=element("div",undefined,"source-links");links.append(link(t("full"),`qa.html?id=${encodeURIComponent(s.id)}`));
   if(/^https?:\/\//.test(s.url||""))links.append(link(t("original"),s.url));
   section.append(title,meta,quote);if(s.excerpt)section.append(element("p",t("excerpt"),"help"));section.append(links);
   if(s.license)section.append(element("p",String(s.license),"help"));$("answer-sources").append(section);
 });
 $("answer-panel").hidden=false;
}
$("language").addEventListener("click",()=>{language=language==="en"?"he":"en";translate();archive();});
for(const button of document.querySelectorAll(".editor-toolbar button")) {
 button.addEventListener("mousedown",e=>e.preventDefault());
 button.addEventListener("click",()=>{const editor=$("question-editor");editor.focus();if(button.dataset.dir)editor.dir=button.dataset.dir;else document.execCommand(button.dataset.command,false);invalidate();});
}
$("question-editor").addEventListener("input",invalidate);
$("question-editor").addEventListener("paste",e=>{e.preventDefault();const text=e.clipboardData.getData("text/plain");document.execCommand("insertText",false,text);invalidate();});
$("question-editor").addEventListener("drop",e=>e.preventDefault());
$("keywords").addEventListener("input",invalidate);$("source-limit").addEventListener("change",invalidate);
$("clear").addEventListener("click",()=>{$("question-editor").replaceChildren();$("keywords").value="";invalidate();});
$("rav-select").addEventListener("change",profileChanged);
$("question-form").addEventListener("submit",async e=>{
 e.preventDefault();const current=++generation,questionHtml=cleanEditor($("question-editor").innerHTML),question=plain(questionHtml);
 if(question.length<8||question.length>8000||questionHtml.length>20000){$("status").textContent=t("changed");return;}
 answer=null;$("answer-panel").hidden=true;$("submission-panel").hidden=true;$("status").textContent=t("loading");$("generate").disabled=true;
 try {const result=await retrieve(cat,$("keywords").value.trim()||question,config,Number($("source-limit").value));if(current!==generation)return;
   if(!result.sources.length){$("status").textContent=t("empty");return;}
   answer={...result,questionHtml,keywords:$("keywords").value};renderAnswer();$("status").textContent=result.partial?t("partial"):`${result.sources.length} · ${t("sourceSummary")}`;
 } catch {if(current===generation)$("status").textContent=t("error");} finally {updateInput();}
});
$("save").addEventListener("click",()=>{
 try {if(!answer)throw new Error(t("changed"));const request=buildRequest({questionHtml:answer.questionHtml,keywords:answer.keywords,language,profileId:$("rav-select").value,useOpenai:$("use-openai").checked,sources:answer.sources});
   const prepared=submission(request);$("submission-body").value=prepared.body;$("open-github").href=prepared.long?prepared.shortUrl:prepared.url;$("submission-status").textContent=t(prepared.long?"long":"submitted");$("submission-panel").hidden=false;$("track-form").hidden=false;
   // The user explicitly submits the prepared issue on GitHub.
   if(!prepared.long)$("open-github").click();
 }catch(error){$("status").textContent=error.message;}
});
$("copy").addEventListener("click",async()=>{try{await navigator.clipboard.writeText($("submission-body").value);$("submission-status").textContent=t("copied");}catch{$("submission-body").focus();$("submission-body").select();$("submission-status").textContent=t("copyFailed");}});
$("track-form").addEventListener("submit",async e=>{
 e.preventDefault();const number=Number($("issue-number").value);if(!Number.isSafeInteger(number)||number<1||number>10000000)return;persist();$("track-status").textContent=t("pending");
 try {const response=await fetch(`https://api.github.com/repos/Moriahise/Sanhedrin/contents/Sanhedrin?ref=main`,{cache:"no-store"});if(response.status===404)return;if(!response.ok)throw new Error();const files=await response.json();const matches=files.filter(f=>new RegExp(`^teshuva-${number}-[a-f0-9]{12}\\.html$`).test(f.name));
   if(matches.length){$("track-status").replaceChildren(element("span",t("saved")),document.createTextNode(" "),...matches.map(f=>link(t("full"),`Sanhedrin/${encodeURIComponent(f.name)}`)));}
 }catch{$("track-status").textContent=t("error");}
});
async function archive(){try{const response=await fetch("teshuvot.json",{cache:"no-store"});if(!response.ok)throw new Error();const entries=await response.json();$("saved-list").replaceChildren();for(const e of entries){if(!/^Sanhedrin\/teshuva-\d+-[a-f0-9]{12}\.html$/.test(e.file))continue;const item=element("article");item.append(link(e.title,e.file),element("p",`${e.profile} · ${e.created_at.slice(0,10)}`,"help"));$("saved-list").append(item);}if(!entries.length)$("saved-list").textContent=t("none");}catch{$("saved-list").textContent=t("error");}}
async function init(){
 try {const draft=JSON.parse(localStorage.getItem("sanhedrin-teshuva-draft")||"null");if(draft){$("question-editor").innerHTML=cleanEditor(draft.question||"");$("keywords").value=String(draft.keywords||"").slice(0,300);language=draft.language==="he"?"he":"en";$("issue-number").value=draft.issue||"";if(draft.issue)$("track-form").hidden=false;}}
 catch{}translate();updateInput();
 try {const responses=await Promise.all([fetch("rav-profiles.json"),fetch("teshuva-search.json")]);if(responses.some(r=>!r.ok))throw new Error();[profiles,config]=await Promise.all(responses.map(r=>r.json()));
   profiles=profiles.filter(p=>/^rav-[a-f0-9]{16}$/.test(p.id)&&p.image.startsWith("Rav/")&&!p.image.includes(".."));
   for(const p of profiles){const o=element("option",p.name);o.value=p.id;$("rav-select").append(o);}const draft=JSON.parse(localStorage.getItem("sanhedrin-teshuva-draft")||"null");if(profiles.some(p=>p.id===draft?.profile))$("rav-select").value=draft.profile;
   $("rav-select").disabled=!profiles.length;draftLoaded=true;profileChanged();await cat.init();ready=Boolean(profiles.length);$("status").textContent=ready?`${t("ready")} · ${cat.manifest.total.toLocaleString()} · HE / EN`:t("noProfiles");updateInput();
 }catch{$("status").textContent=t("error");}await archive();
}
init();
