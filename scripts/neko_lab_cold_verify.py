"""Observe the first cold-start Study instance and restore only awareness."""
import json
import time
from neko_lab_stage import ROOT
from neko_lab_client import LabClient,status_summary


def main():
    client = LabClient()
    original = json.loads((ROOT/'benchmarks/raw/evidence/goal-cold-original-awareness.json').read_text(encoding='utf-8'))
    samples = []
    target = ROOT/'benchmarks/raw/evidence/goal-cold-verification.json'
    try:
        for _ in range(6):
            state = status_summary(client.call('study_status'))
            row = {'config_enabled':state['awareness']['enabled'],
                   'runtime':state['awareness_runtime'],'sensor_available':state['supervision']['sensor_available']}
            samples.append(row)
            print(json.dumps(row),flush=True)
            time.sleep(2)
        communication = client.call('study_neko_communication_status')['data']
        records = {'samples':samples,'communication':communication}
        if not all(row['runtime']['active'] for row in samples):
            raise AssertionError('Cold startup did not preserve awareness')
        if samples[-1]['runtime']['completed_ticks'] <= samples[0]['runtime']['completed_ticks']:
            raise AssertionError('Cold startup ticks did not progress')
    finally:
        client.call('study_update_settings_config',{'config':{'awareness':original}})
        restored = status_summary(client.call('study_status'))
        records = {'samples':samples,'communication':locals().get('communication'),
                   'restored_config':restored['awareness']==original,
                   'restored_active':restored['awareness_runtime']['active']}
        target.write_text(json.dumps(records,indent=2),encoding='utf-8')
        print('Scoped restoration:',records['restored_config'],flush=True)


if __name__ == '__main__':
    main()
