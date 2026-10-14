"""Check observer anchoring and relay boundaries without opening a host or browser."""
import io
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import neko_study_ready_probe as probe


class RelayBoundary(unittest.TestCase):
    def request(self,path,payload):
        handler=object.__new__(probe.Relay)
        raw=json.dumps(payload).encode()
        handler.path=path;handler.headers={'Content-Length':str(len(raw))}
        handler.rfile=io.BytesIO(raw);handler.server=SimpleNamespace(report={},opener=Mock())
        handler.reply=Mock();handler.forward=Mock()
        return handler

    def test_reading_request_is_forwarded_with_original_body(self):
        body={'plugin_id':'study_companion','entry_id':'study_status','args':{'locale':'zh-CN'}}
        handler=self.request('/runs',body);handler.do_POST()
        handler.forward.assert_called_once_with(json.dumps(body).encode())
        self.assertEqual(handler.server.report['reading_entries'],['study_status'])

    def test_model_capture_and_material_mutation_requests_are_refused(self):
        for entry,args in [('study_explain_text',{}),('study_ocr_snapshot',{}),
                           ('__llm_tool__study_material',{'action':'clear'}),
                           ('__llm_tool__study_material',{'action':'status','image_base64':'fixture'}),
                           ('study_status',{'course_id':'another-course'})]:
            with self.subTest(entry=entry,args=args):
                handler=self.request('/runs',{'plugin_id':'study_companion','entry_id':entry,'args':args})
                handler.do_POST();self.assertEqual(handler.reply.call_args.args[0],403)
                handler.forward.assert_not_called()

    def test_non_run_write_and_oversized_body_are_refused(self):
        for path,length,code in [('/other',1,403),('/runs',1_000_001,413)]:
            handler=self.request(path,{});handler.headers['Content-Length']=str(length)
            handler.do_POST();self.assertEqual(handler.reply.call_args.args[0],code)
            handler.forward.assert_not_called()

    def test_absolute_or_network_path_never_reaches_upstream(self):
        for path in ('http://example.invalid/','//example.invalid/'):
            with self.subTest(path=path):
                handler=self.request(path,{})
                probe.Relay.forward(handler)
                self.assertEqual(handler.reply.call_args.args[0],403)
                handler.server.opener.open.assert_not_called()

    def test_bootstrap_observation_preserves_original_handler_and_refuses_unknown_source(self):
        original='bootstrap().catch((error) => { record(error); });'
        changed=probe.observed_main(original)
        self.assertIn('globalThis.__phase54Bootstrap = bootstrap();',changed)
        self.assertIn('globalThis.__phase54Bootstrap.catch((error) => { record(error); });',changed)
        for source in ('unrelated source',original+original):
            with self.assertRaises(ValueError):probe.observed_main(source)

    def test_browser_provenance_is_preserved_without_fabricating_credentials(self):
        handler=self.request('/runs',{})
        handler.headers={'Origin':'http://127.0.0.1:54321','Referer':'http://127.0.0.1:54321/page',
                         'Sec-Fetch-Site':'same-origin','X-Unrelated':'discard'}
        response=Mock();response.status=403;response.read.return_value=b'{}'
        response.headers={'Content-Type':'application/json'}
        response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        handler.server.opener.open.return_value=response
        probe.Relay.forward(handler,b'{}')
        request=handler.server.opener.open.call_args.args[0]
        self.assertEqual(request.get_header('Origin'),handler.headers['Origin'])
        self.assertEqual(request.get_header('Referer'),handler.headers['Referer'])
        self.assertEqual(request.get_header('Sec-fetch-site'),'same-origin')
        self.assertFalse(request.has_header('X-csrf-token'))
        self.assertFalse(request.has_header('X-unrelated'))
        self.assertEqual(handler.reply.call_args.args[0],403)

    def test_deck_listing_permits_only_bounded_reading_pagination(self):
        def allowed(args):
            return probe.allowed_request({'plugin_id':'study_companion',
                                          'entry_id':'study_memory_list_decks','args':args})
        self.assertTrue(allowed({'limit':100,'offset':0,'locale':'zh-CN'}))
        self.assertTrue(allowed({'limit':100,'offset':100}))
        for args in ({},{'limit':100,'offset':-1},{'limit':100,'offset':True},
                     {'limit':100,'offset':10001},{'limit':1000,'offset':0},
                     {'limit':100,'offset':0,'delete':True}):
            self.assertFalse(allowed(args),args)


if __name__=='__main__':unittest.main(verbosity=2)
