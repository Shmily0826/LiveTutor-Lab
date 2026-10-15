"""Bounded, unsent PCM collector; no ASR, provider, DSP or output ownership changes.

Feed already scored 16 kHz mono PCM16 after the caller's real VAD/onset path.
Capture timestamps, tick timestamps and the injected clock share one timebase.
The caller still owns connection/permission checks and the eventual single writer.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
import time
from typing import Callable, Hashable
import uuid

SAMPLE_RATE = 16_000
BYTES_PER_SAMPLE = 2


@dataclass(frozen=True, slots=True)
class PhraseOwnership:
    session_id: str
    owner_token: Hashable
    connection_generation: int

    def __post_init__(self):
        if not isinstance(self.session_id, str) or not self.session_id:
            raise ValueError("session_id must be explicit")
        if self.owner_token is None:
            raise ValueError("owner_token must be explicit and immutable")
        hash(self.owner_token)
        if type(self.connection_generation) is not int or self.connection_generation < 0:
            raise ValueError("connection_generation must be a nonnegative integer")


class PhraseState(str, Enum):
    OPEN = "open"
    SEALED = "sealed"
    TAKEN = "taken"
    FAILED = "failed"
    CLOSED = "closed"


class PhraseBufferError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class SealedPhrase:
    local_phrase_id: str  # Collector transaction only; never a provider utterance ID.
    ownership: PhraseOwnership
    pcm16: bytes
    source_samples: int
    output_samples: int
    compressed_zero_samples: int
    captured_start: float
    speech_end_at: float
    sealed_at: float
    compressed_zero_intervals: tuple[tuple[int, int], ...] = ()  # Source sample offsets, end exclusive.
    compressed_intervals_truncated: bool = False


class PhraseInputBuffer:
    def __init__(self, ownership: PhraseOwnership, *, clock: Callable[[], float] = time.monotonic,
                 quiet_seconds: float = 1.2, max_seconds: float = 20.0,
                 max_bytes: int = 640_000, internal_zero_seconds: float = .1):
        if not isinstance(ownership, PhraseOwnership):
            raise ValueError("explicit PhraseOwnership required")
        for value in (quiet_seconds, max_seconds, internal_zero_seconds):
            if not math.isfinite(value) or value <= 0:
                raise ValueError("duration limits must be finite and positive")
        if internal_zero_seconds >= quiet_seconds or type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError("invalid pause or byte limit")
        self.ownership = ownership
        self.local_phrase_id = "local_phrase_" + uuid.uuid4().hex
        self.state = PhraseState.OPEN
        self.failure_reason = ""
        self._clock = clock
        self.quiet_seconds = quiet_seconds
        self.max_seconds = max_seconds
        self.max_bytes = max_bytes
        self._zero_keep_bytes = max(2, int(internal_zero_seconds * SAMPLE_RATE) * 2)
        self._pcm = bytearray()
        self._zero_pending_bytes = 0
        self._zero_pending_start = None
        self._compressed_intervals = []
        self._compressed_intervals_truncated = False
        self._source_bytes = 0
        self._compressed_zero_bytes = 0
        self.peak_buffered_bytes = 0
        self._start = None
        self._last_capture = None
        self._last_end = None
        self._speech_end = None
        self._quiet_since = None
        self._sealed = None

    @property
    def buffered_bytes(self) -> int:
        return len(self._pcm) + self._zero_pending_bytes + (len(self._sealed.pcm16) if self._sealed else 0)

    def _fail(self, code: str):
        self.state = PhraseState.FAILED
        self.failure_reason = code
        self._pcm.clear()
        self._zero_pending_bytes = 0
        self._zero_pending_start = None
        self._compressed_intervals.clear()
        self._sealed = None
        raise PhraseBufferError(code)

    def assert_current(self, ownership: PhraseOwnership) -> None:
        """The integration writer must recheck real authority at every await."""
        if ownership != self.ownership:
            self._fail("ownership_changed")
        if self.state in (PhraseState.FAILED, PhraseState.CLOSED):
            raise PhraseBufferError(self.failure_reason or "phrase_closed")

    def _time(self, when: float | None) -> float:
        value = self._clock() if when is None else when
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            self._fail("invalid_capture_time")
        return float(value)

    def feed(self, pcm16: bytes, *, speech_active: bool, ownership: PhraseOwnership,
             captured_at: float | None = None) -> PhraseState:
        self.assert_current(ownership)
        if self.state is not PhraseState.OPEN:
            raise PhraseBufferError("phrase_not_open")
        if not isinstance(pcm16, bytes) or not pcm16 or len(pcm16) % 2:
            self._fail("invalid_pcm16_frame")
        if type(speech_active) is not bool:
            self._fail("speech_verdict_required")
        when = self._time(captured_at)
        if self._last_capture is not None and when < self._last_capture:
            self._fail("capture_time_reversed")
        start = self._start if self._start is not None else when
        end = when + len(pcm16) / (SAMPLE_RATE * BYTES_PER_SAMPLE)
        # Count the original input, not its compressed representation. Never
        # evict the beginning or treat compression as permission for a longer turn.
        if self._source_bytes + len(pcm16) > self.max_bytes:
            self._fail("phrase_byte_limit")
        if (self._source_bytes + len(pcm16)) / 32_000 > self.max_seconds or end - start > self.max_seconds + 1e-9:
            self._fail("phrase_duration_limit")
        self._start = start
        self._last_capture = when
        self._last_end = end
        self._source_bytes += len(pcm16)
        if not speech_active and not any(pcm16):
            # Exact all-zero PCM only. Quiet bytes need not be allocated until
            # we know whether this is an internal pause or the terminal tail.
            if self._zero_pending_bytes == 0:
                self._zero_pending_start = (self._source_bytes - len(pcm16)) // 2
            self._zero_pending_bytes += len(pcm16)
        else:
            self._flush_zero_pause(internal=True)
            self._pcm.extend(pcm16)  # Includes VAD-false weak/nonzero speech unchanged.
        self.peak_buffered_bytes = max(self.peak_buffered_bytes, self.buffered_bytes)
        if speech_active:
            self._speech_end = end
            self._quiet_since = None
        elif self._speech_end is not None and self._quiet_since is None:
            self._quiet_since = max(when, self._speech_end)
        return self.tick(ownership=ownership, now=end)

    def _flush_zero_pause(self, *, internal: bool):
        keep = self._zero_pending_bytes
        # Leading silence and trailing silence are kept; only a zero pause
        # followed by another retained frame within this phrase can shrink.
        if internal and self._speech_end is not None:
            keep = min(keep, self._zero_keep_bytes)
        if keep < self._zero_pending_bytes:
            if len(self._compressed_intervals) < 32:
                self._compressed_intervals.append((self._zero_pending_start + keep // 2,
                                                   self._zero_pending_start + self._zero_pending_bytes // 2))
            else:
                self._compressed_intervals_truncated = True
        self._compressed_zero_bytes += self._zero_pending_bytes - keep
        self._pcm.extend(bytes(keep))
        self._zero_pending_bytes = 0
        self._zero_pending_start = None

    def tick(self, *, ownership: PhraseOwnership, now: float | None = None) -> PhraseState:
        self.assert_current(ownership)
        if self.state is not PhraseState.OPEN:
            return self.state
        when = self._time(now)
        if self._last_end is not None and when < self._last_end - 1e-9:
            self._fail("clock_before_capture_end")
        if self._start is not None and when - self._start > self.max_seconds + 1e-9:
            self._fail("phrase_duration_limit")
        if self._quiet_since is not None and when - self._quiet_since >= self.quiet_seconds - 1e-9:
            self._flush_zero_pause(internal=False)
            pcm = bytes(self._pcm)
            self._pcm.clear()
            self._sealed = SealedPhrase(self.local_phrase_id, self.ownership, pcm,
                self._source_bytes // 2, len(pcm) // 2, self._compressed_zero_bytes // 2,
                self._start, self._speech_end, when, tuple(self._compressed_intervals),
                self._compressed_intervals_truncated)
            self.state = PhraseState.SEALED
        return self.state

    def take(self, *, ownership: PhraseOwnership) -> SealedPhrase:
        """Transfer one immutable unsent batch once. This does not write audio."""
        self.assert_current(ownership)
        if self.state is not PhraseState.SEALED:
            raise PhraseBufferError("phrase_not_sealed_or_already_taken")
        result = self._sealed
        self._sealed = None
        self.state = PhraseState.TAKEN
        return result

    def close(self) -> None:
        self._pcm.clear()
        self._zero_pending_bytes = 0
        self._zero_pending_start = None
        self._compressed_intervals.clear()
        self._sealed = None
        self.state = PhraseState.CLOSED
        self.failure_reason = "phrase_closed"
