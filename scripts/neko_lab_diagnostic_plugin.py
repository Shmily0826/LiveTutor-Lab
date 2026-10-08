"""Install an isolated local diagnostic plugin using the public plugin contract."""
from pathlib import Path
import json
import sys
from neko_lab_client import LabClient
from neko_lab_stage import LIVE

SOURCE = '''from plugin.sdk.plugin import NekoPluginBase, neko_plugin, plugin_entry, lifecycle, Ok
import json, os, sys
from pathlib import Path
from plugin.server.application.plugins import lifecycle_service as _ls
_log = Path(__file__).resolve().parents[7] / "evidence/goal-source-import-errors.jsonl"
_log = Path(r"D:/CODE/project/LiveTutor-Lab/benchmarks/raw/evidence/goal-source-import-errors.jsonl")
with _log.open("a", encoding="utf-8") as _fh:
    _fh.write(json.dumps({"pid": os.getpid(), "module": __name__,
                          "cleanup_names": [n for n in dir(_ls) if "cleanup" in n]}) + "\\n")
if hasattr(_ls, "_cleanup_started_host"):
    _original_cleanup = _ls._cleanup_started_host
    async def _diagnostic_cleanup(*args, **kwargs):
        _kind, _error, _traceback = sys.exc_info()
        if _kind is not None:
            with _log.open("a", encoding="utf-8") as _fh:
                _fh.write(json.dumps({"pid": os.getpid(), "error_type": _kind.__name__,
                                      "message": str(_error)[:500]}) + "\\n")
        return await _original_cleanup(*args, **kwargs)
    _ls._cleanup_started_host = _diagnostic_cleanup

@neko_plugin
class LabProbe(NekoPluginBase):
    @lifecycle(id="startup")
    async def startup(self, **_):
        import asyncio, time
        from dataclasses import asdict
        from plugin.sdk.plugin import get_os_activity_snapshot
        result = {"pid": os.getpid(), "helper_module": get_os_activity_snapshot.__module__}
        started = time.monotonic()
        try:
            snapshot = await asyncio.wait_for(get_os_activity_snapshot(self.plugin_id), timeout=2.0)
            result["snapshot"] = asdict(snapshot)
        except Exception as error:
            result["error_type"] = type(error).__name__
        result["elapsed_ms"] = round((time.monotonic()-started)*1000)
        Path(r"D:/CODE/project/LiveTutor-Lab/benchmarks/raw/evidence/goal-sdk-activity.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8")
        from plugin.plugins.study_companion import StudyCompanionPlugin
        if "study_lab_probe" not in str(self.data_path("study_companion.db")):
            raise RuntimeError("diagnostic study storage must be isolated")
        study = StudyCompanionPlugin(self.ctx)
        raw_config = await self.config.dump(timeout=5.0)
        raw_enabled = (raw_config.get("study") or {}).get("awareness", {}).get("enabled")
        await study.startup()
        observations = []
        target = Path(r"D:/CODE/project/LiveTutor-Lab/benchmarks/raw/evidence/goal-compiled-awareness-stack.json")
        for _index in range(4):
            await asyncio.sleep(1.0)
            task = study._awareness_task
            chain = []
            current = task.get_coro() if task else None
            for _ in range(16):
                if current is None: break
                code = getattr(current, "cr_code", None) or getattr(current, "gi_code", None)
                if code: chain.append(code.co_name)
                current = getattr(current, "cr_await", None) or getattr(current, "gi_yieldfrom", None)
            observations.append({"enabled": study._cfg.awareness.enabled,
                                 "raw_enabled": raw_enabled,
                                 "active": study.is_awareness_active(), "chain": chain,
                                 "sensor": study._supervision.status() if study._supervision else None,
                                 "buffer_count": len(study._buffer.snapshots) if study._buffer else None})
            target.write_text(json.dumps(observations, indent=2), encoding="utf-8")
        await study.shutdown()
        return Ok({"status": "ready"})

    @lifecycle(id="shutdown")
    async def shutdown(self, **_):
        return Ok({"status": "stopped"})

    @plugin_entry(id="probe", name="Runtime contract", description="Read-only SDK identity",
                  input_schema={"type":"object", "properties":{}, "additionalProperties":True})
    async def probe(self, **_):
        import dis
        from plugin.sdk.plugin import get_os_activity_snapshot
        from plugin.plugins.study_companion import StudyCompanionPlugin
        functions = {"activity": get_os_activity_snapshot,
                     "awareness": StudyCompanionPlugin.awareness_tick,
                     "subscribe": StudyCompanionPlugin._subscribe_neko_command_bus}
        return Ok({name: {"file": fn.__code__.co_filename,
                          "names": list(fn.__code__.co_names),
                          "bytecode": dis.Bytecode(fn).dis()}
                   for name, fn in functions.items()})
'''


def main():
    directory = LIVE.parent / 'study_lab_probe'
    directory.mkdir(exist_ok=True)
    (directory / '__init__.py').write_text(SOURCE, encoding='utf-8')
    manifest = '''[plugin]
id = "study_lab_probe"
name = "LiveTutor Lab diagnostics"
description = "Local SDK diagnostics for LiveTutor-Lab acceptance."
version = "0.1.0"
type = "plugin"
entry = "plugins.study_lab_probe:LabProbe"
[plugin.author]
name = "LiveTutor Lab"
[plugin.sdk]
recommended = ">=0.1.0,<0.2.0"
supported = ">=0.1.0,<0.3.0"
[plugin_runtime]
enabled = true
auto_start = false
[study.awareness]
enabled = true
[study_companion.communication]
enabled = false
'''
    if '--base-disabled' in sys.argv:
        manifest = manifest.replace('[study.awareness]\nenabled = true', '[study.awareness]\nenabled = false')
    (directory / 'plugin.toml').write_text(manifest, encoding='utf-8')
    client = LabClient(plugin='study_lab_probe')
    print(json.dumps(client.request('/plugins/refresh', 'POST', {}, timeout=30)))
    print(json.dumps(client.request('/plugin/study_lab_probe/start', 'POST', {}, timeout=30)))
    result = client.call('probe')
    # Keep runtime diagnostics alongside other ignored evidence.
    target = Path(__file__).resolve().parents[1] / 'benchmarks/raw/evidence/goal-frozen-sdk-probe.json'
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({name: {key: value for key, value in data.items() if key != 'bytecode'}
                      for name, data in result['data'].items()}, ensure_ascii=False))


if __name__ == '__main__':
    main()
