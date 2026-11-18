"""Match public, answered Sanhedrin records to the published Daf Yomi editions."""
import datetime as dt
import json
import re
import unicodedata
from collections import defaultdict
from html import escape
from urllib.parse import quote
from zoneinfo import ZoneInfo

from .visibility import BASE, LANGS, link, page

STOP = set("""a an the from through about which what when where who whom why how may can could would might should does do did is are were was has have had will and nor or for not with into on in by to as at one two three first last second after before between their his its your this that there these those if all some more other another still even against under than according laws halakha mishnah gemara talmud tractate daf case question rabbi mishnah mishna rabbis law rules ruling status dispute discussion people person different same אדם אחד אחת שני שתי של את על עם אל או אי בין לא כל הוא היא הם הן מה מי כיצד האם זו זה אלו אילו אותו אלא אבל כאשר רבי רב מסכת דף דין דיני הלכה סוגיה משנה גמרא""".split())
MARKS = re.compile(r"[\u0591-\u05bd\u05bf\u05c1\u05c2\u05c4\u05c5\u05c7]")
WORDS = re.compile(r"[a-z]+|[א-ת]+")
ALIASES = {"bekhorot": ("bechoros", "bechorot", "bekhoros"), "arakhin": ("arachin", "erchin", "erachin"),
           "shabbat": ("shabbos",), "berakhot": ("berachot", "berachos"), "ketubot": ("ketubos", "kesuvos"),
           "yevamot": ("yevamos",)}


# Cross-language names for the explicitly identified subjects of these opening studies.
TOPICS = {
    "bekhorot-61": ("animal tithe", "cattle tithe", "maaser behema", "מעשר בהמה", "מעשר בהמות"),
    "arakhin-2": ("ערכי נפשות", "נדרי ערכין", "valuation vows"),
    "arakhin-3": ("מקרא מגילה", "megillah reading"),
    "arakhin-6": ("charity pledges", "נדרי צדקה", "נדר צדקה"),
}


def norm(text):
    return MARKS.sub("", unicodedata.normalize("NFKC", text).lower()).replace("־", " ")


def numeral(n):
    values = [(100,"ק"),(90,"צ"),(80,"פ"),(70,"ע"),(60,"ס"),(50,"נ"),(40,"מ"),(30,"ל"),(20,"כ"),(10,"י")]
    result = ""
    for value, letter in values:
        while n >= value:
            if n in (15,16):
                return result + ("טו" if n == 15 else "טז")
            result += letter
            n -= value
    return result + ("אבגדהוזחט"[n-1] if n else "")


def phrases(text):
    words = WORDS.findall(norm(text))
    return {" ".join((a,b)) for a,b in zip(words,words[1:])
            if len(a)>=3 and len(b)>=3 and a not in STOP and b not in STOP and a!=b}


