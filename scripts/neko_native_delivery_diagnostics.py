"""Default-OFF, bounded numeric observation of existing native audio methods.

These counters show method boundaries, not a provider ACK or a drop reason.
Install only on the task's actual loaded classes; no runtime imports or devices.
"""
from __future__ import annotations

import asyncio
import functools
import inspect
import json
import logging
import os
import time

_MISSING = object()
_FAILED = object()
_FIELDS = (
    'active', 'route_native', 'owner_core', 'activation_degraded',
    'activation_required', 'activation_factory_present', 'activation_enforced',
    'noise_contract_match',
)
_METHODS = (
    ('core', '_process_microphone_stream_data', 'core_process', True),
    ('core', '_route_microphone_audio', 'core_route', True),
    ('core', '_route_microphone_audio_unfiltered', 'core_native_route', True),
    ('phrase', 'accept', 'phrase_accept', False),
    ('phrase', 'flush', 'phrase_flush', True),
    ('transport', 'stream_audio', 'native_stream_audio', True),
    ('transport', 'send_event', 'provider_audio_append', True),
)
_STAGES = frozenset(row[2] for row in _METHODS)
_EVENTS = frozenset(('entered', 'returned_true', 'returned_false', 'returned_none',
                     'returned_other', 'raised', 'cancelled'))


def _read(value, name):
    try:
        return getattr(value, name, _MISSING)
    except Exception:
        return _FAILED


def _boolean(value):
    return value if type(value) is bool else None


def safe_native_snapshot(owner):
    """Only fixed bool/unknown projections; never stringify arbitrary values."""
    factory = _read(owner, '_voice_session_activation_factory')
    present = None if factory is _MISSING or factory is _FAILED else factory is not None
    enforce = None
    match = None
    if present:
        setting = _read(factory, 'enforce')
        enforce = True if setting is _MISSING else _boolean(setting)
        expected = _boolean(_read(factory, 'noise_reduction_enabled'))
        actual = _boolean(_read(owner, '_voice_input_noise_reduction_enabled'))
        if expected is not None and actual is not None:
            match = expected == actual
    route = _read(owner, '_asr_route_mode')
    lease = _read(owner, '_voice_lease_owner')
    return {
        'active': _boolean(_read(owner, 'is_active')),
        'route_native': route == 'native' if type(route) is str else None,
        'owner_core': lease == 'core' if type(lease) is str else None,
        'activation_degraded': _boolean(_read(owner, '_voice_session_activation_degraded')),
        'activation_required': _boolean(_read(owner, '_voice_session_activation_required')),
        'activation_factory_present': present,
        'activation_enforced': enforce,
        'noise_contract_match': match,
    }


class DeliveryCounters:
    """One task-local aggregate, with a fixed key space and saturating counters."""
    def __init__(self, *, logger=None, clock=None, interval_seconds=2.0,
                 count_limit=1_000_000):
        if type(count_limit) is not int or not 1 <= count_limit <= 1_000_000:
            raise ValueError('invalid diagnostic count limit')
        if not isinstance(interval_seconds, (int, float)) or interval_seconds < 2:
            raise ValueError('diagnostic logging interval must be at least two seconds')
        self._logger = logger if logger is not None else logging.getLogger(__name__)
        self._clock = clock if clock is not None else time.monotonic
        self._interval = interval_seconds
        self._limit = count_limit
        self._next_log_at = 0.0
        self._counts = {}
        self._states = {}
        self._diagnostic_errors = 0

    def _increment(self, mapping, key):
        mapping[key] = min(self._limit, mapping.get(key, 0) + 1)

    def snapshot(self):
        return {
            'counts': {stage: dict(values) for stage, values in self._counts.items()},
            'states': {stage: {phase: {field: dict(values) for field, values in fields.items()}
                              for phase, fields in phases.items()}
                       for stage, phases in self._states.items()},
            'diagnostic_errors': self._diagnostic_errors,
        }

    def observe(self, stage, event, owner):
        if stage not in _STAGES or event not in _EVENTS:
            raise ValueError('unknown diagnostic stage or event')
        self._increment(self._counts.setdefault(stage, {}), event)
        phase = 'entry' if event == 'entered' else 'exit'
        states = self._states.setdefault(stage, {}).setdefault(phase, {})
        projection = safe_native_snapshot(owner)
        for field in _FIELDS:
            value = projection[field]
            key = 'true' if value is True else 'false' if value is False else 'unknown'
            self._increment(states.setdefault(field, {}), key)
        now = self._clock()
        if now >= self._next_log_at:
            # Advance before calling the logger, including its failure path.
            self._next_log_at = now + self._interval
            self._logger.info('native delivery diagnostics %s',
                              json.dumps(self.snapshot(), sort_keys=True))

    def _observe_safely(self, stage, event, owner):
        try:
            self.observe(stage, event, owner)
        except BaseException:
            # Instrumentation must never replace the business return/exception.
            self._diagnostic_errors = min(self._limit, self._diagnostic_errors + 1)


