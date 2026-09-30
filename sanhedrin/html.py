"""Shared HTML5 sanitization and Unicode search normalization."""
import html
import re
import unicodedata
from urllib.parse import urljoin,urlsplit
import bleach
from bs4 import BeautifulSoup
from markdown_it import MarkdownIt

TAGS={'p','br','strong','b','em','i','u','s','blockquote','ul','ol','li','pre','code','a','h1','h2','h3','h4','h5','h6','table','thead','tbody','tr','td','th','hr','sub','sup','details','summary','span','div'}
CLEANER=bleach.Cleaner(tags=TAGS,attributes={'a':['href','title','rel'],'*':['dir','lang'],'td':['colspan','rowspan'],'th':['colspan','rowspan']},protocols={'http','https','mailto'},strip=True,strip_comments=True)
MARKDOWN=MarkdownIt('commonmark',{'html':True,'breaks':True})

def sanitize(text,fmt='html',base_url=''):
    rendered=MARKDOWN.render(str(text or '')) if fmt=='markdown' else str(text or '')
    soup=BeautifulSoup(rendered,'html.parser')
    for node in soup.select('script,style,iframe,object,embed,template,svg,math,form,input,button,link,meta'):node.decompose()
    for a in soup.find_all('a'):
        href=str(a.get('href') or '')
        try:
            if base_url and href and not href.startswith('#'):href=urljoin(base_url,href)
            allowed=bool(href and (href.startswith('#') or urlsplit(href).scheme in {'http','https','mailto'}))
        except ValueError:allowed=False
        if allowed:a['href']=href
        else:a.attrs.pop('href',None)
        a['rel']='noopener noreferrer'
    return CLEANER.clean(str(soup))

def plain_text(text):
    soup=BeautifulSoup(str(text or ''),'html.parser')
    for node in soup.select('script,style,template,svg,math'):node.decompose()
    return re.sub(r'\s+',' ',html.unescape(soup.get_text(' ',strip=True))).strip()

def search_normalize(text):
    text=unicodedata.normalize('NFKC',str(text or '')).lower()
    return re.sub(r'[\u0591-\u05bd\u05bf-\u05c7]','',text).replace('׳',"'").replace('״','"').replace('’',"'")

def tokens(text):return re.findall(r'[^\W_]+(?:[\x27\"][^\W_]+)*',search_normalize(text),flags=re.UNICODE)
