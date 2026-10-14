"""Actual indexed-file window command, scope/credential guards, and precise shown rows."""
import asyncio
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
import test_neko_code_structure_request as actual


class CodeFileWindow(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.outside_temp=tempfile.TemporaryDirectory()
        self.outside=Path(self.outside_temp.name)/'outside.dart'
        self.outside.write_text('outside source must never reach CLI',encoding='utf-8')
        (self.root/'server/routes').mkdir(parents=True)
        (self.root/'server/routes/weather.js').write_text('fixture',encoding='utf-8')
        (self.root/'.env').write_text('DUMMY ONLY',encoding='utf-8')
        self.authorized={'root':str(self.root),'prefix':'sky_scout/','name':'fixture','commit':'grant-A'}

    def tearDown(self):self.temp.cleanup();self.outside_temp.cleanup()

    async def test_command_uses_authorized_index_path_and_discards_dependency_header(self):
        h=actual.Harness();h._code_authorization=lambda:self.authorized
        calls=[]
        async def run(command,**kwargs):
            calls.append(command)
            return types.SimpleNamespace(returncode=0,stdout='**sky_scout/server/routes/weather.js** — used by 1 file: sky_scout/server/app.js\n\n7\trouter.get();\n8\tconst lat = req.query.lat;\n9\tconst lon = req.query.lon;\n10\tresponse();\n**Dependents**\nother source data')
        original=actual.scope['_run'];actual.scope['_run']=run
        try:
            result=await h.study_code_tool(mode='file',file='server/routes/weather.js',offset=8,limit=2)
        finally:actual.scope['_run']=original
        self.assertTrue(result['ok'],result)
        self.assertEqual(calls[0],['fixture-codegraph','node','--file','sky_scout/server/routes/weather.js','--offset','8','--limit','2','--path',str(self.root)])
        self.assertNotIn('server/app.js',result['evidence'])
        self.assertNotIn('7\t',result['evidence']);self.assertNotIn('10\t',result['evidence'])
        self.assertEqual(result['shown'],[{'file':'sky_scout/server/routes/weather.js','lines':[8,9]}])

    async def test_parent_absolute_outside_credentials_and_bad_limits_are_refused_before_cli(self):
        h=actual.Harness();h._code_authorization=lambda:self.authorized
        actual.calls.clear()
        for fields in ({'file':'../outside.dart'},{'file':str(self.outside)},
                       {'file':'.env'},{'file':'server/routes/weather.js','offset':True},
                       {'file':'server/routes/weather.js','limit':121},{'file':'server/routes/weather.js','offset':0}):
            result=await h.study_code_tool(mode='file',**fields)
            self.assertFalse(result['ok'],result)
            self.assertEqual(result['error'],'INVALID_SOURCE_FILE_REQUEST')
        self.assertEqual(actual.calls,[])

    async def test_returned_index_prefix_and_mismatched_cli_header(self):
        indexed=actual.scope['_code_file_request'](self.authorized,'sky_scout/server/routes/weather.js',1,40)
        self.assertEqual(indexed,'sky_scout/server/routes/weather.js')
        self.assertEqual(actual.scope['_code_file_window']('**sibling/routes/weather.js**\n8\tbad',indexed,1,40),'')

    async def test_later_file_block_cannot_be_relabelled_as_requested_source(self):
        indexed='sky_scout/server/routes/weather.js'
        raw=f'**{indexed}**\n8\tconst lat = req.query.lat;\n**foreign/routes/weather.js**\n8\tforeign source must be withheld'
        window=actual.scope['_code_file_window'](raw,indexed,8,2)
        self.assertIn('const lat',window)
        self.assertNotIn('foreign',window)

    async def resolve(self, requested, rows, *, returncode=0):
        h=actual.Harness();h._code_authorization=lambda:self.authorized
        calls=[]
        async def run(command,**kwargs):
            calls.append(command)
            if command[1]=='files':
                return types.SimpleNamespace(returncode=returncode,stdout=rows if isinstance(rows,str) else json.dumps(rows))
            return types.SimpleNamespace(returncode=0,stdout='**'+command[3]+'**\n8\tfixture source\n9\tmore source')
        with patch.dict(actual.scope,{'_run':run}):
            result=await h.study_code_tool(mode='file',file=requested,offset=8,limit=1)
        return result,calls

    async def test_unique_basename_and_suffix_reuse_index_then_exact_window(self):
        rows=[{'path':'sky_scout/server/routes/weather.js'},
              {'path':'sibling/server/routes/weather.js'},
              {'path':'sky_scout/server/routes/weather.js'}]
        for requested in ('weather.js','routes/weather.js','sky_scout/routes/weather.js'):
            with self.subTest(requested=requested):
                result,calls=await self.resolve(requested,rows)
                self.assertTrue(result['ok'],result)
                self.assertEqual(calls[0],['fixture-codegraph','files','--path',str(self.root),'-j'])
                self.assertEqual(calls[1],['fixture-codegraph','node','--file','sky_scout/server/routes/weather.js','--offset','8','--limit','1','--path',str(self.root)])
                self.assertEqual(result['shown'],[{'file':'sky_scout/server/routes/weather.js','lines':[8]}])
                self.assertNotIn('sibling',str(result));self.assertNotIn('9\t',result['evidence'])

    async def test_same_name_returns_authorized_candidates_without_reading_either(self):
        (self.root/'client').mkdir();(self.root/'client/weather.js').write_text('second fixture')
        result,calls=await self.resolve('weather.js',[{'path':p} for p in
            ['sky_scout/server/routes/weather.js','sky_scout/client/weather.js','sibling/server/weather.js']])
        self.assertFalse(result['ok']);self.assertEqual(result['error'],'AMBIGUOUS_SOURCE_FILE')
        self.assertEqual(result['candidates'],['sky_scout/client/weather.js','sky_scout/server/routes/weather.js'])
        self.assertEqual(result['candidate_count'],2);self.assertEqual(len(calls),1)
        self.assertNotIn('evidence',result);self.assertNotIn('sibling',str(result))

    async def test_unsafe_index_entries_cannot_resolve_to_source(self):
        (self.root/'.aws').mkdir();(self.root/'.aws/weather.js').write_text('credential fixture only')
        result,calls=await self.resolve('weather.js',[{'path':p} for p in
            ['sky_scout/.aws/weather.js','sky_scout/../outside/weather.js','sky_scout_copy/weather.js','/sky_scout/server/routes/weather.js']])
        self.assertEqual(result['error'],'SOURCE_FILE_NOT_RESOLVED');self.assertEqual(result['candidates'],[])
        self.assertEqual(len(calls),1);self.assertNotIn('.aws',str(result));self.assertNotIn('outside',str(result))

    async def test_lookup_failures_do_not_turn_into_source_or_retry(self):
        for rows,returncode,error in [('broken json',0,'SOURCE_FILE_LOOKUP_FAILED'),
                                      ({'path':'not a list'},0,'SOURCE_FILE_LOOKUP_FAILED'),
                                      ([],0,'SOURCE_FILE_NOT_RESOLVED'),([],3,'CODEGRAPH_EXIT_3')]:
            with self.subTest(rows=rows,returncode=returncode):
                result,calls=await self.resolve('weather.js',rows,returncode=returncode)
                self.assertEqual(result['error'],error);self.assertEqual(len(calls),1)
                self.assertNotIn('evidence',result)

    async def test_ambiguous_candidate_list_is_bounded_and_never_contains_source(self):
        rows=[]
        for number in range(10):
            folder=self.root/f'part{number}';folder.mkdir();(folder/'weather.js').write_text('private fixture source')
            rows.append({'path':f'sky_scout/part{number}/weather.js'})
        result,calls=await self.resolve('weather.js',rows)
        self.assertEqual(result['error'],'AMBIGUOUS_SOURCE_FILE');self.assertEqual(result['candidate_count'],10)
        self.assertEqual(len(result['candidates']),8);self.assertEqual(len(calls),1)
        self.assertNotIn('private fixture source',str(result))

    async def test_missing_unsafe_request_is_refused_before_index_discovery(self):
        h=actual.Harness();h._code_authorization=lambda:self.authorized
        for requested in ('../missing.js','.ssh/missing.js',str(self.outside.parent/'missing.js')):
            with self.subTest(requested=requested),patch.dict(actual.scope,{'_run':None}):
                result=await h.study_code_tool(mode='file',file=requested)
                self.assertEqual(result['error'],'INVALID_SOURCE_FILE_REQUEST')


if __name__=='__main__':unittest.main(verbosity=2)