def _outcome(value):
    if value is True:
        return 'returned_true'
    if value is False:
        return 'returned_false'
    if value is None:
        return 'returned_none'
    return 'returned_other'


def _observed_call(stage, args, kwargs):
    if stage != 'provider_audio_append':
        return True
    # Classify this exact event only; no payload fields enter the record.
    event = args[0] if args else kwargs.get('event')
    kind = event.get('type') if type(event) is dict else None
    return type(kind) is str and kind == 'input_audio_buffer.append'


def _wrap(original, stage, asynchronous, counters):
    if asynchronous:
        @functools.wraps(original)
        async def wrapper(self, *args, **kwargs):
            observed = _observed_call(stage, args, kwargs)
            if observed:
                counters._observe_safely(stage, 'entered', self)
            try:
                result = await original(self, *args, **kwargs)
            except BaseException as error:
                if observed:
                    counters._observe_safely(stage, 'cancelled' if isinstance(error, asyncio.CancelledError) else 'raised', self)
                raise
            if observed:
                counters._observe_safely(stage, _outcome(result), self)
            return result
    else:
        @functools.wraps(original)
        def wrapper(self, *args, **kwargs):
            counters._observe_safely(stage, 'entered', self)
            try:
                result = original(self, *args, **kwargs)
            except BaseException as error:
                counters._observe_safely(stage, 'cancelled' if isinstance(error, asyncio.CancelledError) else 'raised', self)
                raise
            counters._observe_safely(stage, _outcome(result), self)
            return result
    wrapper._neko_native_delivery_counters = counters
    return wrapper


def install_native_delivery_diagnostics(asr_class, phrase_class=None, transport_class=None,
                                        *, enabled=None, logger=None):
    """Wrap actual classes once when explicitly ON; OFF changes no identities.

    Return the aggregate for a local task report, or None when disabled.
    Existing method arguments, guards, owners, and scheduling are untouched.
    """
    if enabled is None:
        enabled = os.environ.get('NEKO_NATIVE_DELIVERY_DIAGNOSTICS') == '1'
    if enabled is not True:
        return None
    classes = {'core': asr_class, 'phrase': phrase_class, 'transport': transport_class}
    pending = []
    counters = None
    for group, method, stage, asynchronous in _METHODS:
        cls = classes[group]
        if cls is None:
            continue
        original = getattr(cls, method)
        if inspect.iscoroutinefunction(original) is not asynchronous:
            raise ValueError('unexpected diagnostic method kind')
        existing = getattr(original, '_neko_native_delivery_counters', None)
        if existing is not None:
            if counters is not None and counters is not existing:
                raise ValueError('diagnostic installations differ')
            counters = existing
        else:
            pending.append((cls, method, stage, asynchronous, original))
    if counters is None:
        counters = DeliveryCounters(logger=logger)
    for cls, method, stage, asynchronous, original in pending:
        setattr(cls, method, _wrap(original, stage, asynchronous, counters))
    return counters
