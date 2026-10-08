"""Validate the scoped loop compatibility hook before any Study deployment."""
from pathlib import Path
import shutil
from neko_lab_stage import LIVE, ROOT
from neko_lab_client import LabClient

PLUGIN = 'study_lab_loop_probe'


def main():
    roots = (LIVE.parent,LIVE.parents[2]/'plugins')
    source = '''from plugins.lab_study_runtime import install
install("study_lab_loop_probe")
from plugin.sdk.plugin import NekoPluginBase, neko_plugin, plugin_entry, lifecycle, Ok
import asyncio
@neko_plugin
class Plugin(NekoPluginBase):
    @lifecycle(id="startup")
    async def startup(self, **_):
        self.ticks = 0
        async def observe():
            while True:
                self.ticks += 1
                await asyncio.sleep(0.2)
        self.background = asyncio.create_task(observe())
        await asyncio.sleep(0)
        return Ok({"status":"ready"})
    @lifecycle(id="shutdown")
    async def shutdown(self, **_):
        self.background.cancel()
        await asyncio.gather(self.background,return_exceptions=True)
        return Ok({"status":"stopped"})
    @plugin_entry(id="probe",name="Read loop state",description="Local diagnostics",
                  input_schema={"type":"object","properties":{}})
    async def probe(self, **_):
        return Ok({"ticks":self.ticks,"active":not self.background.done()})
'''
    for root in roots:
        root.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/'scripts/neko_lab_runtime_loop.py',root/'lab_study_runtime.py')
        directory = root/PLUGIN
        directory.mkdir(exist_ok=True)
        (directory/'__init__.py').write_text(source,encoding='utf-8')
    template = (LIVE.parent/'study_lab_probe_clean/plugin.toml').read_text(encoding='utf-8')
    (roots[0]/PLUGIN/'plugin.toml').write_text(template.replace('study_lab_probe_clean',PLUGIN),encoding='utf-8')
    client = LabClient(plugin=PLUGIN)
    client.request('/plugins/refresh','POST',{},timeout=30)
    print(client.request(f'/plugin/{PLUGIN}/start','POST',{},timeout=30))
    print(client.call('probe'))
    # Parent metadata import installs the hook; the following spawn exercises it.
    client.request(f'/plugin/{PLUGIN}/stop','POST',{},timeout=30)
    print(client.request(f'/plugin/{PLUGIN}/start','POST',{},timeout=30))
    for _ in range(3):
        import time
        time.sleep(1)
        print(client.call('probe'))


if __name__ == '__main__':
    main()
