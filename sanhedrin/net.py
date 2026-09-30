"""Bounded HTTPS transport: allowlisted redirects, robots, retries and quotas."""
import gzip
import io
import json
import time
import urllib.error
import urllib.request
import urllib.robotparser
from datetime import datetime,timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit,urlunsplit
from .model import DataError

USER_AGENT='SanhedrinCollector/1.0 (+https://github.com/Moriahise/Sanhedrin)'
MAX_BYTES=12_000_000
class FetchError(RuntimeError):pass
class Deferred(FetchError):pass
class Response:
    def __init__(self,body,headers,url):self.body=body;self.headers=headers;self.url=url
    def json(self):
        try:return json.loads(self.body)
        except (ValueError,UnicodeError):raise FetchError('Invalid JSON response') from None
    def text(self):return self.body.decode('utf-8-sig',errors='replace')

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self,client):self.client=client
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        self.client.validate(newurl);self.client.consume()
        redirected=super().redirect_request(req,fp,code,msg,headers,newurl)
        if redirected and urlsplit(req.full_url).hostname!=urlsplit(newurl).hostname:
            redirected.remove_header('Authorization');redirected.remove_header('Cookie')
        return redirected

class Client:
    def __init__(self,hosts,*,budget=100,delay=1.2,timeout=30,max_bytes=MAX_BYTES,token=None,token_host=None):
        self.hosts=set(hosts);self.budget=budget;self.delay=delay;self.timeout=timeout;self.max_bytes=max_bytes;self.used=0;self.next_request=0;self.robots={};self.token=token;self.token_host=token_host
        self.opener=urllib.request.build_opener(SafeRedirect(self))
    def validate(self,url):
        try:
            p=urlsplit(url)
            if p.scheme!='https' or p.hostname not in self.hosts or p.username or p.password or p.port not in (None,443):raise ValueError()
        except ValueError:raise DataError('Request URL is outside the HTTPS host allowlist') from None
        return url
    def consume(self):
        if self.used>=self.budget:raise Deferred('Request budget reached; resume in the next run')
        self.used+=1
    def wait(self,seconds):
        if seconds>60:raise Deferred('Server requested a delay longer than 60 seconds')
        if seconds>0:time.sleep(seconds)
    def honor_backoff(self,seconds):
        if not isinstance(seconds,(int,float)) or seconds<0:raise FetchError('Invalid API backoff')
        if seconds>60:raise Deferred('API backoff exceeds this run; retry later')
        self.next_request=max(self.next_request,time.monotonic()+seconds)
    def allowed(self,url):
        p=urlsplit(self.validate(url));origin=urlunsplit((p.scheme,p.netloc,'','',''))
        if origin not in self.robots:
            try:r=self.get(origin+'/robots.txt',robots=False,auth=False);text=r.text()
            except FetchError as e:
                if getattr(e,'status',None)==404:text=''
                else:raise Deferred('Robots policy unavailable; collection postponed') from None
            parser=urllib.robotparser.RobotFileParser();parser.parse(text.splitlines());self.robots[origin]=parser
        policy=self.robots[origin]
        if not policy.can_fetch(USER_AGENT,url):raise FetchError('Robots policy disallows this path')
        delay=policy.crawl_delay(USER_AGENT) or policy.crawl_delay('*')
        if delay:self.delay=max(self.delay,delay)
    def get(self,url,*,robots=False,auth=True):
        self.validate(url)
        if robots:self.allowed(url)
        for attempt in range(3):
            self.consume();self.wait(max(0,self.next_request-time.monotonic()));self.next_request=time.monotonic()+self.delay
            headers={'User-Agent':USER_AGENT,'Accept':'application/json, application/rss+xml, application/atom+xml, text/html;q=0.8','Accept-Encoding':'gzip'}
            if auth and self.token and urlsplit(url).hostname==self.token_host:headers['Authorization']='Bearer '+self.token
            try:
                with self.opener.open(urllib.request.Request(url,headers=headers),timeout=self.timeout) as r:
                    data=r.read(self.max_bytes+1)
                    if len(data)>self.max_bytes:raise FetchError('Compressed response exceeds byte limit')
                    if r.headers.get('Content-Encoding','').lower()=='gzip':
                        try:
                            with gzip.GzipFile(fileobj=io.BytesIO(data)) as f:data=f.read(self.max_bytes+1)
                        except (OSError,EOFError):raise FetchError('Invalid gzip response') from None
                    if len(data)>self.max_bytes:raise FetchError('Decoded response exceeds byte limit')
                    return Response(data,r.headers,r.url)
            except urllib.error.HTTPError as e:
                if e.code in {429,500,502,503,504} and attempt<2:
                    delay=2**attempt;retry=e.headers.get('Retry-After')
                    if retry:
                        try:delay=max(0,float(retry))
                        except ValueError:
                            try:delay=max(0,(parsedate_to_datetime(retry)-datetime.now(timezone.utc)).total_seconds())
                            except (ValueError,TypeError):pass
                    e.close();self.wait(delay);continue
                error=FetchError(f'{urlsplit(url).hostname}: HTTP {e.code}');error.status=e.code;e.close();raise error from None
            except (urllib.error.URLError,TimeoutError,OSError):raise FetchError(f'{urlsplit(url).hostname}: network request failed') from None
        raise FetchError('Retry limit reached')