class DafMatches:
    def __init__(self, entries):
        self.entries = entries
        self.top = defaultdict(dict)
        self.labels = {}
        self.phrase_map = defaultdict(set)
        self.references = {}
        names = set()
        for slug, en, he, title, htitle in entries.values():
            key = slug.split("-",2)[2]
            number = int(key.rsplit("-",1)[1])
            en_name = norm(en.rsplit(" ",1)[0])
            he_name = norm(he.rsplit(" ",1)[0]).removesuffix(" דף")
            self.labels[key] = en
            for name in (en_name, he_name, *ALIASES.get(en_name, ())):
                names.add(name)
                self.references[name,str(number)] = key
                if name == he_name:
                    self.references[name,numeral(number)] = key
            for phrase in phrases(title.removeprefix(en)) | phrases(htitle) | set(TOPICS.get(key,())):
                self.phrase_map[phrase].add(key)
        self.phrase_map = {k:v for k,v in self.phrase_map.items() if len(v)<=12}
        # Common English nouns such as 'Shabbat' still require an exact folio number.
        variants = "|".join(map(re.escape,sorted(names,key=len,reverse=True)))
        self.citation = re.compile(r'(?<![\w])(?:[בכלמ](?=[א-ת]))?('+variants+r')\s+(?:דף\s+)?(\d{1,3}(?:[ab])?|[א-ת]{1,3}[״"׳\x27]?[א-ת]?)(?![\w])')
        self.examples = {}

    def consider(self, card, question, answers):
        if card["kind"] != "qa" or not card["has_evidence"] or not card["answers"]:
            return
        # Search actual saved answers, not a remote-answer count or an unaudited related link.
        answer = next((v for v in answers if len(v.strip())>=25),None)
        if not answer:
            return
        matches = {}
        title_phrases = phrases(card["title"])
        for phrase in sorted(title_phrases | phrases(question[:900])):
            for key in self.phrase_map.get(phrase, ()):
                if phrase not in title_phrases and phrase not in TOPICS.get(key, ()):
                    continue
                rank = (5 if phrase in title_phrases else 1) + (5 if phrase in TOPICS.get(key,()) else 0) + min(3,len(phrase)//8)
                if rank>matches.get(key,(0,''))[0]:
                    matches[key] = (rank,phrase)
        for name,num in self.citation.findall(norm(" ".join([card["title"],question,*answers]))):
            value = num.rstrip("ab").translate(str.maketrans('', '', '״"׳\x27'))
            key = self.references.get((name,value))
            if key:
                matches[key] = (20,self.labels[key])
        for key,(score,reason) in matches.items():
            bucket = self.top[key].setdefault(card["language"], [])
            candidate = (score,card["id"],reason)
            if len(bucket)<2 or candidate>bucket[-1]:
                bucket.append(candidate)
                bucket.sort(reverse=True)
                del bucket[2:]
                self.examples[card["id"]] = (card["title"],card["language"],card["provider"])

    def write(self, out):
        folder = out/"learn"
        mapping = {k:[[pid,reason,lang,score>=20] for lang,hits in langs.items() for score,pid,reason in hits]
                   for k,langs in self.top.items()}
        (folder/"daf-related.json").write_text(json.dumps(mapping,ensure_ascii=False,separators=(",",":")))
        day = dt.datetime.now(ZoneInfo("Asia/Jerusalem")).date().isoformat()
        row = self.entries.get(day)
        for lang in LANGS:
            en = lang=="en"
            title = "Daf Yomi chavruta" if en else "חברותא לדף היומי"
            body = '<p><time>'+day+'</time></p>'
            if row:
                slug,daf_en,daf_he,en_title,he_title=row
                url="https://moriahise.github.io/Daf-Yomi/shiur/"+slug+"/"
                title=(en_title if en else he_title)
                body+='<p>'+link(url,"Read the shiur" if en else "לימוד השיעור")+' · '+link(url+"sources/","Source sheet" if en else "דף מקורות")+'</p><h2>'+("From the library" if en else "מתוך הספרייה")+'</h2>'
                hits=sorted(mapping.get(slug.split("-",2)[2],[]), key=lambda h:(not h[3],h[2]!=lang))
                for pid,reason,language,cited in hits:
                    question,_,provider=self.examples[pid]
                    body+=f'<article lang="{escape(language)}" dir="auto"><h3>'+link('/qa.html?id='+quote(pid,safe=""),question)+'</h3></article><small>'+escape(provider+' · '+reason)+'</small>'
                if not hits: body+='<p>'+("No matching answered record was found." if en else "לא נמצאה שאלה מתאימה עם תשובה במאגר.")+'</p>'
            else:
                body+=link("https://moriahise.github.io/Daf-Yomi/#calendar","Daf Yomi calendar" if en else "לוח הדף היומי")
            body+='<p>'+link(f"/learn/{lang}/daf-yomi/","Browse the collection" if en else "לכל דפי החברותא")+'</p>'
            # The interactive date picker is canonical. The fallback is a printable view.
            (folder/lang/"daf-yomi"/"today.html").write_text(page(lang,"daf-yomi",title,title,body))


def load_matches(root):
    path = root/"visibility/daf-catalogue.json"
    return DafMatches(json.loads(path.read_text())) if path.is_file() else None
