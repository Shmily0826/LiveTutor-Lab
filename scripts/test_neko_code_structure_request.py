"""Actual tool route ignores a learner sentence as a structure directory filter."""
import ast
from pathlib import Path
import types
import unittest
import test_neko_product_course_memory  # Existing offline package, without the desktop/audio host.

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'patches/neko-study-2026-10-10-product/payload/study_companion/study_code_tools.py'
tree=ast.parse(PATH.read_text(encoding='utf-8'))
tree.body=[n for n in tree.body if not (isinstance(n,ast.ImportFrom) and n.module=='plugin.sdk.plugin')]
scope={'__name__':'actual_code_tool_fixture','__package__':'product_study','llm_tool':lambda **kwargs:lambda fn:fn}
exec(compile(tree,str(PATH),'exec'),scope)
calls=[]
async def run(command,**kwargs):
    calls.append(command)
    return types.SimpleNamespace(returncode=0,stdout='[{"path":"sky_scout/app/lib/main.dart","nodeCount":4},{"path":"sibling_copy/lib/main.dart","nodeCount":99}]')
async def surface(*args):return {'available':False}
scope['_run']=run;scope['_publish_code_surface']=surface


class Harness(scope['_StudyCodeToolsMixin']):
    def __init__(self):self.logger=None;self.recorded=None
    def _code_authorization(self):return {'root':'D:/fixture','prefix':'sky_scout/','name':'fixture','commit':'grant-A'}
    def _code_cli(self):return ['fixture-codegraph']
    async def _code_sync(self,*args,**kwargs):return 'synced'
    async def _code_head(self,*args):return 'current-B'
    def _code_filter(self,text,*args):return text.splitlines(),{'chars':len(text),'kept_lines':2,'dropped_outside_root':0,'dropped_denied_path':0,'redacted':0}
    def _code_leak(self,*args):return ''
    def _code_receipt(self,*args):pass
    async def _code_record(self,*args,**kwargs):self.recorded=kwargs


class StructureRequest(unittest.IsolatedAsyncioTestCase):
    async def test_structure_sentence_or_empty_query_uses_whole_authorized_tree(self):
        for query in ('Sky Scout的主要模块怎么分？', ''):
            h=Harness();calls.clear()
            result=await h.study_code_tool(mode='structure',query=query)
            self.assertTrue(result['ok'],result)
            self.assertEqual(calls,[['fixture-codegraph','files','--path','D:/fixture','-j']])
            self.assertIn('sky_scout/app/lib',result['evidence'])
            self.assertNotIn('sibling_copy',result['evidence'])
            self.assertEqual(result['shown'],[])
            self.assertEqual(h.recorded['repo_commit'],'current-B')
            self.assertIn('top-level entries of the project',result['evidence'])
            # A tree carries no calls: the teacher must offer a thread, not assert a data flow.
            self.assertIn('never state which module calls or feeds which as a fact',result['note'])


if __name__=='__main__':unittest.main(verbosity=2)
