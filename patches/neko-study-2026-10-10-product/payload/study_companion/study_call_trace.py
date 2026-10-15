"""Per-call stage timings; never record learner text or source contents."""
from contextlib import contextmanager
from contextvars import ContextVar
import json
import time
import uuid

_current = ContextVar('study_code_call_trace', default=None)


@contextmanager
def trace_call(logger):
    trace = {'id': uuid.uuid4().hex[:12], 'start': time.perf_counter(), 'stages': []}
    token = _current.set(trace)
    try:
        yield trace
    finally:
        _current.reset(token)
        if logger is not None:
            record = {'id': trace['id'], 'total_ms': round((time.perf_counter() - trace['start']) * 1000, 3),
                      'stages': trace['stages']}
            try:
                logger.info('study_code_timing ' + json.dumps(record, separators=(',', ':')))
            except Exception:
                pass  # Timing must not replace a teaching result or cancellation.


@contextmanager
def phase(name):
    trace = _current.get()
    if trace is None:
        yield
        return
    began = time.perf_counter()
    outcome = 'ok'
    try:
        yield
    except BaseException:
        outcome = 'error'
        raise
    finally:
        trace['stages'].append({'name': name, 'at_ms': round((began - trace['start']) * 1000, 3),
                                'elapsed_ms': round((time.perf_counter() - began) * 1000, 3),
                                'outcome': outcome})
