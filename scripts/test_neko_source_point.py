"""Actual source metadata and avatar callback over a real local HTTP surface."""
import ast
import os
from pathlib import Path
import re
import tempfile
import threading
import types
import unittest
from unittest.mock import patch
import httpx
from neko_learning_surface import LearningSurface

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'patches/neko-study-2026-10-10-product/payload/study_companion/study_avatar_tools.py'
tree = ast.parse(PATH.read_text(encoding='utf-8'))
method = next(n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == 'study_point_tool')
method.decorator_list = []
scope = {'os': os, 're': re, 'httpx': httpx}
exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), str(PATH), 'exec'), scope)
POINT = scope['study_point_tool']
SOURCE = '**`lib/weather_service.dart`**\n```dart\n13\tFuture<Weather> fetchWeather(AppLocation location) async {\n14\t  final uri = Uri.parse("/api/weather");\n```\n13\tThis is prose, not source.'


class SourcePointTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        material = Path(self.temp.name) / 'diagram.html'
        material.write_text('<p>diagram</p>', encoding='utf-8')
        self.surface = LearningSurface([material], port=0)
        self.thread = threading.Thread(target=self.surface.serve_forever, daemon=True)
        self.thread.start()
        self.env = patch.dict(os.environ, {'NEKO_LEARNING_SURFACE_URL': f'http://127.0.0.1:{self.surface.server_port}', 'NEKO_LEARNING_SURFACE_TOKEN': self.surface.token})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.surface.shutdown(); self.surface.server_close(); self.thread.join(timeout=3)
        self.temp.cleanup()

    def select(self, evidence=SOURCE):
        result = self.surface.show_code_evidence({'evidence': evidence, 'project': 'fixture', 'repo_commit': 'sha1'})
        self.surface.select(result['material_id'])
        return result['material_id']

    async def point(self, **kwargs):
        return await POINT(types.SimpleNamespace(), **kwargs)

    async def test_original_file_line_and_symbol_resolve_without_css_or_id(self):
        material = self.select()
        targets = self.surface.materials[material]['targets_for_pointing']
        self.assertEqual([(t['source_file'], t['source_line']) for t in targets], [('lib/weather_service.dart', 13), ('lib/weather_service.dart', 14)])
        result = await self.point(kind='source', source_line=13, symbol='fetch Weather')
        self.assertTrue(result['ok'], result)
        self.assertEqual(self.surface.command['selector'], '[data-line="evidence-3"]')
        self.assertEqual(self.surface.command['material_id'], material)
        self.assertEqual(self.surface.command['label'], 'lib/weather_service.dart:13')
        self.assertNotIn('material', result) # no unrelated source rows in an action acknowledgement
        self.assertEqual(result['say_this'], '已请求高亮当前源码第13行。')

    async def test_duplicate_file_lines_require_disambiguation(self):
        self.select(SOURCE + '\n**`lib/other.dart`**\n```dart\n13\tFuture<Weather> fetchWeather() {}\n```')
        refused = await self.point(kind='source', source_line=13, symbol='fetchWeather')
        self.assertEqual(refused['error'], 'source_line_not_unique_or_not_shown')
        self.assertIsNone(self.surface.command)
        accepted = await self.point(source_line=13, source_file='weather_service.dart', symbol='fetchWeather')
        self.assertTrue(accepted['ok'], accepted)

    async def test_unattributed_example_fence_does_not_inherit_previous_file(self):
        material = self.select(SOURCE + '\nExample, not source:\n```dart\n999\tfetchWeather(exampleOnly)\n```')
        targets = self.surface.materials[material]['targets_for_pointing']
        self.assertEqual([t['source_line'] for t in targets], [13, 14])
        result = await self.point(kind='source', source_line=999)
        self.assertEqual(result['error'], 'source_line_not_unique_or_not_shown')

    async def test_actual_codegraph_header_with_symbol_summary(self):
        self.select(SOURCE.replace('**`lib/weather_service.dart`**', '**`lib/weather_service.dart`** — fetchWeather(method), WeatherService(class)'))
        result = await self.point(kind='source', source_line=13, symbol='fetchWeather')
        self.assertTrue(result['ok'], result)

    async def test_status_keeps_locator_metadata_and_confirmation_language_is_one_off(self):
        self.select()
        status = await self.point(kind='status')
        self.assertEqual(status['material']['targets_for_pointing'][0]['source_line'], 13)
        first = await self.point(kind='source', source_line=13, language='en-US')
        self.assertEqual(first['say_this'], 'Requested a highlight on source line 13.')
        next_reply = await self.point(kind='source', source_line=13)
        self.assertEqual(next_reply['say_this'], '已请求高亮当前源码第13行。')

    async def test_non_source_or_unshown_symbol_is_refused(self):
        result = await self.point(kind='source', source_line=13)
        self.assertEqual(result['error'], 'source_evidence_not_selected')
        self.select()
        for line, symbol in [(500, ''), (13, 'notShown')]:
            result = await self.point(kind='source', source_line=line, symbol=symbol)
            self.assertEqual(result['error'], 'source_line_not_unique_or_not_shown')
        self.assertIsNone(self.surface.command)

    async def test_boolean_negative_and_missing_line_are_invalid(self):
        self.select()
        for kwargs in [{'source_line': True}, {'source_line': -1}, {}, {'source_line': '13'}]:
            result = await self.point(kind='source', **kwargs)
            self.assertEqual(result['error'], 'invalid_source_line')
        self.assertIsNone(self.surface.command)

    async def test_old_material_identity_cannot_point_current_version(self):
        old = self.select()
        self.select(SOURCE.replace('sha1', 'sha2') + '\nnew version')
        result = await self.point(kind='source', source_line=13, material_id=old)
        self.assertEqual(result['error'], 'stale_material')
        self.assertIsNone(self.surface.command)

    async def test_learner_switch_between_snapshot_and_command_rejects_old_target(self):
        self.select()
        original = self.surface.guide
        def changed(command):
            self.surface.select(next(k for k, m in self.surface.materials.items() if m.get('source') != 'filtered_codegraph_evidence'))
            return original(command)
        self.surface.guide = changed
        result = await self.point(kind='source', source_line=13, symbol='fetchWeather')
        self.assertFalse(result['ok'], result)
        self.assertIsNone(self.surface.command)

    async def test_invented_css_without_material_is_an_explicit_repair_error(self):
        self.select()
        result = await self.point(kind='selector', selector='.code-line:nth-child(13)')
        self.assertEqual(result['error'], 'missing_material_identity')
        self.assertIsNone(self.surface.command)


if __name__ == '__main__': unittest.main(verbosity=2)
