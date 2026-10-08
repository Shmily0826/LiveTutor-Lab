"""Bounded live observation through the public settings entry, with rollback."""
import argparse
import json
import time
from neko_lab_client import LabClient, status_summary
from neko_lab_stage import ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['read','respond'],default='read')
    options = parser.parse_args()
    client = LabClient()
    original = status_summary(client.call('study_status'))['awareness']
    target = ROOT/f'benchmarks/raw/evidence/goal-awareness-fixed-{options.mode}.json'
    evidence = {'original':original,'samples':[]}
    try:
        enabled = {**original,'enabled':True,'snapshot_interval_seconds':1,
                   'push_to_llm_interval_seconds':30,'push_to_llm_mode':options.mode}
        result = client.call('study_update_settings_config',{'config':{'awareness':enabled}})
        payload = result['data'].get('data',result['data'])
        evidence['settings_awareness'] = payload.get('config',{}).get('awareness')
        evidence['communication'] = payload.get('communication_status')
        for _ in range(8):
            time.sleep(1)
            state = status_summary(client.call('study_status'))
            messages = client.request('/plugin/messages?plugin_id=study_companion&max_count=30')
            sample = {'runtime':state['awareness_runtime'],
                      'sensor_available':state['supervision']['sensor_available'],
                      'legacy_api_message_count':messages.get('count')}
            evidence['samples'].append(sample)
            print(json.dumps(sample),flush=True)
            target.write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    finally:
        client.call('study_update_settings_config',{'config':{'awareness':original}})
        restored = status_summary(client.call('study_status'))
        evidence['restored'] = restored['awareness'] == original
        evidence['restored_runtime'] = restored['awareness_runtime']
        target.write_text(json.dumps(evidence,indent=2),encoding='utf-8')
        print('Original awareness restored:',evidence['restored'],flush=True)


if __name__ == '__main__':
    main()
