"""Separate synchronous and asynchronous source-handler startup behavior."""
from pathlib import Path
import json
import urllib.error
from neko_lab_client import LabClient
from neko_lab_stage import LIVE


def main():
    directory = LIVE.parent / 'study_lab_sync_probe'
    directory.mkdir(exist_ok=True)
    (directory / '__init__.py').write_text('''from plugin.sdk.plugin import NekoPluginBase, neko_plugin, plugin_entry, lifecycle, Ok
@neko_plugin
class LabProbe(NekoPluginBase):
    @lifecycle(id="startup")
    def startup(self, **_):
        return Ok({"status":"ready"})
    @lifecycle(id="shutdown")
    def shutdown(self, **_):
        return Ok({"status":"stopped"})
    @plugin_entry(id="probe", name="Probe", description="Synchronous handler probe")
    def probe(self, **_):
        return Ok({"pong":True})
''', encoding='utf-8')
    template = (LIVE.parent / 'study_lab_probe/plugin.toml').read_text(encoding='utf-8')
    (directory / 'plugin.toml').write_text(template.replace('study_lab_probe','study_lab_sync_probe'),encoding='utf-8')
    client = LabClient(plugin='study_lab_sync_probe')
    client.request('/plugins/refresh','POST',{},timeout=30)
    try:
        print(json.dumps(client.request('/plugin/study_lab_sync_probe/start','POST',{},timeout=30)))
        print(json.dumps(client.call('probe')))
    except urllib.error.HTTPError as error:
        print(error.code,error.read(1000).decode())


if __name__ == '__main__':
    main()
