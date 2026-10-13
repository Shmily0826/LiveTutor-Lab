"""Only the intentional first-answer retirement path; no host/audio/network."""
import copy
import unittest
from neko_daily_voice_probe import material_retirement_observed

class ReplacementObservation(unittest.TestCase):
    def setUp(self):
        self.change={'old_native_token':'native_connection_owned','submission_completed_wall':2,
                     'before':{'playback':{'active':True}}}
        self.snapshot={'playback':{'active':False},'trace':{'events':[
            {'type':'game_route_speech_cancel','correlation_id':'native_connection_owned'},
            {'type':'speech_playback_state','reason':'native_connection_cancel','correlationId':'native_connection_owned','active':False}]}}
    def test_exact_cancel_and_stopped_queue_ends_retired_answer(self):
        self.assertTrue(material_retirement_observed(self.change,self.snapshot))
    def test_submission_or_different_token_never_ends_first_answer(self):
        for mutation in ('no_cancel','other_stop','no_submit','before_inactive','new_playing'):
            change=copy.deepcopy(self.change);snapshot=copy.deepcopy(self.snapshot)
            if mutation=='no_cancel':snapshot['trace']['events'].pop(0)
            elif mutation=='other_stop':snapshot['trace']['events'][1]['correlationId']='native_connection_new'
            elif mutation=='no_submit':change.pop('submission_completed_wall')
            elif mutation=='before_inactive':change['before']['playback']['active']=False
            else:snapshot['playback']['active']=True
            with self.subTest(mutation=mutation):self.assertFalse(material_retirement_observed(change,snapshot))
    def test_ordinary_or_missing_observation_does_not_gain_retirement_shortcut(self):
        self.assertFalse(material_retirement_observed(None,self.snapshot))
        self.assertFalse(material_retirement_observed(self.change,{}))

if __name__=='__main__':unittest.main(verbosity=2)
