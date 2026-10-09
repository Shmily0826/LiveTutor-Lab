"""Bounded delivery-path bootstrap for the inspected embedded frozen host.

This temporary hook starts only the missing message components. It does not run
the full server startup, clear registrations, or read provider credentials.
"""
import asyncio
import multiprocessing

_lifecycle = None
_original_ensure = None
_gate = None
_ready = False
_START_TIMEOUT = 5.0


async def _ensure_delivery():
    global _ready
    async with _gate:
        if _ready:
            return True
        async def start():
            service = _lifecycle._service
            if service._message_plane_runner is None:
                await service._start_message_plane()
            if service._message_plane_runner is None:
                raise RuntimeError('Message plane did not initialize')
            from plugin.server.messaging import plane_bridge
            refresh = getattr(plane_bridge, 'refresh_ingest_endpoint', None)
            if callable(refresh):
                refresh()
            await asyncio.to_thread(_lifecycle.start_bridge)
            await asyncio.to_thread(_lifecycle.start_proactive_bridge)
            await _lifecycle.bus_subscription_manager.start()
        await asyncio.wait_for(start(),timeout=_START_TIMEOUT)
        _ready = True
        return True


async def _ensure_messaging():
    await _original_ensure()
    try:
        return await _ensure_delivery()
    except Exception as error:
        _lifecycle.logger.warning('Lab delivery-path bootstrap unavailable: {}',type(error).__name__)
        return False


def install():
    global _lifecycle, _original_ensure, _gate
    if multiprocessing.current_process().name != 'MainProcess' or _original_ensure is not None:
        return
    from plugin.server import lifecycle
    from plugin.server.routes import plugins
    from plugin.server.messaging.request_router import plugin_router
    _lifecycle = lifecycle
    _original_ensure = lifecycle.ensure_plugin_messaging_started
    _gate = asyncio.Lock()
    lifecycle.ensure_plugin_messaging_started = _ensure_messaging
    plugins.ensure_plugin_messaging_started = _ensure_messaging
    task = getattr(plugin_router,'_router_task',None)
    if task is not None and task.get_loop().is_running():
        future = asyncio.run_coroutine_threadsafe(_ensure_messaging(),task.get_loop())
        # Retrieve failures; the coroutine logs a sanitized degradation result.
        future.add_done_callback(lambda finished: finished.exception() if not finished.cancelled() else None)
