"""Temporary Study-only compatibility hook for the inspected frozen host.

Prefer host-loop.patch in a source build. This hook needs identical importable
copies at both documented plugin roots and a backend restart to remove it.
"""
import asyncio
import threading
import atexit
import multiprocessing

_compiled_runner = None
_enabled_plugins = {'study_lab_loop_probe', 'study_companion'}
_runner_active = False
_child_runner = None
_child_original_run = None
_child_owner_thread = None


def _run_on_loop(runner, owner_thread, awaitable, *, debug=None):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        if asyncio.iscoroutine(awaitable):
            awaitable.close()
        raise RuntimeError('asyncio.run() cannot be called from a running event loop')
    if threading.get_ident() != owner_thread:
        return asyncio.run_coroutine_threadsafe(awaitable, runner.get_loop()).result()
    if debug is not None:
        runner.get_loop().set_debug(debug)
    return runner.run(awaitable)


def _child_run(awaitable, *, debug=None):
    return _run_on_loop(_child_runner,_child_owner_thread,awaitable,debug=debug)


def _close_child_loop():
    global _child_runner
    if _child_runner is None:
        return
    if asyncio.run is _child_run:
        asyncio.run = _child_original_run
    runner, _child_runner = _child_runner, None
    runner.close()


def _install_child_loop():
    global _child_runner, _child_original_run, _child_owner_thread
    if _runner_active or _child_runner is not None:
        return
    _child_runner = asyncio.Runner()
    _child_owner_thread = threading.get_ident()
    _child_original_run = asyncio.run
    asyncio.run = _child_run
    atexit.register(_close_child_loop)


def _plugin_runner(*args, **kwargs):
    global _compiled_runner, _runner_active
    if _compiled_runner is None:
        from plugin.core import host
        _compiled_runner = host._plugin_process_runner
        if _compiled_runner is _plugin_runner:
            raise RuntimeError('Original frozen host runner is unavailable')
    plugin_id = args[0] if args else kwargs.get('plugin_id')
    if plugin_id not in _enabled_plugins:
        return _compiled_runner(*args, **kwargs)
    original_run = asyncio.run
    owner_thread = threading.get_ident()
    with asyncio.Runner() as runner:
        def run_on_process_loop(awaitable, *, debug=None):
            return _run_on_loop(runner,owner_thread,awaitable,debug=debug)
        _runner_active = True
        asyncio.run = run_on_process_loop
        try:
            return _compiled_runner(*args, **kwargs)
        finally:
            asyncio.run = original_run
            _runner_active = False


def install(plugin_id):
    global _compiled_runner
    from plugin.core import host
    if multiprocessing.current_process().name != 'MainProcess':
        _install_child_loop()
    _enabled_plugins.add(plugin_id)
    if host._plugin_process_runner is _plugin_runner:
        return
    if _compiled_runner is not None and host._plugin_process_runner is not _compiled_runner:
        raise RuntimeError('Host runner changed after compatibility installation')
    _compiled_runner = host._plugin_process_runner
    host._plugin_process_runner = _plugin_runner
