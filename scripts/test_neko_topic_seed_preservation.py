"""Actual seed loader/SQL, temporary SQLite only; no runtime or user-store imports."""
import ast
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'patches/neko-study-2026-10-10-product/payload/study_companion/store_topics.py'
FIELDS='id name subject chapter stage unit depth difficulty prerequisites related typical_misconceptions skills question_types examples course_family curriculum_version exam_region exam_type aliases source updated_at'.split()

def actual_methods():
    tree=ast.parse(SOURCE.read_text(encoding='utf-8'))
    methods=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in ('load_knowledge_seed','upsert_topic')]
    ns={'Path':Path,'json':json,'Any':object,'safe_int':lambda value,default: default if value is None else int(value),
        'safe_float':lambda value,default:default if value is None else float(value)}
    exec(compile(ast.Module(body=methods,type_ignores=[]),str(SOURCE),'exec'),ns)
    return ns

class Store:
    def __init__(self):
        self._lock=threading.RLock()
        self.conn=sqlite3.connect(':memory:')
        self.conn.row_factory=sqlite3.Row
        self.conn.execute('CREATE TABLE topics ('+', '.join(name+(' TEXT PRIMARY KEY' if name=='id' else ' REAL' if name in ('depth','difficulty') else ' TEXT') for name in FIELDS)+')')
        self.knowledge_seed_json_path=None
    def _require_conn(self):return self.conn
    def _json_dumps(self,value):return json.dumps(value,ensure_ascii=False)
    def _log_warning(self,*args):raise AssertionError('unexpected invalid seed')
    def row(self):return dict(self.conn.execute('SELECT * FROM topics WHERE id=?',('seed-one',)).fetchone())

for name in ('load_knowledge_seed','upsert_topic'):setattr(Store,name,actual_methods()[name])

class SeedPreservation(unittest.TestCase):
    def setUp(self):
        self.store=Store();self.addCleanup(self.store.conn.close)
        self.topic={'id':'seed-one','name':'Original concept','subject':'math','chapter':'chapter','stage':'university','unit':'unit','source':'seed'}
    def old_time(self):
        self.store.conn.execute("UPDATE topics SET updated_at='1999-01-01 00:00:00'")
        self.store.conn.commit()
    def test_identical_seed_preserves_every_column_and_performs_no_update(self):
        self.store.upsert_topic(self.topic);self.old_time();before=self.store.row();count=self.store.conn.total_changes
        self.store.upsert_topic(dict(self.topic))
        self.assertEqual(self.store.row(),before)
        self.assertEqual(self.store.conn.total_changes,count)
    def test_changed_seed_still_updates_content_and_timestamp(self):
        self.store.upsert_topic(self.topic);self.old_time()
        self.store.upsert_topic({**self.topic,'name':'Updated concept','skills':['reasoning']})
        row=self.store.row();self.assertEqual(row['name'],'Updated concept')
        self.assertEqual(json.loads(row['skills']),['reasoning'])
        self.assertNotEqual(row['updated_at'],'1999-01-01 00:00:00')
    def test_nonseed_call_retains_existing_seed_authority_and_enrichment(self):
        self.store.upsert_topic(self.topic)
        self.store.upsert_topic({**self.topic,'name':'Model guess','source':'inferred','skills':['explain']})
        row=self.store.row();self.assertEqual(row['name'],'Original concept');self.assertEqual(row['source'],'seed')
        self.assertEqual(json.loads(row['skills']),['explain'])
    def test_real_seed_loader_repeated_load_preserves_existing_row(self):
        with tempfile.TemporaryDirectory(prefix='neko-topic-seed-') as directory:
            seed=Path(directory)/'seed.json';seed.write_text(json.dumps({'topics':[self.topic]}),encoding='utf-8')
            self.store.knowledge_seed_json_path=seed
            self.assertEqual(self.store.load_knowledge_seed(),1)
            self.old_time();before=self.store.row();count=self.store.conn.total_changes
            self.assertEqual(self.store.load_knowledge_seed(),1)
            self.assertEqual(self.store.row(),before);self.assertEqual(self.store.conn.total_changes,count)

if __name__=='__main__':unittest.main()
