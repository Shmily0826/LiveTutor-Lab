"""Persist a bounded read-mode cold-start fixture and save scoped rollback."""
import json
from neko_lab_client import LabClient,status_summary
from neko_lab_stage import ROOT


def main():
    target = ROOT/'benchmarks/raw/evidence/goal-cold-original-awareness.json'
    if target.exists():
        raise RuntimeError('Cold-start backup exists; do not overwrite it')
    client = LabClient()
    original = status_summary(client.call('study_status'))['awareness']
    target.write_text(json.dumps(original,indent=2),encoding='utf-8')
    client.call('study_update_settings_config',{'config':{'awareness':{
        **original,'enabled':True,'snapshot_interval_seconds':2,
        'push_to_llm_mode':'read','push_to_llm_interval_seconds':30}}})
    print(client.request('/plugin/study_companion/stop','POST',{}))


if __name__ == '__main__':
    main()
