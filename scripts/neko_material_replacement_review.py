"""Review a preserved replacement scene and complete WASAPI WAV; no external calls."""
import argparse
import hashlib
import json
from pathlib import Path
import wave
import numpy as np

def review(report_path):
    data=json.loads(report_path.read_text(encoding='utf-8'))
    replacement=data.get('material_replacement') or {}
    old=replacement.get('old_native_token')
    events=(replacement.get('first_turn_trace') or [])+((data.get('native_final') or {}).get('trace') or {}).get('events',[])
    cancels=[event for event in events if event.get('type')=='game_route_speech_cancel' and event.get('correlation_id')==old]
    stops=[event for event in events if event.get('type')=='speech_playback_state' and event.get('reason')=='native_connection_cancel'
           and event.get('correlationId')==old and event.get('active') is False]
    cancel=min((event['wall'] for event in cancels),default=None)
    wav_path=report_path.with_suffix('.loopback.wav')
    with wave.open(str(wav_path)) as audio:
        assert audio.getsampwidth()==2
        rate=audio.getframerate();channels=audio.getnchannels()
        signal=np.frombuffer(audio.readframes(audio.getnframes()),dtype='<i2').reshape(-1,channels)
    start=((data.get('loopback') or {}).get('device') or {}).get('capture_start_wall')
    curve=[];step=max(1,int(rate*.25))
    for offset in range(0,len(signal),step):
        peak=float(np.max(np.abs(signal[offset:offset+step].astype(np.int32))))/32767
        curve.append({'wall':start+offset/rate if start else None,'at':offset/rate,'peak':round(peak,4)})
    # Use complete preserved audio, not the meter JSON's first 60 bins. Each
    # 250ms bin spans an interval; allow 500ms after cancel for endpoint/bins.
    quiet=[item for item in curve if cancel is not None and item['wall'] is not None and cancel+.5<=item['wall']<cancel+3.5]
    loud=[item for item in curve if item['peak']>.02]
    turns=data.get('turns') or []
    followup=turns[1] if len(turns)>1 else {}
    followup_frames=[event for event in events if event.get('type')=='audio_frame' and followup and event.get('wall',0)>=followup['input_wall']]
    checks={'old_playback_active':bool((replacement.get('before') or {}).get('playback',{}).get('active')),
        'old_token_cancel_received':bool(old) and bool(cancels),'old_native_queue_stopped':bool(stops),
        'actual_loopback_signal':bool(loud),'loopback_quiet_after_cancel':len(quiet)>=10 and all(item['peak']<=.02 for item in quiet),
        'followup_uses_new_token':bool(followup_frames) and all(str(event.get('correlation_id') or '').startswith('native_connection_')
            and event['correlation_id']!=old for event in followup_frames),
        'finalized_report':isinstance(data.get('after'),dict) and bool(data.get('after')) and bool(data.get('proof')),
        'followup_terminal':bool(followup.get('observation_end_wall')) and not followup.get('turn_timeout')
            and any(event.get('type')=='system' and event.get('data')=='turn end' and event.get('wall',0)>=followup.get('input_wall',float('inf')) for event in events)
            and not (((data.get('native_final') or {}).get('playback') or {}).get('active')),
        'session_normal':not data.get('failure') and not data.get('turn_timeout')}
    return {'report':str(report_path.resolve()),'sha256':hashlib.sha256(report_path.read_bytes()).hexdigest(),
        'checks':checks,'result':'PASS_THIS_FIXED_DEVICE_SCENE_REQUIRES_FACT_REVIEW' if all(checks.values()) else 'PARTIAL_OR_FAILED',
        'cancel_wall':cancel,'native_stop_wall':min((event['wall'] for event in stops),default=None),
        'loopback':{'capture_start_wall':start,'duration_seconds':len(signal)/rate,'total_loud_bins':len(loud),
            'bins_after_cancel_with_500ms_grace':quiet,'last_loud_bin_end_wall':max((item['wall']+.25 for item in loud if item['wall'] is not None),default=None)},
        'material_control_submission':(replacement.get('material_after_submission') or {}).get('output',{}).get('material_control_submission'),
        'native_replies':[turn.get('native_reply') for turn in turns], 'failure':data.get('failure'),
        'before_ledger':data.get('before'),'after_ledger':data.get('after'),'human_experience':'PENDING',
        'scope':'one preserved fixed-input scene; loopback is system output and not semantic/human listening; facts require actual material review'}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists():raise RuntimeError('preserve existing review')
    result=review(args.report);args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:result[key] for key in ('result','checks','failure')},ensure_ascii=False))
