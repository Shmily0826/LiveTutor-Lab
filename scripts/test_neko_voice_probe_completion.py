"""Probe progress/default predicates only; no application/provider/device imports."""
import ast
from copy import deepcopy
from pathlib import Path
import unittest

source=Path(__file__).with_name('neko_daily_voice_probe.py')
tree=ast.parse(source.read_text(encoding='utf-8'))
nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef)
       and node.name in ('native_response_progress','teaching_defaults_unchanged')]
scope={}
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),scope)
progress=scope['native_response_progress'];defaults=scope['teaching_defaults_unchanged']

class ProbeCompletion(unittest.TestCase):
    def snapshot(self):return {'trace':{'binaryFrames':24,'events':[{'type':'system','data':'turn end','wall':100.0}]}}
    def test_pongs_and_periodic_playback_do_not_extend_quiet_window(self):
        snapshot=self.snapshot();before=progress(snapshot)
        for kind in ('pong','native_speech_playback_state','speech_playback_state'):
            snapshot['trace']['events'].append({'type':kind,'wall':101.0,'active':False})
        self.assertEqual(progress(snapshot),before)
    def test_late_text_audio_transcript_or_failure_still_extend_window(self):
        for kind in ('gemini_response','audio_frame','user_transcript','session_failed','system'):
            with self.subTest(kind=kind):
                snapshot=self.snapshot();before=progress(snapshot)
                snapshot['trace']['events'].append({'type':kind,'wall':102.0})
                self.assertNotEqual(progress(snapshot),before)
    def test_rotating_trace_count_or_binary_only_progress_is_detected(self):
        snapshot=self.snapshot();before=progress(snapshot)
        snapshot['trace']['events']=[{'type':'system','wall':103.0}]
        self.assertNotEqual(progress(snapshot),before)
    def test_ignored_traffic_evicting_all_semantic_events_is_not_new_progress(self):
        snapshot=self.snapshot();before=progress(snapshot)
        snapshot['trace']['events']=[{'type':'pong','wall':101+i} for i in range(500)]
        self.assertEqual(progress(snapshot,before),before)
        snapshot['trace']['events'][-1]={'type':'gemini_response','wall':701}
        self.assertNotEqual(progress(snapshot,before),before)
        before=progress(snapshot);snapshot['trace']['binaryFrames']+=1
        self.assertNotEqual(progress(snapshot),before)
    def report(self):
        report={'preferences_before_voice':{'output':{'ok':True,'preferences':{'length':'brief'}}},
                'study_before_voice':{'data':{'config':{'language':'zh-CN'}}}}
        report['preferences_after_voice']=deepcopy(report['preferences_before_voice'])
        report['study_after_voice']=deepcopy(report['study_before_voice'])
        return report
    def test_unchanged_inherited_default_needs_no_explicit_saved_language(self):
        self.assertTrue(defaults(self.report()))
    def test_saved_or_effective_language_change_fails(self):
        for saved in (True,False):
            report=self.report()
            if saved:report['preferences_after_voice']['output']['preferences']['language']='en-US'
            else:report['study_after_voice']['data']['config']['language']='en-US'
            self.assertFalse(defaults(report))
    def test_absent_or_failed_observation_does_not_pass(self):
        for section in ('preferences_before_voice','preferences_after_voice','study_before_voice','study_after_voice'):
            report=self.report();report.pop(section)
            self.assertFalse(defaults(report))
        report=self.report()
        for side in ('preferences_before_voice','preferences_after_voice'):
            report[side]['output'].pop('preferences')
        self.assertFalse(defaults(report))
        report=self.report();report['preferences_after_voice']['output']['ok']=False
        self.assertFalse(defaults(report))

if __name__=='__main__':unittest.main(verbosity=2)
