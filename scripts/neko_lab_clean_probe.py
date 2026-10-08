"""Minimal source plugin with complete manifest and explicit entry schema."""
from pathlib import Path
import json
import urllib.error
from neko_lab_client import LabClient
from neko_lab_stage import LIVE

PLUGIN = 'study_lab_probe_clean'


def main():
    directory = LIVE.parent / PLUGIN
    directory.mkdir(exist_ok=True)
    (directory/'__init__.py').write_text('''from plugin.sdk.plugin import NekoPluginBase, neko_plugin, plugin_entry, lifecycle, Ok
import asyncio, json, time
from pathlib import Path
@neko_plugin
class Plugin(NekoPluginBase):
    @lifecycle(id="startup")
    async def startup(self, **_):
        started = time.monotonic()
        self.background = asyncio.create_task(asyncio.sleep(3600))
        def finished(task):
            Path(r"D:/CODE/project/LiveTutor-Lab/benchmarks/raw/evidence/goal-background-lifecycle.json").write_text(
                json.dumps({"cancelled":task.cancelled(), "elapsed_ms":round((time.monotonic()-started)*1000)}),encoding="utf-8")
        self.background.add_done_callback(finished)
        await asyncio.sleep(0)
        return Ok({"status":"ready", "result":{}})
    @lifecycle(id="shutdown")
    async def shutdown(self, **_):
        return Ok({"status":"stopped"})
    @plugin_entry(id="probe", name="Probe", description="Read-only probe",
                  input_schema={"type":"object", "properties":{}, "additionalProperties":True})
    async def probe(self, **_):
        return Ok({"pong":True})
''', encoding='utf-8')
    (directory/'plugin.toml').write_text(f'''[plugin]
id = "{PLUGIN}"
name = "LiveTutor Lab clean probe"
description = "Read-only diagnostic"
version = "0.1.0"
type = "plugin"
entry = "plugins.{PLUGIN}:Plugin"
[plugin.author]
name = "LiveTutor Lab"
[plugin.sdk]
recommended = ">=0.1.0,<0.2.0"
supported = ">=0.1.0,<0.3.0"
[plugin.store]
enabled = true
[plugin.database]
enabled = false
[plugin_state]
backend = "memory"
[plugin_runtime]
enabled = true
auto_start = false
''', encoding='utf-8')
    client = LabClient(plugin=PLUGIN)
    client.request('/plugins/refresh','POST',{},timeout=30)
    try:
        print('start',client.request(f'/plugin/{PLUGIN}/start','POST',{},timeout=30))
        print('probe',json.dumps(client.call('probe')))
    except urllib.error.HTTPError as error:
        print('start_error',error.code,error.read(1000).decode())


if __name__ == '__main__':
    main()
