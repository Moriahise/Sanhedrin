"""Regressions for empty answers, wrong context and useful partial answers."""
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from sanhedrin.model import normalize
from sanhedrin.store import Store
from sanhedrin.teshuva import compose, profiles, retrieve_library, search_groups, render, api_draft
from sanhedrin.research import source_urls, web_queries, extract_page, rerank_sources, sefaria_text, plan_question, review_draft
from tools.save_teshuva import save
from test_teshuva import FakeGitHub, mock_response

ROOT = Path(__file__).resolve().parents[1]
PLAN = {'context':'Speech and the four levels of creation, not prophetic empires.', 'anchor_terms':['memallel','דיבור','ממללא'], 'references':['Onkelos Genesis 2:7'], 'queries_en':['memallel medaber speech'],'queries_he':['ממללא דיבור שיחה'],'subquestions':['What distinguishes speech?'],'material_terms':[],'problem_terms':[],'requires_same_material_evidence':False}

class ImprovementsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);shutil.copytree(ROOT/'config',self.root/'config')
        (self.root/'Rav').mkdir();(self.root/'Rav/Test.png').write_bytes(b'image')
        self.store=Store(self.root/'db.sqlite');self.addCleanup(self.store.close)
        self.config=json.loads((self.root/'config/teshuva-search.json').read_text())
        self.record=normalize({'id':'yeshiva-1','title':"Memallel vs. M'daber vs. M'Siach",'question':'Are porpoises chai or memallel?','answers':[{'text':'This saved source distinguishes speech and conversation, with the relevant context.'}],'format':'plain'})
        self.store.insert(self.record)
        self.request={'schema':1,'question_html':"<p>Memallel vs. M'daber vs. M'Siach</p><p>Are porpoises chai or memallel?</p>",'language':'en','profile_id':profiles(self.root)[0]['id'],'source_ids':[self.record['id']],'keywords':'','use_openai':True,'search_version':2,'external_research':False,'source_urls':[]}

    def test_transliterated_apostrophes_join_and_do_not_mean_messiah(self):
        groups=search_groups("M'daber M’Siach",self.config)
        self.assertTrue(any('mdaber' in g for g in groups));self.assertTrue(any('שיחה' in g for g in groups))
        self.assertFalse(any('משיח' in g for g in groups))
        self.assertTrue(any('חוצפית' in g for g in search_groups('Chutzpit',self.config)))

    def test_short_direct_answer_beats_long_incidental_vocabulary(self):
        self.store.insert(normalize({'id':'yeshiva-2','title':'Four kingdoms in prophecy','question':'Historical empires','answers':[{'text':('Memallel mdaber msiach speech conversation porpoises kingdom prophecy. '*800)}],'format':'plain'}))
        groups=search_groups('memallel mdaber msiach speech conversation porpoises',self.config)
        sources,_=retrieve_library(self.store,groups,query="Memallel vs. M'daber vs. M'Siach",config=self.config)
        self.assertEqual(sources[0]['id'],self.record['id'])

    def test_question_links_are_read_without_repeating_them_in_url_field(self):
        url='https://en.wikisource.org/wiki/Translation:Likutei_Etzot#DIBBUR_-_Speech'
        self.assertEqual(source_urls('See '+url+'.'),[url])
        self.assertEqual(source_urls('https://127.0.0.1/a https://user:secret@example.com/a'),[])

    def test_fragment_extraction_reads_dibbur_not_first_section_of_book(self):
        page=('<title>Likutei Etzot</title><main><div class="mw-parser-output"><h2 id="Other">Other</h2><p>'+('Unrelated. '*400)+'</p>\n<h2 id="DIBBUR_-_Speech">Speech</h2>\n<p>'+('Dibbur is heard and accepted in the quoted discussion. '*3)+'</p>\n<h2 id="Next">Next</h2><p>Different chapter</p></div></main>').encode()
        text=extract_page(page,'https://en.wikisource.org/wiki/Book#DIBBUR_-_Speech')['text']
        self.assertIn('heard and accepted',text);self.assertNotIn('Unrelated.',text);self.assertNotIn('Different chapter',text)

    def test_nonreasoning_search_receives_plain_focused_query(self):
        queries=web_queries(PLAN,['sefaria.org','chabad.org','en.wikisource.org'],'memallel speech')
        self.assertEqual(len(queries),2);self.assertIn('site:sefaria.org',queries[0]);self.assertTrue(queries[1].startswith('ממללא'))
        self.assertFalse(any(q.startswith('{') for q in queries))

    def test_semantic_selection_discards_wrong_kingdom_context(self):
        sources=[{'title':'Four prophetic empires','text':'The kingdom of Babylon.'},{'title':'Onkelos Genesis 2:7','text':'The human becomes a speaking spirit.'}]
        response={'sources':[{'number':1,'relevance':1,'reason':'Wrong meaning of kingdom.'},{'number':2,'relevance':5,'reason':'Direct primary text.'}]}
        selected=rerank_sources('The speaking kingdom',sources,PLAN,api_key='test',model='test',opener=lambda *a,**k:mock_response(response))
        self.assertEqual([s['title'] for s in selected],['Onkelos Genesis 2:7'])

    def test_single_irrelevant_source_is_still_checked(self):
        selected=rerank_sources('Memallel',[{'title':'Harp music','text':'Ancient musical instruments.'}],PLAN,api_key='test',model='test',opener=lambda *a,**k:mock_response({'sources':[]}))
        self.assertEqual(selected,[])

    def test_primary_reference_is_loaded_and_license_retained(self):
        class HTTP:
            def json(inner,url):
                self.assertIn('Onkelos%20Genesis%202%3A7',url)
                return {'ref':'Onkelos Genesis 2:7','versions':[{'language':'he','text':'והות באדם לרוח ממללא — מקור ראשוני שנקרא מן הספרייה.','license':'Public Domain'}]}
        source=sefaria_text('Onkelos Genesis 2:7',HTTP(),[],lambda text,*a:(text,False))
        self.assertIn('ממללא',source['text']);self.assertEqual(source['kind'],'primary_text');self.assertIn('Public Domain',source['license'])

    def test_plan_records_precise_context_and_primary_leads(self):
        plan=plan_question('Memallel and medaber',api_key='test',model='test',opener=lambda *a,**k:mock_response(PLAN))
        self.assertEqual(plan['references'],['Onkelos Genesis 2:7']);self.assertIn('not prophetic',plan['context'])

    def test_good_paragraph_survives_bad_paragraph_and_second_search(self):
        draft={'status':'partial','paragraphs':[{'text':'The original text distinguishes speech and conversation.','citations':[1]},{'text':'Use vinegar to clean moldy bamboo.','citations':[1]}],'missing_evidence':['The porpoise classification is not established.'],'clarification_questions':[]}
        review={'status':'partial','citation_audit_version':1,'issues':['No bamboo treatment is established.'],'clarification_questions':[],'checks':[{'paragraph':1,'supported':True,'material_scope_matches':True,'answers_question':True,'unsupported_analogy':False,'reason':'Supported explanation.'},{'paragraph':2,'supported':False,'material_scope_matches':False,'answers_question':False,'unsupported_analogy':True,'reason':'Wrong material and topic.'}]}
        with patch('sanhedrin.research.plan_question',return_value=PLAN) as plan,patch('sanhedrin.research.rerank_sources',side_effect=lambda q,s,**kw:s),patch('sanhedrin.teshuva.api_draft',return_value=draft),patch('sanhedrin.research.review_draft',return_value=review):
            result=compose(self.store,self.root,self.request,identity='teshuva-1-123456789abc',api_key='test')
        self.assertEqual(plan.call_count,2);self.assertIn('feedback',plan.call_args.kwargs)
        self.assertEqual(result['publication_status'],'partial');self.assertEqual(len(result['paragraphs']),1)
        page=render(result);self.assertIn('distinguishes speech',page);self.assertNotIn('Use vinegar',page);self.assertIn('Still open',page)

    def test_research_does_not_ask_user_to_find_sources(self):
        draft={'status':'needs_clarification','paragraphs':[],'missing_evidence':[],'clarification_questions':['Which preferred sources should I use?','Is this a spoken or a written statement?']}
        with patch('sanhedrin.research.plan_question',return_value=PLAN),patch('sanhedrin.research.rerank_sources',side_effect=lambda q,s,**kw:s),patch('sanhedrin.teshuva.api_draft',return_value=draft):
            result=compose(self.store,self.root,self.request,identity='teshuva-1-123456789abc',api_key='test')
        self.assertEqual(result['clarification_questions'],['Is this a spoken or a written statement?'])
        self.assertNotIn('preferred sources',render(result))

    def test_old_failed_request_is_upgraded_once_with_same_identity(self):
        api=FakeGitHub();first=save(api,self.root,self.store,9,self.request,api_block_reason='disabled')
        path='Sanhedrin/'+first['id']+'.json';old=json.loads(api.files[path]);old.pop('answer_version');old['publication_status']='needs_research';old['openai_status']='insufficient';api.files[path]=json.dumps(old)
        replacement={**old,'answer_version':8,'citation_audit_version':1,'publication_status':'ready','mode':'openai','openai_status':'draft','paragraphs':[{'text':'A supported answer.','citations':[1]}]}
        with patch('tools.save_teshuva.compose',return_value=replacement) as run:
            second=save(api,self.root,self.store,9,self.request,api_key='test')
        run.assert_called_once();self.assertEqual(first['id'],second['id']);self.assertEqual(second['publication_status'],'ready')
        with patch('tools.save_teshuva.compose',side_effect=AssertionError('No duplicate paid request')):
            save(api,self.root,self.store,9,self.request,api_key='test')

    def test_wrong_model_context_cannot_reintroduce_daniel_or_messiah(self):
        wrong={**PLAN,'context':'Prophetic kingdoms','anchor_terms':['משיח','Daniel kingdoms'],'references':[]}
        fixed=plan_question('Are porpoises Memallel or Chai in the fourth kingdom?',api_key='test',model='test',opener=lambda *a,**k:mock_response(wrong))
        self.assertIn('NOT Daniel',fixed['context']);self.assertIn('Onkelos Genesis 2:7',fixed['references'])
        self.assertFalse(any('משיח' in word or 'kingdom' in word for word in fixed['anchor_terms']))

    def test_supported_flag_without_real_quote_does_not_publish_claim(self):
        draft={'paragraphs':[{'text':'Speech must be heard and accepted to count as medaber.','citations':[1]}]}
        response={'status':'ready','issues':[],'clarification_questions':[],'checks':[{'paragraph':1,'supported':True,'material_scope_matches':True,'answers_question':True,'unsupported_analogy':False,'reason':'Claimed support.','evidence':[{'claim':draft['paragraphs'][0]['text'],'source':1,'quote':'speech must be heard and accepted','kind':'explicit'}]}]}
        review=review_draft('Memallel and Chai',[{'title':'Animal hide','text':'There are four levels of creation: inanimate, plant, animal and human.'}],draft,api_key='test',model='test',opener=lambda *a,**k:mock_response(response))
        self.assertFalse(review['checks'][0]['supported']);self.assertEqual(review['status'],'needs_research')

    def test_exact_supporting_quote_is_verified_against_cited_text(self):
        claim='The source lists four levels of creation.'
        response={'status':'ready','issues':[],'clarification_questions':[],'checks':[{'paragraph':1,'supported':True,'material_scope_matches':True,'answers_question':True,'unsupported_analogy':False,'reason':'Direct classification.','evidence':[{'claim':claim,'source':1,'quote':'four levels of creation: inanimate, plant, animal and human','kind':'explicit'}]}]}
        review=review_draft('Creation levels',[{'title':'Creation','text':'There are four levels of creation: inanimate, plant, animal and human.'}],{'paragraphs':[{'text':claim,'citations':[1]}]},api_key='test',model='test',opener=lambda *a,**k:mock_response(response))
        self.assertTrue(review['checks'][0]['supported']);self.assertEqual(review['citation_audit_version'],1)

    def test_model_status_mismatch_preserves_text_for_independent_review(self):
        for status in ['draft','insufficient','needs_clarification']:
            response={'status':status,'paragraphs':[{'text':'The source lists four creation levels.','citations':[1]}],'missing_evidence':['The linguistic distinction is not established.'],'clarification_questions':[]}
            result=api_draft('Creation levels',[{'title':'Creation','provider':'local','text':'Four levels of creation.'}],'en',api_key='test',model='test',opener=lambda *a,**k:mock_response(response))
            self.assertEqual(result['status'],'partial');self.assertEqual(len(result['paragraphs']),1)

    def test_source_author_is_displayed_as_name(self):
        result=compose(self.store,self.root,{**self.request,'use_openai':False},identity='teshuva-1-123456789abc')
        result['sources'][0]['author']={'display_name':'Source Writer','user_id':123}
        page=render(result)
        self.assertIn('Source Writer',page);self.assertNotIn('user_id',page);self.assertNotIn('[object Object]',page)

    def test_duplicate_source_numbers_do_not_discard_valid_selection(self):
        response={'sources':[{'number':1,'relevance':5,'reason':'Direct text.'},{'number':1,'relevance':4,'reason':'Repeated lead.'}]}
        sources=[{'title':'Creation','text':'Four levels of creation.'}]
        selected=rerank_sources('Creation levels',sources,{},api_key='test',model='test',opener=lambda *a,**k:mock_response(response))
        self.assertEqual(len(selected),1);self.assertEqual(selected[0]['relevance'],5)

    def test_named_review_slots_distinguish_paragraph_and_source_numbers(self):
        paragraphs=[{'text':'There are four levels of creation.','citations':[2]},{'text':'The fourth level is speaking.','citations':[2]}]
        def opener(req,**kwargs):
            payload=json.loads(req.data);data=json.loads(payload['input'])
            self.assertEqual([p['paragraph'] for p in data['draft']],[1,2])
            self.assertEqual(payload['text']['format']['schema']['properties']['checks']['required'],['1','2'])
            checks={str(i):{'supported':True,'material_scope_matches':True,'answers_question':True,'unsupported_analogy':False,'reason':'Exact source statement.','evidence':[{'claim':p['text'],'source':2,'quote':p['text'],'kind':'explicit'}]} for i,p in enumerate(paragraphs,1)}
            return mock_response({'status':'ready','issues':[],'clarification_questions':[],'checks':checks})
        review=review_draft('Creation levels',[{'title':'Other','text':'Unrelated text.'},{'title':'Creation','text':'There are four levels of creation. The fourth level is speaking.'}],{'paragraphs':paragraphs},api_key='test',model='test',opener=opener)
        self.assertEqual([c['paragraph'] for c in review['checks']],[1,2]);self.assertEqual(review['status'],'ready')

    def test_verified_claim_survives_unverified_neighbour_in_same_paragraph(self):
        valid='The source lists four levels of creation.'
        original=valid+' It also establishes every distinction about hearing, acceptance and literacy, and recommends cleaning bamboo schach with vinegar.'
        check={'supported':True,'material_scope_matches':True,'answers_question':True,'unsupported_analogy':False,'reason':'The classification is documented.','evidence':[{'claim':valid,'source':1,'quote':'four levels of creation','kind':'explicit'}]}
        review=review_draft('Creation levels',[{'title':'Creation','text':'There are four levels of creation.'}],{'paragraphs':[{'text':original,'citations':[1]}]},api_key='test',model='test',opener=lambda *a,**k:mock_response({'status':'partial','issues':['Other distinctions are unestablished.'],'clarification_questions':[],'checks':{'1':check}}))
        self.assertTrue(review['checks'][0]['supported']);self.assertEqual(review['checks'][0]['verified_text'],valid)
        self.assertNotIn('vinegar',review['checks'][0]['verified_text'])

    def test_authentic_short_phrase_and_typography_are_not_rejected(self):
        claim='Onkelos describes the human as a “speaking spirit”.'
        check={'supported':True,'material_scope_matches':True,'answers_question':True,'unsupported_analogy':False,'reason':'The phrase is explicit.','evidence':[{'claim':'Onkelos describes the human as a "speaking spirit".','source':1,'quote':'speaking spirit','kind':'explicit'}]}
        review=review_draft('Memallel',[{'title':'Onkelos Genesis 2:7','text':'The human became a speaking spirit.'}],{'paragraphs':[{'text':claim,'citations':[1]}]},api_key='test',model='test',opener=lambda *a,**k:mock_response({'status':'ready','issues':[],'clarification_questions':[],'checks':{'1':check}}))
        self.assertTrue(review['checks'][0]['supported'])
