"""Research regressions: relevance, authorization, source integrity and publication."""
import copy
import io
import json
import tempfile
import shutil
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch, MagicMock
from sanhedrin.model import DataError, normalize
from sanhedrin.store import Store
from sanhedrin.build import build
from sanhedrin.teshuva import compose, profiles, publish_assets, render, retrieve_library, search_groups, make_source, validate_request
from sanhedrin.research import public_url, extract_page, external_sources, PublicHTTP, review_draft, api_response, ResearchAPIError
from tools.save_teshuva import save
from test_teshuva import FakeGitHub, mock_response

ROOT = Path(__file__).resolve().parents[1]
PLAN = {'queries_en': ['schach mold'], 'queries_he': ['סכך עובש'], 'subquestions': ['May the schach be treated?']}
DRAFT = {'status': 'draft', 'paragraphs': [{'text': 'The source addresses mold on schach.', 'citations': [1]}], 'missing_evidence': [], 'clarification_questions': []}


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        shutil.copytree(ROOT / 'config', self.root / 'config')
        (self.root / 'Rav').mkdir()
        (self.root / 'Rav/Test.png').write_bytes(b'image')
        self.store = Store(self.root / 'db.sqlite')
        self.config = json.loads((self.root / 'config/teshuva-search.json').read_text())
        self.record = normalize({'id': 'yeshiva-1', 'title': 'Schach mold', 'question': 'What to do about mold?', 'answers': [{'text': 'This source discusses mold on schach and the need to check the treatment.'}], 'format': 'plain', 'url': 'https://www.yeshiva.org.il/ask/1'})
        self.store.insert(self.record)
        self.request = {'schema': 1, 'question_html': '<p>May schach be treated against mold?</p>', 'language': 'en', 'profile_id': profiles(self.root)[0]['id'], 'keywords': 'schach mold', 'source_ids': [self.record['id']], 'use_openai': True, 'search_version': 2, 'external_research': False, 'source_urls': []}

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_specific_bilingual_sources_beat_general_holiday(self):
        for i in range(2, 20):
            self.store.insert(normalize({'id': f'yeshiva-{i}', 'title': 'Sukkot', 'question': 'Sukkot question', 'answers': [{'text': 'Sukkot is discussed in a general source about the holiday and its customs.'}], 'format': 'plain'}))
        he = normalize({'id': 'doc-encyclopedia', 'provider': 'local', 'native_id': 'responsa/סכך.html', 'title': 'סכך', 'kind': 'document', 'question': 'סכך שיש עליו עובש: זהו טקסט עברי מפורט מן האנציקלופדיה לצורך בדיקת המקורות.', 'format': 'plain'})
        self.store.insert(he)
        sources, stats = retrieve_library(self.store, search_groups('schach mold', self.config))
        self.assertEqual({s['id'] for s in sources}, {'yeshiva-1', he['id']})
        self.assertEqual(stats['scanned'], 20)

    def test_hebrew_prefixes_match_the_encyclopedia_text(self):
        record = {**self.record, 'kind': 'document', 'answers': [], 'question': 'דיון הלכתי בסכך ובעובש וההבדלים בין סוגי החומרים.', 'format': 'plain'}
        self.store.upsert(record)
        groups = search_groups('סכך עובש', self.config)
        sources, _ = retrieve_library(self.store, groups)
        self.assertTrue(sources)
        self.assertEqual(search_groups('ובסכך ובעובש', self.config), groups)

    def test_public_search_index_contains_hebrew_roots(self):
        shutil.copytree(ROOT / 'web', self.root / 'web')
        self.store.insert(normalize({'id':'yeshiva-33','title':'דיון בסכך ובעובש','question':'דיון','answers':[{'text':'בדיקה הלכתית בסכך ובעובש עם דיון מפורט במקורות.'}],'format':'plain'}))
        out=self.root/'publication';build(self.store,self.root,out)
        manifest=json.loads((out/'catalog/manifest.json').read_text())
        index={}
        for path in (out/manifest['data_base']/'search').glob('*.json'):
            index.update(json.loads(path.read_text()))
        self.assertIn('סכך',index)
        self.assertIn('עובש',index)

    def test_full_relevant_text_and_separate_answers_are_available(self):
        record = copy.deepcopy(self.record)
        record['answers'] = [{'text': 'Schach mold. ' + 'Context matters. ' * 300, 'format': 'plain', 'answer_id': 'a'}, {'text': 'A different answer discusses mold on schach and distinguishes the treatment.', 'format': 'plain', 'answer_id': 'b'}]
        source = make_source(record, search_groups('schach mold', self.config))
        self.assertGreater(len(source['text']), 2200)
        self.assertIn('Answer 2', source['text'])
        self.assertEqual(source['answer_ids'], ['a', 'b'])

    def test_new_requests_can_research_without_local_hits(self):
        request = {**self.request, 'source_ids': []}
        self.assertEqual(validate_request(request, self.root)['source_ids'], [])
        with self.assertRaises(DataError):
            validate_request({**request, 'use_openai': False}, self.root)

    def test_external_requires_api_and_public_urls(self):
        for url in ['http://example.org/x', 'https://127.0.0.1/x', 'https://169.254.169.254/latest/meta-data/', 'https://10.0.0.1/', 'https://[::1]/', 'https://user:secret@example.org/', 'https://example.org:444/', 'https://foo.local/x']:
            with self.subTest(url=url), self.assertRaises(DataError):
                public_url(url)
        self.assertEqual(public_url('https://www.yeshiva.org.il/ask/1'), 'https://www.yeshiva.org.il/ask/1')
        with self.assertRaises(DataError):
            validate_request({**self.request, 'use_openai': False, 'external_research': True}, self.root)

    def test_dns_private_addresses_never_connect(self):
        with patch('sanhedrin.research.socket.getaddrinfo', return_value=[(2, 1, 6, '', ('127.0.0.1', 443))]), patch('sanhedrin.research.socket.create_connection') as connect:
            with self.assertRaises(DataError):
                PublicHTTP().request('https://example.org/x')
            connect.assert_not_called()

    def test_hebrew_urls_are_encoded_for_the_https_request(self):
        connection=MagicMock();response=connection.getresponse.return_value
        response.status=200;response.read.return_value=b'content'
        response.getheader.side_effect=lambda key, default=None: {'Content-Type':'text/html'}.get(key,default)
        addresses=[(2,1,6,'',('93.184.216.34',443))]
        with patch('sanhedrin.research.socket.getaddrinfo',return_value=addresses), patch('sanhedrin.research.socket.create_connection'), patch('sanhedrin.research.ssl.create_default_context'), patch('sanhedrin.research.http.client.HTTPSConnection',return_value=connection):
            PublicHTTP().request('https://www.kipa.co.il/שאל-את-הרב/?q=סכך')
        target=connection.request.call_args.args[1]
        target.encode('ascii')
        from urllib.parse import unquote
        self.assertEqual(unquote(target),'/שאל-את-הרב/?q=סכך')

    def test_bot_wall_and_empty_question_form_are_not_evidence(self):
        for page in [b'<title>Just a moment</title><body>Verify you are human</body>', b'<title>Ask a rabbi</title><form>Question</form>']:
            with self.assertRaises(DataError):
                extract_page(page, 'https://example.org')
        page = extract_page(('<title>Published answer</title><article>' + 'An actual answer with context. ' * 20 + '</article>').encode(), 'https://example.org')
        self.assertGreater(len(page['text']), 180)

    def test_blocked_owner_or_master_switch_never_runs_research(self):
        for reason in ('owner_only', 'disabled'):
            with patch('sanhedrin.research.plan_question') as plan, patch('sanhedrin.research.external_sources') as research, patch('sanhedrin.teshuva.api_draft') as draft:
                result = compose(self.store, self.root, {**self.request, 'external_research': True}, identity='teshuva-1-123456789abc', api_key='test-only', api_block_reason=reason)
            plan.assert_not_called(); research.assert_not_called(); draft.assert_not_called()
            self.assertEqual(result['publication_status'], 'needs_research')

    def test_plain_sources_are_never_published_as_finished_teshuvot(self):
        request={k:v for k,v in self.request.items() if k!='search_version'}
        request['use_openai']=False
        result=compose(self.store,self.root,request,identity='teshuva-1-123456789abc')
        self.assertEqual(result['publication_status'],'needs_research')
        result.pop('publication_status')  # old saved source compilations receive the same gate
        self.assertNotIn('Draft answer',render(result))
        self.assertIn('saved for further research',render(result))

    def test_failed_external_search_never_becomes_a_library_only_draft(self):
        notes=[{'provider':'web','status':'unavailable','http_status':400},{'provider':'Sefaria','status':'searched','sources':0}]
        with patch('sanhedrin.research.plan_question',return_value=PLAN), patch('sanhedrin.research.external_sources',return_value=([],notes)), patch('sanhedrin.teshuva.api_draft') as draft:
            result=compose(self.store,self.root,{**self.request,'external_research':True},identity='teshuva-1-123456789abc',api_key='test-only')
        draft.assert_not_called()
        self.assertEqual(result['publication_status'],'needs_research')
        self.assertTrue(result['missing_evidence'])

    def test_same_material_evidence_blocks_torah_scroll_analogy(self):
        self.store.close()
        self.store=Store(self.root/'scope.sqlite')
        record=normalize({'id':'yeshiva-2','title':'Mold on Torah scrolls','question':'How to clean mold on a Torah scroll?','answers':[{'text':'This answer discusses cleaning mold on a Torah scroll with vinegar.'}],'format':'plain','url':'https://www.yeshiva.org.il/ask/2'})
        self.store.insert(record)
        request={**self.request,'source_ids':[record['id']]}
        plan={**PLAN,'requires_same_material_evidence':True,'material_terms':['schach','bamboo','סכך','במבוק'],'problem_terms':['mold','moldy schach','עובש']}
        with patch('sanhedrin.research.plan_question',return_value=plan), patch('sanhedrin.teshuva.api_draft') as draft:
            result=compose(self.store,self.root,request,identity='teshuva-1-123456789abc',api_key='test-only')
        draft.assert_not_called()
        self.assertEqual(result['openai_status'],'insufficient')
        self.assertEqual(result['publication_status'],'needs_research')

    def test_review_rejects_ready_when_a_paragraph_uses_unsupported_analogy(self):
        response={'status':'ready','issues':[],'clarification_questions':[],'checks':[{'paragraph':1,'supported':True,'material_scope_matches':False,'answers_question':True,'unsupported_analogy':True,'reason':'Torah-scroll cleaning does not establish safe treatment of bamboo schach.'}]}
        review=review_draft('Schach mold',[{'text':'Torah-scroll care'}],DRAFT,api_key='test',model='test',opener=lambda *a,**k:mock_response(response))
        self.assertEqual(review['status'],'needs_research')
        self.assertTrue(review['issues'])

    def test_api_diagnostics_redact_credentials_and_keep_parameter_error(self):
        key='sk-test-secret'
        def fail(*a,**k):
            raise urllib.error.HTTPError('https://api.openai.com/v1/responses',400,'Bad Request',{},io.BytesIO(json.dumps({'error':{'type':'invalid_request_error','param':'max_tool_calls','message':'Unsupported parameter. '+key}}).encode()))
        with self.assertRaises(ResearchAPIError) as caught:
            api_response({},api_key=key,opener=fail)
        self.assertNotIn(key,json.dumps(caught.exception.details))
        self.assertEqual(caught.exception.status,400)
        self.assertEqual(caught.exception.details['param'],'max_tool_calls')

    def test_answered_question_context_is_kept_for_scope_checking(self):
        source=make_source(self.record,search_groups('schach mold',self.config))
        self.assertIn('mold',source['question_context'])
        self.assertTrue(source['text'])

    def test_second_pass_rejects_unsupported_draft(self):
        with patch('sanhedrin.research.plan_question', return_value=PLAN), patch('sanhedrin.teshuva.api_draft', return_value=copy.deepcopy(DRAFT)), patch('sanhedrin.research.review_draft', return_value={'status': 'needs_research', 'issues': ['Treatment is not supported by the cited text.'], 'clarification_questions': []}):
            result = compose(self.store, self.root, self.request, identity='teshuva-1-123456789abc', api_key='test-only')
        self.assertEqual(result['publication_status'], 'needs_research')
        self.assertEqual(result['paragraphs'], [])
        self.assertNotIn('The optional API did not produce', render(result))
        self.assertNotIn('Treatment is not supported', render(result))

    def test_older_api_requests_also_receive_research_and_review(self):
        request={k:v for k,v in self.request.items() if k not in {'search_version','source_urls','external_research'}}
        with patch('sanhedrin.research.plan_question',return_value=PLAN) as plan, patch('sanhedrin.teshuva.api_draft',return_value=copy.deepcopy(DRAFT)), patch('sanhedrin.research.review_draft',return_value={'status':'needs_research','issues':['Unsupported treatment'],'clarification_questions':[]}) as review:
            result=compose(self.store,self.root,request,identity='teshuva-1-123456789abc',api_key='test-only')
        plan.assert_called_once();review.assert_called_once()
        self.assertEqual(result['publication_status'],'needs_research')
        self.assertEqual(result['retrieval']['scanned'],1)

    def test_review_requires_empty_issues_for_ready(self):
        with self.assertRaises(DataError):
            review_draft('Question', [], DRAFT, api_key='test', model='test', opener=lambda *a, **k: mock_response({'status': 'ready', 'issues': ['Missing evidence'], 'clarification_questions': []}))

    def test_pending_is_excluded_from_archive_and_questions_preserved(self):
        with patch('sanhedrin.research.plan_question', return_value=PLAN), patch('sanhedrin.teshuva.api_draft', return_value={'status': 'needs_clarification', 'paragraphs': [], 'missing_evidence': [], 'clarification_questions': ['What treatment will be used?']}):
            result = compose(self.store, self.root, self.request, identity='teshuva-1-123456789abc', api_key='test-only')
        (self.root / 'Sanhedrin').mkdir()
        (self.root / 'Sanhedrin'/ (result['id'] + '.json')).write_text(json.dumps(result))
        out = self.root / 'out';out.mkdir();publish_assets(self.root, out)
        self.assertEqual(json.loads((out / 'teshuvot.json').read_text()), [])
        page = (out / 'Sanhedrin' / (result['id'] + '.html')).read_text()
        self.assertIn('What treatment will be used?', page)
        self.assertNotIn('Draft answer', page)

    def test_pending_retry_is_explicit_and_success_is_idempotent(self):
        api = FakeGitHub()
        with patch('sanhedrin.research.plan_question', return_value=PLAN), patch('sanhedrin.teshuva.api_draft', return_value={'status': 'insufficient', 'paragraphs': []}):
            first = save(api, self.root, self.store, 1, self.request, api_key='test-only')
        with patch('tools.save_teshuva.compose', side_effect=AssertionError('No automatic paid retry')):
            save(api, self.root, self.store, 1, self.request, api_key='test-only')
        with patch('sanhedrin.research.plan_question', return_value=PLAN), patch('sanhedrin.teshuva.api_draft', return_value=DRAFT), patch('sanhedrin.research.review_draft', return_value={'status': 'ready', 'issues': [], 'clarification_questions': []}):
            second = save(api, self.root, self.store, 1, self.request, api_key='test-only', retry_pending=True)
        self.assertEqual(first['id'], second['id'])
        self.assertEqual(second['publication_status'], 'ready')
        with patch('tools.save_teshuva.compose', side_effect=AssertionError('Reuse complete answer')):
            save(api, self.root, self.store, 1, self.request, api_key='test-only', retry_pending=True)

    def test_changed_or_closed_question_does_not_commit(self):
        api = FakeGitHub()
        with self.assertRaises(DataError):
            save(api, self.root, self.store, 1, {**self.request, 'use_openai': False}, commit_guard=lambda: False)
        self.assertEqual(api.commits, 0)

    def test_deleted_saved_request_is_not_resurrected_by_retry(self):
        api = FakeGitHub()
        first = save(api, self.root, self.store, 1, self.request, api_block_reason='disabled')
        def removed(*a, **k):
            api.files.pop('Sanhedrin/' + first['id'] + '.json')
            return {'schema': 1, 'id': first['id'], 'request_hash': 'unused'}
        with patch('tools.save_teshuva.compose', side_effect=removed), self.assertRaises(DataError):
            save(api, self.root, self.store, 1, self.request, api_key='test-only')

    def test_older_model_domain_filters_fall_back_without_changing_model(self):
        calls=[]
        class HTTP:
            def json(self,*a):return {'hits':{'hits':[]}}
            def page(self,url):return {'title':'Answer','text':'An actual published source on schach mold. '*10,'url':url}
        def opener(request,timeout):
            payload=json.loads(request.data);calls.append(payload)
            if len(calls)==1:
                raise urllib.error.HTTPError(request.full_url,400,'Bad Request',{},io.BytesIO(json.dumps({'error':{'message':"Parameter 'filters' not supported with model 'gpt-4.1-mini'",'param':'tools'}}).encode()))
            return io.BytesIO(json.dumps({'status':'completed','output':[{'type':'web_search_call','action':{'sources':[{'url':'https://asktherav.com/answer'},{'url':'https://outside.example/answer'}]}}]}).encode())
        sources,notes=external_sources('Schach mold',PLAN,json.loads((self.root/'config/teshuva-research.json').read_text()),[],api_key='test-only',model='gpt-4.1-mini',groups=search_groups('schach mold',self.config),passage=lambda text,groups,limit:(text,False),http=HTTP(),opener=opener)
        self.assertEqual(len(calls),2)
        self.assertTrue(all(p['model']=='gpt-4.1-mini' for p in calls))
        self.assertNotIn('filters',calls[1]['tools'][0])
        self.assertIn('allowed_domains',json.loads(calls[1]['input']))
        self.assertEqual(len(sources),1)
        self.assertEqual(next(n for n in notes if n.get('provider')=='web')['search_mode'],'query_domains')

    def test_sefaria_anchor_and_url_sources_are_read_not_inferred(self):
        class HTTP:
            def __init__(self): self.queries=[];self.pages=[]
            def json(self, url, value=None):
                if value is not None:
                    self.queries.append(value)
                    return {'hits': {'hits': [{'_source': {'ref': 'Sukkah 12a:1'}}]}}
                return {'ref': 'Sukkah 12a:1', 'versions': [{'language': 'he', 'text': 'מקור עברי מפורט על סכך ופסוליו מן התלמוד.', 'license': 'Public Domain'}]}
            def page(self, url):
                self.pages.append(url)
                if 'blocked' in url: raise DataError('Source verification page is not evidence')
                return {'title': 'Actual answer', 'url': url, 'text': 'Schach mold treatment with original answer context. ' * 10}
        http = HTTP()
        response = {'status': 'completed', 'output': [{'type': 'web_search_call', 'action': {'sources': [*({'url': f'https://asktherav.com/blocked/{i}'} for i in range(12)), {'url': 'https://unselected.example/answer'}]}}, {'type':'message','content':[{'type':'output_text','text':'Lead','annotations':[{'type':'url_citation','url':'https://asktherav.com/answer'}]}]}]}
        sources, notes = external_sources('Schach mold', PLAN, json.loads((self.root/'config/teshuva-research.json').read_text()), ['https://new-source.example/answer'], api_key='test-only', model='test', groups=search_groups('schach mold', self.config), passage=lambda text, groups, limit: (text, False), http=http, opener=lambda *a, **k: io.BytesIO(json.dumps(response).encode()))
        self.assertTrue(any(q['query'] == 'סכך עובש' for q in http.queries))
        self.assertTrue(any(q['query'] == 'schach mold' for q in http.queries))
        self.assertTrue(all(q['type'] == 'text' for q in http.queries))
        self.assertEqual(len(sources), 3)
        self.assertTrue(sources[0]['provider'] == 'Sefaria')
        self.assertFalse(any('unselected' in u for u in http.pages))
        self.assertTrue(any(n.get('status') == 'unavailable' for n in notes))
