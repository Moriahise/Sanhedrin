"""Lossless normalization: public ID, provider and native ID are distinct."""
import copy
import hashlib
import json
import re
from datetime import datetime,timezone
from urllib.parse import unquote,urlsplit,urlunsplit,parse_qs

PROVIDERS={'judaism.stackexchange.com':'miyodeya','www.yeshiva.org.il':'yeshiva','yeshiva.org.il':'yeshiva','din.org.il':'din','www.din.org.il':'din','aish.com':'aish','www.aish.com':'aish','www.chabad.org':'chabad','chabad.org':'chabad'}
PREFIXES={'miyodeya':'my','yeshiva':'yeshiva','din':'din','aish':'aish','chabad':'chabad','local':'doc','upload':'up'}
CATEGORIES={'general','halacha','tanach','talmud','history','kabbalah'}
class DataError(ValueError):pass
def utcnow():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def canonical_json(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(value):return hashlib.sha256(canonical_json(value).encode()).hexdigest()

def canonical_url(value):
    value=str(value or '').strip()
    if not value:return ''
    try:p=urlsplit(value)
    except ValueError:raise DataError('Invalid original URL') from None
    if p.scheme not in {'http','https'} or not p.hostname or p.username or p.password:raise DataError('Original URL must use HTTP(S) without credentials')
    host=p.hostname.lower()
    if host.startswith('www.') and host[4:] in {'aish.com','din.org.il','chabad.org','yeshiva.org.il'}:host=host[4:]
    path=unquote(p.path).rstrip('/') or '/'
    if host=='judaism.stackexchange.com':
        m=re.match(r'/(?:questions|q)/(\d+)(?:/|$)',path)
        if m:path='/questions/'+m[1]
    return urlunsplit(('https',host,path,p.query,''))

def provider_identity(raw,default_provider=''):
    meta=raw.get('metadata') if isinstance(raw.get('metadata'),dict) else {}
    url=str(raw.get('url') or meta.get('url') or '')
    canon=canonical_url(url) if url else ''
    provider=PROVIDERS.get(urlsplit(url).hostname or '') if url else None
    declared=raw.get('provider') or meta.get('provider') or default_provider
    if provider and declared in PREFIXES and declared not in {provider,'upload'}:raise DataError('Provider conflicts with original URL')
    if not provider:provider=declared if declared in PREFIXES else 'upload'
    patterns={'miyodeya':r'/(?:questions|q)/(\d+)','yeshiva':r'/ask/(\d+)','chabad':r'/aid/(\d+)'}
    m=re.search(patterns[provider],urlsplit(url).path) if provider in patterns and url else None
    if m:native=m[1]
    elif provider=='chabad' and url and str(parse_qs(urlsplit(url).query).get('aid',[''])[0]).isdigit():native=parse_qs(urlsplit(url).query)['aid'][0]
    elif provider in {'din','aish'} and canon:native='url:'+hashlib.sha256(canon.encode()).hexdigest()[:24]
    else:
        native=str(raw.get('native_id') or raw.get('source_id') or raw.get('id') or meta.get('id') or '').strip()
        native=re.sub(r'^(?:miyodeya[_-]|my-|yeshiva-|chabad-|din-|aish-)','',native)
        if not native:raise DataError('Missing source identity')
    return provider,native,canon

def date_value(value):
    if value in (None,''):return None
    if isinstance(value,(int,float)):
        try:return datetime.fromtimestamp(value,timezone.utc).isoformat(timespec='seconds')
        except (ValueError,OverflowError):return None
    text=str(value).strip()
    try:
        if re.fullmatch(r'\d{4}',text):datetime.strptime(text,'%Y');return text
        if re.fullmatch(r'\d{4}-\d{2}',text):datetime.strptime(text,'%Y-%m');return text
        if re.fullmatch(r'\d{2}/\d{2}/\d{4}',text):return datetime.strptime(text,'%d/%m/%Y').date().isoformat()
        dt=datetime.fromisoformat(text.replace('Z','+00:00'))
        return dt.isoformat() if 'T' in text or ' ' in text else dt.date().isoformat()
    except ValueError:return None

def parse_miyodeya(content):
    body=re.split(r'##\s*Frage\s*\n',str(content or ''),maxsplit=1,flags=re.I)[-1]
    parts=re.split(r'##\s*Antworten\s*\n',body,maxsplit=1,flags=re.I);answers=[]
    if len(parts)>1:
        segments=re.split(r'\n?###\s*([^\n]*)\n',parts[1])
        if len(segments)>1:
            for i in range(1,len(segments)-1,2):
                if segments[i+1].strip():answers.append({'text':segments[i+1].strip(),'accepted':'✅' in segments[i],'accepted_verified':False,'legacy_heading':segments[i],'format':'markdown'})
        elif parts[1].strip():answers.append({'text':parts[1].strip(),'accepted':False,'accepted_verified':False,'format':'markdown'})
    return parts[0].strip(),answers

def normalize(raw,*,default_provider='',exported_at=None,public_id=None,preserve=False,allow_reference=False):
    if not isinstance(raw,dict):raise DataError('Record must be a JSON object')
    q=copy.deepcopy(raw);meta=q.get('metadata') if isinstance(q.get('metadata'),dict) else {}
    provider,native,canon=provider_identity(q,default_provider)
    title=str(q.get('title') or q.get('title_he') or q.get('title_en') or '').strip()
    question=str(q.get('question') or q.get('body') or '')
    answers=q.get('answers') if isinstance(q.get('answers'),list) else []
    if 'content' in q and provider=='miyodeya' and not question:question,answers=parse_miyodeya(q['content'])
    elif not question and 'content' in q:question=str(q['content'] or '')
    if not answers and str(q.get('answer') or '').strip():answers=[{'text':str(q['answer']),'author':meta.get('rabbi') or meta.get('author'),'accepted':False}]
    clean=[]
    for a in answers:
        if isinstance(a,str):a={'text':a}
        if not isinstance(a,dict):raise DataError('Answer must be an object or text')
        a=copy.deepcopy(a);a['text']=str(a.get('text') or a.get('body') or a.get('answer') or '')
        if not a['text'].strip():continue
        if 'is_accepted' in a:
            if not isinstance(a['is_accepted'],bool):raise DataError('is_accepted must be a boolean')
            a['accepted']=a['is_accepted'];a['accepted_verified']=True
        else:a.setdefault('accepted',False);a.setdefault('accepted_verified',False)
        a.setdefault('format','markdown' if provider=='miyodeya' else 'html')
        if a.get('answer_id') is not None:a['answer_id']=str(a['answer_id'])
        else:a.setdefault('legacy_answer_id','legacy:'+digest(a['text'])[:24])
        clean.append(a)
    technical=bool(re.fullmatch(r'(?:ERROR\s*404|Unknown(?: Question| Article)?)',title,flags=re.I))
    if not preserve:
        if technical:raise DataError('Technical error placeholder')
        if not title and not question.strip():raise DataError('Missing title and body')
        if not question.strip() and not clean and q.get('kind')!='link':
            if allow_reference and title and canon and provider not in {'upload','local'}:q['kind']='link';q['quality_status']='legacy_extraction_incomplete'
            else:raise DataError('Empty content')
    published=date_value(q.get('published_at') or meta.get('original_publication_date') or meta.get('date'))
    if not published and provider=='miyodeya':published=date_value(q.get('date'))
    saved=date_value(q.get('saved_at') or meta.get('source_saved_at') or meta.get('saved_at'))
    imported=date_value(q.get('imported_at') or exported_at or saved)
    kind=q.get('kind') or ('article' if provider in {'chabad','aish'} and (not question.strip() or meta.get('original_question_empty')) and clean else 'qa')
    q.update(provider=provider,native_id=native,canonical_url=canon,title=title,question=question,answers=clean,kind=kind,published_at=published,saved_at=saved,imported_at=imported)
    if preserve and q.get('date') and provider!='miyodeya':q.setdefault('legacy_date',q['date'])
    if preserve and technical:q['quality_status']='legacy_extraction_incomplete'
    q['format']=q.get('format') or ('markdown' if provider=='miyodeya' else 'html')
    q['category']=q.get('category') if q.get('category') in CATEGORIES else 'general'
    q.setdefault('needs_review',not bool(raw.get('category')))
    q.setdefault('category_source','legacy' if preserve else 'source' if raw.get('category') else 'unclassified')
    if not preserve and not raw.get('category'):
        from .categories import classify
        result=classify(q.get('tags') or [])
        if result:q.update(result)
    q['answer_count_local']=len(clean)
    if public_id is not None:q['id']=public_id
    elif not preserve:q['id']=PREFIXES[provider]+'-'+re.sub(r'[^\w-]','-',native,flags=re.UNICODE)
    if preserve and not q.get('id'):raise DataError('Published record lacks public ID')
    return q

def content_fingerprint(q):return digest({'question':q.get('question',''),'answers':[a.get('text','') for a in q.get('answers',[])]})

def legacy_context(src):
    src=unquote(str(src or '')).replace('\\','/')
    while src.startswith('./'):src=src[2:]
    if src.startswith('/') or '..' in src.split('/') or ':' in src:raise DataError('Invalid legacy source path')
    return src
