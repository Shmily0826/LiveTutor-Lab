"""Stage 1 acceptance: correlate an awareness proactive message with the character UI.

What it does, in order:
  1. records the baseline awareness config and Main-log length,
  2. enables awareness with push_to_llm_mode=respond and a short interval,
  3. while it runs, samples study_status + the Main log for the delivery chain
     (submitted -> trigger_agent_callbacks -> agent_callback_turn),
  4. reports whether the session was live (`goodbye_silent`) at push time,
  5. ALWAYS restores the original awareness config in a finally block.

It does NOT touch the database, does not read credentials, and does not send a
user message. Driving the character chat panel (to clear goodbye_silent) is left
to the caller because it needs the desktop unobstructed.

Usage: neko_lab_stage1_acceptance.py [--seconds 60] [--tag STAGE1]
"""
import argparse
import json
import re
import time
from pathlib import Path

from neko_lab_client import LabClient, status_summary
from neko_lab_stage import ROOT

MAIN_LOG = ROOT / 'benchmarks/raw/neko-store/logs/N.E.K.O_Main_20261008.log'
EVIDENCE = ROOT / 'benchmarks/raw/evidence'

CHAIN_PATTERNS = {
    'submitted_proactive': r'submitting proactive callback to delivery manager',
    'enqueued_passive': r'enqueued callback \(passive\)',
    'hud_suppressed': r'agent_notification suppressed by visibility',
    'hud_sent': r'agent_notification sent to frontend',
    'callback_enter': r'trigger_agent_callbacks enter',
    'callback_deferred_goodbye': r'deferred: goodbye silent',
    'callback_deferred_takeover': r'deferred: session takeover',
    'callback_turn': r'agent_callback_turn=True',
    'rerouted': r'proactive_message rerouted',
    'goodbye_true': r'goodbye_silent=True',
    'goodbye_false': r'goodbye_silent=False',
}


def read_log():
    if not MAIN_LOG.exists():
        return ''
    return MAIN_LOG.read_text(encoding='utf-8', errors='replace')


def analyze(text):
    counts = {}
    for name, pattern in CHAIN_PATTERNS.items():
        counts[name] = len(re.findall(pattern, text, re.IGNORECASE))
    return counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=int, default=60)
    parser.add_argument('--tag', default='stage1')
    options = parser.parse_args()

    client = LabClient()
    original = status_summary(client.call('study_status'))['awareness']
    before_text = read_log()
    before_counts = analyze(before_text)

    evidence = {'tag': options.tag, 'original_awareness': original,
                'before_counts': before_counts, 'samples': []}
    target = EVIDENCE / f'goal-{options.tag}-acceptance.json'

    try:
        enabled = {**original, 'enabled': True, 'snapshot_interval_seconds': 1,
                   'push_to_llm_interval_seconds': 30, 'push_to_llm_mode': 'respond'}
        result = client.call('study_update_settings_config',
                             {'config': {'awareness': enabled}})
        payload = result['data'].get('data', result['data'])
        evidence['settings_awareness'] = payload.get('config', {}).get('awareness')
        evidence['communication'] = payload.get('communication_status')

        deadline = time.time() + options.seconds
        while time.time() < deadline:
            time.sleep(5)
            state = status_summary(client.call('study_status'))
            sample = {'runtime': state['awareness_runtime'],
                      'sensor_available': state['supervision']['sensor_available'],
                      'classification_count': state['classification_count']}
            evidence['samples'].append(sample)
            print(json.dumps(sample, ensure_ascii=False), flush=True)
            target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2),
                              encoding='utf-8')
    finally:
        client.call('study_update_settings_config',
                    {'config': {'awareness': original}})
        restored = status_summary(client.call('study_status'))
        evidence['restored_config'] = restored['awareness'] == original
        evidence['restored_runtime'] = restored['awareness_runtime']

        after_text = read_log()
        after_counts = analyze(after_text)
        evidence['after_counts'] = after_counts
        evidence['delta'] = {k: after_counts[k] - before_counts.get(k, 0)
                             for k in after_counts}

        new_lines = after_text[len(before_text):].splitlines()
        evidence['new_log_lines'] = [line for line in new_lines
                                     if re.search(r'proactive|callback|goodbye_silent|'
                                                  r'agent_notification|rerouted', line, re.I)][-60:]
        target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2),
                          encoding='utf-8')
        print('restored:', evidence['restored_config'],
              'delta:', json.dumps(evidence['delta'], ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
