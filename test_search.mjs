import { readFileSync } from "node:fs";
const real = globalThis.fetch;
globalThis.fetch = (u,o) => real(new URL(u, "http://localhost:8128/").href, o);
new Function(readFileSync("qa-data.js","utf-8"))();
let pass=0, fail=0;
const ok=(n,c,d="")=>{c?pass++:fail++;console.log(`  [${c?"OK":"FEHLER"}] ${n}${d?" — "+d:""}`)};

await QAData.init();
// 5.1 Titel (englisch)
let r = await QAData.search("sugya Gemara");
ok("Titel EN: 'sugya Gemara'", r.length===1 && r[0].id==="my-1001");
// 5.2 Frage (deutsch, Sonderzeichen)
r = await QAData.search("Gänsefüßchen");
ok("Frage DE: 'Gänsefüßchen'", r.length===1 && r[0].id==="my-1003");
// 5.3 Antwort (deutsch, im Antwort-Exzerpt)
r = await QAData.search("Dappim");
ok("Antwort DE: 'Dappim' (Antwort-Exzerpt)", r.length===1 && r[0].id==="my-1001");
// 5.4 Hebräisch (Frage)
r = await QAData.search("מוקצה");
ok("Hebräisch: 'מוקצה'", r.length===1 && r[0].id==="my-1002");
// Hebräisch (Titel, Upload)
r = await QAData.search("הכוונות");
ok("Hebräisch Titel (Upload): 'הכוונות'", r.some(e=>e.id==="up-2026-0003"));
// 5.5 Kategorie-Filter allein
r = await QAData.search("", {category:"halacha"});
ok("Kategorie-Filter 'halacha'", r.length===4 && r.every(e=>e.category==="halacha"), `n=${r.length}`);
// Kategorie + Text kombiniert
r = await QAData.search("shabbat", {category:"halacha"});
ok("Kategorie+Text: 'shabbat' in halacha", r.length>=2 && r.every(e=>e.category==="halacha"), `n=${r.length}`);
// 5.6 Schlagwort/Tag
r = await QAData.search("muktzeh");
ok("Schlagwort/Tag: 'muktzeh'", r.length===1 && r[0].id==="my-1002");
// 5.7 ID-Suche: neue ID, nackte Alt-ID, alte Nummer
r = await QAData.search("my-2001");
ok("ID neu: 'my-2001'", r.length===1 && r[0].id==="my-2001");
r = await QAData.search("555");
ok("ID alt (nackt, kollidierend): '555' -> eindeutig", r.length===1 && r[0].id==="ye-555");
r = await QAData.search("n1002");
ok("ID alte Nummer: 'n1002'", r.length===1 && r[0].id==="my-1002");
// Mehrwort-UND
r = await QAData.search("temple chronology");
ok("Mehrwort-UND: 'temple chronology'", r.length===1 && r[0].id==="my-2001");
// Tiefensuche: Begriff NUR in nicht-akzeptierter Zweitantwort
r = await QAData.search("Bavli structure");
const deep = await QAData.searchDeep("structure of the Bavli");
ok("Index findet Zweitantwort-Begriff NICHT (erwartet)", r.length===0);
ok("searchDeep findet ihn im Antwort-Volltext", deep.length===1 && deep[0].id==="my-1001" && deep[0].matchedIn==="fulltext");
// Kein Treffer bleibt leer
r = await QAData.search("xyzzy-nichtvorhanden");
ok("Kein Fantasie-Treffer", r.length===0);

// Legacy-Modus (Server ohne data/questions/)
globalThis.fetch = (u,o) => real(new URL(u, "http://localhost:8129/").href, o);
new Function(readFileSync("qa-data.js","utf-8"))();
await QAData.init();
r = await QAData.search("Second Temple");
ok("Legacy-Suche EN über responsa.json", r.length===1 && r[0].id==="2001");
r = await QAData.search("לטלטל");
ok("Legacy-Suche Hebräisch", r.length===1 && r[0].id==="1002");
r = await QAData.search("", {category:"other"});
ok("Legacy-Kategorie-Filter 'other'", r.length===3, `n=${r.length}`);

console.log(`\nErgebnis: ${pass} OK, ${fail} FEHLER`);
process.exit(fail?1:0);
