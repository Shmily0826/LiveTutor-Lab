"""Measure what the machine actually sent to the default output device.

`audio_deltas` in the host log only proves frames arrived at the realtime client.
WASAPI loopback on the endpoint the character plays into proves sound left the machine,
which is the difference between "a reply was generated" and "the learner heard it".
Run it with the isolated host's Python, where the capture package lives.
"""
from __future__ import annotations

import argparse
import array
import json
import math
import struct
import subprocess
import sys
import time
import wave
from pathlib import Path

import pyaudiowpatch as pa

THRESHOLD = 0.02  # peak above this is audible signal, not the noise floor


def peak_and_rms(samples: list[int]) -> tuple[float, float]:
    if not samples:
        return 0.0, 0.0
    full = float(2 ** 15 - 1)
    worst = max(abs(value) for value in samples) / full
    mean = math.sqrt(sum(value * value for value in samples) / len(samples)) / full
    return round(worst, 4), round(mean, 5)


def pick_loopback(audio: pa.PyAudio, name: str = "") -> dict:
    """The loopback tap for one render endpoint - by name, or the current default."""
    if not name:
        return audio.get_default_wasapi_loopback()
    devices = list(audio.get_loopback_device_info_generator())
    for device in devices:
        if name.lower() in device["name"].lower():
            return device
    raise RuntimeError(f"no loopback endpoint matching {name!r}; available: "
                       f"{[d['name'] for d in devices]}")


def capture(seconds: float, chunk_seconds: float = 0.25, device_name: str = "") -> tuple[list[int], list[dict], dict]:
    """Record the loopback of the current default output; no callback thread involved."""
    with pa.PyAudio() as audio:
        device = pick_loopback(audio, device_name)
        rate = int(device["defaultSampleRate"])
        channels = int(device["maxInputChannels"])
        chunk = max(1, int(rate * chunk_seconds))
        stream = audio.open(format=pa.paInt16, channels=channels, rate=rate, input=True,
                            input_device_index=device["index"], frames_per_buffer=chunk)
        started = time.time()
        deadline = time.monotonic() + seconds
        levels: list[int] = []
        while time.monotonic() < deadline:
            data = stream.read(chunk, exception_on_overflow=False)
            levels.extend(struct.unpack(f"<{len(data) // 2}h", data))
        stream.stop_stream()
        stream.close()
    curve = []
    step = chunk * channels
    for index in range(0, len(levels), step):
        window = levels[index:index + step]
        peak, rms = peak_and_rms(window)
        curve.append({"at": round(index / (rate * channels), 2), "peak": peak, "rms": rms})
    info = {"loopback_device": device["name"], "rate": rate, "channels": channels,
            "capture_start_wall": started, "chunk_seconds": chunk_seconds,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started))}
    return levels, curve, info


def write_wav(path: Path, samples: list[int], rate: int, channels: int) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(array.array("h", samples).tobytes())


def read_capture(seconds: float) -> dict:
    """Ask a separate process to capture, so PortAudio is never used twice at once."""
    output = subprocess.run([sys.executable, str(Path(__file__)), "--seconds", str(seconds)],
                            capture_output=True, text=True, encoding="utf-8", check=True).stdout
    return json.loads(output)


def self_test() -> dict:
    """Silence first, then a tone played *during* a capture, in two processes."""
    baseline = read_capture(1.5)
    capture_process = subprocess.Popen(
        [sys.executable, str(Path(__file__)), "--seconds", "3"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
    time.sleep(0.5)
    tone_started = time.monotonic()
    with pa.PyAudio() as audio:
        rate = int(audio.get_default_output_device_info()["defaultSampleRate"])
        tone = array.array("h", [int(3200 * math.sin(2 * math.pi * 440 * n / rate))
                                 for n in range(int(rate * 1.6))])
        stream = audio.open(format=pa.paInt16, channels=1, rate=rate, output=True)
        stream.write(tone.tobytes())
        stream.stop_stream()
        stream.close()
    heard = json.loads(capture_process.communicate()[0])
    return {"loopback_device": heard["device"]["loopback_device"],
            "silence_peak": baseline["max_peak"], "tone_peak": heard["max_peak"],
            "meter_works": heard["max_peak"] > max(baseline["max_peak"] * 3, THRESHOLD),
            "tone_played_at": round(tone_started, 3)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=0.0)
    parser.add_argument("--device", default="", help="loopback endpoint to tap (default: the render default)")
    parser.add_argument("--list", action="store_true", help="show every loopback endpoint and exit")
    parser.add_argument("--out", default="", help="write the captured signal here (wav)")
    args = parser.parse_args()
    if args.list:
        with pa.PyAudio() as audio:
            print(json.dumps({"loopback_endpoints": [device["name"] for device in
                                                      audio.get_loopback_device_info_generator()],
                              "default": audio.get_default_wasapi_loopback()["name"]},
                             ensure_ascii=False))
        return 0
    if args.seconds <= 0:
        print(json.dumps(self_test(), ensure_ascii=False))
        return 0
    levels, curve, info = capture(args.seconds, device_name=args.device)
    peaks = [point["peak"] for point in curve]
    record = {"device": info, "chunks": len(curve), "max_peak": max(peaks, default=0.0),
              "loud_chunks": sum(1 for value in peaks if value > THRESHOLD),
              "first_loud_at": next((point["at"] for point in curve if point["peak"] > THRESHOLD), None),
              "curve": curve}
    if args.out and levels:
        write_wav(Path(args.out), levels, int(info["rate"]), int(info["channels"]))
        record["wav"] = args.out
    record["curve"] = record["curve"][:60]
    print(json.dumps(record, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
