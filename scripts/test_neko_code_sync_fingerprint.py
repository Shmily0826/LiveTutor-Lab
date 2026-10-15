"""Actual _code_sync: skip the index sync only for a byte-identical authorized tree."""
import ast
import os
from pathlib import Path
import tempfile
import types
import unittest
import test_neko_product_course_memory  # Existing offline package, without the desktop/audio host.

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'patches/neko-study-2026-10-10-product/payload/study_companion/study_code_tools.py'
tree = ast.parse(PATH.read_text(encoding='utf-8'))
tree.body = [n for n in tree.body if not (isinstance(n, ast.ImportFrom) and n.module == 'plugin.sdk.plugin')]
scope = {'__name__': 'actual_code_sync_fixture', '__package__': 'product_study', 'llm_tool': lambda **kwargs: lambda fn: fn}
exec(compile(tree, str(PATH), 'exec'), scope)


class Harness(scope['_StudyCodeToolsMixin']):
    def __init__(self, data):
        self.data = data

    def data_path(self, name):
        return str(Path(self.data) / name)


class SyncFingerprint(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.root = base / 'project'
        (self.root / 'lib').mkdir(parents=True)
        (self.root / 'build').mkdir()
        (self.root / 'lib/main.dart').write_text('void main() {}', encoding='utf-8')
        (base / 'data').mkdir()
        self.data = base / 'data'
        self.syncs = []
        self.exit = 0
        async def run(command, **kwargs):
            self.syncs.append(command)
            return types.SimpleNamespace(returncode=self.exit)
        scope['_run'] = run
        self.grant = {'root': str(self.root)}

    async def asyncTearDown(self):
        self.temp.cleanup()

    async def sync(self, h, **kwargs):
        h._code_sync_at = {}  # Past the throttle window, as in a slow spoken conversation.
        return await h._code_sync(['codegraph'], self.grant, **kwargs)

    async def test_unchanged_tree_skips_sync_across_turns_and_restarts(self):
        h = Harness(self.data)
        self.assertEqual(await self.sync(h), 'synced')
        self.assertEqual(await self.sync(h), 'unchanged')
        self.assertEqual(await self.sync(Harness(self.data)), 'unchanged')  # Fresh plugin, saved state.
        self.assertEqual(len(self.syncs), 1)
        self.assertEqual(self.syncs[0], ['codegraph', 'sync', str(self.root.parent)])

    async def test_edit_add_delete_rename_or_force_still_sync_while_build_output_does_not(self):
        h = Harness(self.data)
        await self.sync(h)
        main = self.root / 'lib/main.dart'
        changes = [
            lambda: (main.write_text('void main() { run(); }', encoding='utf-8'),
                     os.utime(main, ns=(1, 10**18))),
            lambda: (self.root / 'lib/new.dart').write_text('class A {}', encoding='utf-8'),
            lambda: (self.root / 'lib/new.dart').unlink(),
            lambda: main.rename(self.root / 'lib/app.dart'),
        ]
        for change in changes:
            change()
            self.assertEqual(await self.sync(h), 'synced')
        (self.root / 'build/out.bin').write_bytes(b'artifact')
        self.assertEqual(await self.sync(h), 'unchanged')
        self.assertEqual(await self.sync(h, force=True), 'synced')
        self.assertEqual(len(self.syncs), 6)

    async def test_file_listing_is_reused_only_for_an_unchanged_synced_tree(self):
        listings = []
        async def run(command, **kwargs):
            if command[1] == 'files':
                listings.append(command)
                return types.SimpleNamespace(returncode=0, stdout=f'listing-{len(listings)}')
            self.syncs.append(command)
            return types.SimpleNamespace(returncode=0)
        scope['_run'] = run
        h = Harness(self.data)
        self.assertEqual(await h._code_inventory(['codegraph'], self.grant), 'listing-1')  # never synced: no reuse
        self.assertEqual(await h._code_inventory(['codegraph'], self.grant), 'listing-2')
        await self.sync(h)
        self.assertEqual(await h._code_inventory(['codegraph'], self.grant), 'listing-3')
        self.assertEqual(await h._code_inventory(['codegraph'], self.grant), 'listing-3')  # reused
        (self.root / 'lib/second.dart').write_text('class B {}', encoding='utf-8')
        self.assertEqual(await h._code_inventory(['codegraph'], self.grant), 'listing-4')  # new file: fresh list
        self.assertEqual(await h._code_inventory(['codegraph'], self.grant), 'listing-5')  # still unsynced

    async def test_failed_sync_is_not_remembered_and_throttle_still_wins(self):
        h = Harness(self.data)
        self.exit = 3
        self.assertEqual(await self.sync(h), 'failed:exit_3')
        self.exit = 0
        self.assertEqual(await self.sync(h), 'synced')
        self.assertEqual(await h._code_sync(['codegraph'], self.grant), 'throttled')
        self.assertEqual(len(self.syncs), 2)


if __name__ == '__main__': unittest.main(verbosity=2)
