"""Actual indexed-file window command, scope/credential guards, and precise shown rows."""
import asyncio
import json
from pathlib import Path
import tempfile
import types
import unittest
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


if __name__=='__main__':unittest.main(verbosity=2)
