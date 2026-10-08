"""Inspect only message-plane lifecycle capability names in the actual host."""
from neko_lab_stage import LIVE, ROOT
from neko_lab_client import LabClient


def main():
    source = '''import json, os, threading, traceback, inspect
from pathlib import Path
from plugin.server import lifecycle
from plugin.server.messaging.request_router import plugin_router
service = getattr(lifecycle, "_service", None)
task = getattr(plugin_router, "_router_task", None)
result = {"pid":os.getpid(),"thread":threading.current_thread().name,
          "service_methods":[n for n in dir(service) if "start" in n or "delivery" in n or "plane" in n],
          "module_methods":[n for n in dir(lifecycle) if "start" in n or "bridge" in n or "subscription" in n],
          "router_loop_running":task.get_loop().is_running() if task is not None else False,
          "plane_runner_present":getattr(service,"_message_plane_runner",None) is not None,
          "signatures":{name:str(inspect.signature(getattr(lifecycle,name))) for name in
                        ("start_bridge","start_proactive_bridge","ensure_plugin_messaging_started")},
          "plane_signature":str(inspect.signature(service._start_message_plane)),
          "subscription_signature":str(inspect.signature(lifecycle.bus_subscription_manager.start)),
          "stack":[frame.name for frame in traceback.extract_stack()[-8:]]}
Path(r"D:/CODE/project/LiveTutor-Lab/benchmarks/raw/evidence/goal-plane-capabilities-"+str(os.getpid())+".json").write_text(json.dumps(result,indent=2),encoding="utf-8")
from . import Plugin
'''
    for root in (LIVE.parent,LIVE.parents[2]/'plugins'):
        (root/'study_lab_probe_clean/lab_plane_info.py').write_text(source,encoding='utf-8')
    manifest = LIVE.parent/'study_lab_probe_clean/plugin.toml'
    text = manifest.read_text(encoding='utf-8').replace('plugins.study_lab_probe_clean.lab_plane:Plugin',
        'plugins.study_lab_probe_clean.lab_plane_info:Plugin')
    manifest.write_text(text,encoding='utf-8')
    client = LabClient(plugin='study_lab_probe_clean')
    client.request('/plugin/study_lab_probe_clean/stop','POST',{})
    client.request('/plugins/refresh','POST',{},timeout=30)
    print(client.request('/plugin/study_lab_probe_clean/start','POST',{},timeout=30))


if __name__ == '__main__':
    main()
