"""Task-only instrumentation, immutable canonical gateway and unknown-source refusal."""
from pathlib import Path
import tempfile
import unittest
from neko_desktop_tutor_host import PRODUCT,prepare_summary_prompt_audit

class SummaryAudit(unittest.TestCase):
    def test_task_gateway_only_and_unknown_source_preserved(self):
        original=(PRODUCT/'payload/study_companion/study_model_gateway.py').read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            store=Path(folder)/'neko-daily-speech-acceptance-test'
            target=store/'plugin-code/study_companion/study_model_gateway.py'
            target.parent.mkdir(parents=True);target.write_bytes(original)
            result=prepare_summary_prompt_audit(store)
            patched=target.read_text(encoding='utf-8')
            self.assertIn('operation == "summarize_session"',patched)
            self.assertEqual(patched.replace('audit("started", **({"messages": messages} if operation == "summarize_session" else {}))','audit("started")'),original.decode('utf-8'))
            self.assertNotEqual(result['canonical_sha256'],result['instrumented_sha256'])
            edited=target.read_bytes()+b'\n# unknown'
            target.write_bytes(edited)
            with self.assertRaises(RuntimeError):prepare_summary_prompt_audit(store)
            self.assertEqual(target.read_bytes(),edited)
            with self.assertRaises(RuntimeError):prepare_summary_prompt_audit(Path(folder)/'neko-daily-companion')
        self.assertEqual((PRODUCT/'payload/study_companion/study_model_gateway.py').read_bytes(),original)

if __name__=='__main__':unittest.main(verbosity=2)
