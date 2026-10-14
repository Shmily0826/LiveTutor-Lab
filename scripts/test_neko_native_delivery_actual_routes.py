"""Actual Core routing and phrase/Omni delivery with a local queue socket.

DSP, preview registry and Core lifecycle/token seam are isolated doubles;
no provider, capture, audio output, real RNNoise or user data is exercised.
"""
import asyncio
import os
from pathlib import Path
import struct
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

# Runtime dependency imports can initialize ConfigManager; isolate it first.
storage=tempfile.TemporaryDirectory(prefix='neko-delivery-actual-')
storage_env=patch.dict(os.environ,{'NEKO_STORAGE_DEFAULT_ROOT':storage.name,
    'NEKO_STORAGE_SELECTED_ROOT':storage.name,'LOCALAPPDATA':storage.name,
    'NEKO_NATIVE_DELIVERY_DIAGNOSTICS':'0','NEKO_EXPERIMENTAL_PHRASE_INPUT':'1'})
storage_env.start()
import test_neko_native_barge_in as native
import neko_phrase_input_transport as phrase
from neko_native_delivery_diagnostics import install_native_delivery_diagnostics

class ActualCore(native.OfflineManager):
    _process_microphone_stream_data=native.production_method('main_logic/core/asr_runtime.py','_process_microphone_stream_data')
    _route_microphone_audio=native.production_method('main_logic/core/asr_runtime.py','_route_microphone_audio')
    _route_microphone_audio_unfiltered=native.production_method('main_logic/core/asr_runtime.py','_route_microphone_audio_unfiltered')

ActualCore._process_microphone_stream_data.__globals__['struct']=struct
ActualCore._route_microphone_audio.__globals__.update(os=os,
    preview_isolation_registry=SimpleNamespace(is_manager_isolated=lambda manager:False))

class DeliveryActualRoutes(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fixture=native.NativeHandoffTest()
        self.manager,self.client,self.socket=await self.fixture.fixture()
        self.manager.__class__=ActualCore
        del self.manager._route_microphone_audio_unfiltered
        self.manager._voice_activation_pending_capture={}
        self.manager._audio_stream_epoch=1
        self.manager._voice_input_pipeline_failed=False
        self.manager._voice_session_activation_factory=None
        self.manager._voice_session_activation_required=False
        self.manager._voice_session_activation_degraded=False
        self.manager._voice_input_noise_reduction_enabled=True
        self.manager._ingress_token_matches=lambda token:token is self.manager._native_ingress_token
        self.manager.hot_swap_cache_lock=asyncio.Lock()
        self.manager.is_hot_swap_imminent=False
        self.manager.is_flushing_hot_swap_cache=False
        self.client._ai_recent_activity_time=0
        self.manager.note_native_speech_playback_state({'active':False,
            'sdk_speech_correlation_id':self.client._native_output_connection_token},self.manager.websocket)
        self.speech=True;self.frame_index=0;self.dsp_calls=0
        async def dsp(pcm,*,sample_rate_hz):
            self.dsp_calls+=1
            return SimpleNamespace(pcm16=pcm,sample_rate_hz=sample_rate_hz,
                speech_probability=.9 if self.speech else .1,rnnoise_available=True,rnnoise_evidence=None)
        self.manager._voice_input_audio_pipeline=SimpleNamespace(process=dsp)
        # Restore the actual class methods after each case; hooks never outlive this fixture.
        self.restores=[]
        for cls,names in ((ActualCore,('_process_microphone_stream_data','_route_microphone_audio','_route_microphone_audio_unfiltered')),
                          (phrase.NativePhraseUplink,('accept','flush')),
                          (native.transport._TransportMixin,('stream_audio','send_event'))):
            for name in names:
                guard=patch.object(cls,name,getattr(cls,name));guard.start();self.restores.append(guard)
        self.counters=install_native_delivery_diagnostics(ActualCore,phrase.NativePhraseUplink,native.transport._TransportMixin,
            enabled=True,logger=native.LogRecorder())
    async def asyncTearDown(self):
        driver=getattr(self.client,'_native_phrase_uplink',None)
        if driver:
            driver.retire()
            if driver.failure_task:await asyncio.gather(driver.failure_task,return_exceptions=True)
        await self.fixture.dispose(self.manager)
        for restore in reversed(self.restores):restore.stop()
    async def frame(self,speech=True):
        self.speech=speech;self.frame_index+=1
        await self.manager._process_microphone_stream_data({'sample_rate_hz':16000,'data':[11 if speech else 0]*512},
            ingress_token=self.manager._native_ingress_token,audio_stream_epoch=1,ingress_sequence=self.frame_index,
            captured_at=time.time()+self.frame_index*.032)
    def counts(self):return self.counters.snapshot()['counts']
    async def test_actual_positive_process_route_phrase_flush_and_append(self):
        for _ in range(8):await self.frame(True)
        for _ in range(38):await self.frame(False)
        driver=self.client._native_phrase_uplink
        if driver.writer:await driver.writer
        counts=self.counts()
        for stage in ('core_process','core_route','core_native_route','native_stream_audio','phrase_accept'):
            self.assertEqual(counts[stage]['entered'],46)
        self.assertEqual(counts['phrase_flush']['entered'],1)
        self.assertGreater(counts['provider_audio_append']['entered'],0)
        self.assertTrue(any(event['type']=='input_audio_buffer.append' for event in self.socket.sent))
        self.assertGreater(self.manager._omni_mic_audio_bytes,0)
        self.assertEqual(self.dsp_calls,46)
    async def test_required_missing_factory_keeps_actual_fail_closed(self):
        self.manager._voice_session_activation_required=True
        await self.frame();counts=self.counts()
        self.assertEqual(counts['core_process']['entered'],1);self.assertEqual(counts['core_route']['returned_true'],1)
        self.assertNotIn('core_native_route',counts);self.assertEqual(self.socket.sent,[])
        self.assertEqual(self.counters.snapshot()['states']['core_route']['entry']['activation_required'],{'true':1})
    async def test_actual_noise_contract_mismatch_never_reaches_transport(self):
        self.manager._voice_session_activation_factory=SimpleNamespace(enforce=True,noise_reduction_enabled=False)
        await self.frame();counts=self.counts()
        self.assertEqual(counts['core_route']['entered'],1);self.assertNotIn('core_native_route',counts)
        self.assertEqual(self.counters.snapshot()['states']['core_route']['entry']['noise_contract_match'],{'false':1})
        self.assertEqual(self.socket.sent,[])
    async def test_actual_inactive_after_dsp_stops_before_route(self):
        self.manager.is_active=False
        await self.frame();counts=self.counts()
        self.assertEqual(self.dsp_calls,1);self.assertEqual(counts['core_process']['returned_none'],1)
        self.assertNotIn('core_route',counts);self.assertEqual(self.socket.sent,[])

if __name__=='__main__':
    try:unittest.main()
    finally:storage_env.stop();storage.cleanup()
