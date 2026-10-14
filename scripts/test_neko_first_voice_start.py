"""Official fresh-card setup, no host, provider, audio device or learner data."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import neko_desktop_tutor_host as host


class FirstVoiceStart(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='neko-first-voice-')
        self.addCleanup(self.temp.cleanup);self.store=Path(self.temp.name)
        self.card=self.store/'N.E.K.O/config/characters.json'

    def test_fresh_official_card_has_native_voice_and_guidance_before_first_host(self):
        result=host.apply_free_voice_route(self.store)
        self.assertIs(result.get('created_from_host_defaults'),True)
        data=json.loads(self.card.read_text(encoding='utf-8'));active=data['当前猫娘']
        self.assertEqual(data['猫娘'][active]['_reserved']['voice_id'],'yui')
        self.assertEqual(host.apply_tutor_role_guidance(self.store/'N.E.K.O'),'set')
        before=self.card.read_bytes();host.apply_free_voice_route(self.store)
        self.assertEqual(self.card.read_bytes(),before)

    def test_existing_card_only_changes_voice_and_preserves_learner_guidance(self):
        self.card.parent.mkdir(parents=True)
        data={'当前猫娘':'own','猫娘':{'own':{'custom':'keep','_reserved':{
            'voice_id':'old','persona_override':{'prompt_guidance':'My own guidance'}}}},'other':['keep']}
        self.card.write_text(json.dumps(data),encoding='utf-8');expected=deepcopy(data)
        expected['猫娘']['own']['_reserved']['voice_id']='yui'
        result=host.apply_free_voice_route(self.store)
        self.assertNotIn('created_from_host_defaults',result)
        self.assertEqual(json.loads(self.card.read_text(encoding='utf-8')),expected)
        self.assertEqual(host.apply_tutor_role_guidance(self.store/'N.E.K.O'),"kept the learner's own guidance")

    def test_malformed_existing_card_is_not_recreated(self):
        self.card.parent.mkdir(parents=True);self.card.write_bytes(b'{invalid')
        with self.assertRaises(ValueError):host.apply_free_voice_route(self.store)
        self.assertEqual(self.card.read_bytes(),b'{invalid')

    def test_fresh_text_card_can_receive_guidance_without_selecting_a_voice(self):
        self.assertTrue(host.ensure_tutor_character_card(self.store))
        before=json.loads(self.card.read_text(encoding='utf-8'))
        active=before['当前猫娘']
        self.assertEqual(host.apply_tutor_role_guidance(self.store/'N.E.K.O'),'set')
        after=json.loads(self.card.read_text(encoding='utf-8'))
        card=after['猫娘'][active]['_reserved']
        self.assertEqual(card['voice_id'],before['猫娘'][active]['_reserved']['voice_id'])
        self.assertNotEqual(card['voice_id'],host.FREE_ROUTE_VOICE)
        self.assertIn('material_source=project_code',card['persona_override']['prompt_guidance'])
        saved=self.card.read_bytes()
        self.assertFalse(host.ensure_tutor_character_card(self.store))
        self.assertEqual(self.card.read_bytes(),saved)


if __name__=='__main__':unittest.main(verbosity=2)
