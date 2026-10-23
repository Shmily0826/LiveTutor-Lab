"""Fixed WAV + screen pixels through the actual N.E.K.O application protocol.

This client captures provider output without any microphone or speaker device.
The separately started product host owns credentials, prompts and egress guard.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import io
import json
from pathlib import Path
import time
import urllib.parse
import wave

import numpy as np
from PIL import Image
import soxr
import websockets

ROOT = Path(__file__).resolve().parents[1]


async def main(args):
    ledger = ROOT / "benchmarks/raw/neko-desktop-egress-cap"
    report = {"before": json.loads(ledger.read_text()), "room_microphone": False,
              "playback": False, "input": "fixed WAV and screen pixels",
              "events": [], "audio_bytes": 0}
    started = asyncio.Event()
    reply_done = asyncio.Event()
    failed = asyncio.Event()
    last_output = 0.0
    plan = json.loads(args.plan.read_text(encoding="utf-8")) if args.plan else [
        {"image": str(args.image), "wav": str(args.wav)}]
    report["steps"] = []

    async with websockets.connect("ws://127.0.0.1:48911/ws/" + urllib.parse.quote(args.character),
                                  proxy=None, max_size=5*1024*1024) as socket:
        async def receive():
            nonlocal last_output
            async for frame in socket:
                last_output = time.monotonic()
                if isinstance(frame, bytes):
                    report["audio_bytes"] += len(frame)
                    continue
                event = json.loads(frame)
                if event.get("type") != "audio_chunk":
                    report["events"].append(event)
                if event.get("type") == "session_started":
                    started.set()
                if event.get("type") in ("session_failed", "session_ended_by_server"):
                    failed.set()
                    started.set()
                    reply_done.set()
                if event.get("type") == "system" and event.get("data") == "turn end":
                    reply_done.set()
        receiver = asyncio.create_task(receive())
        async def send(value):
            await socket.send(json.dumps(value, ensure_ascii=False))
        try:
            await send({"action": "start_session", "input_type": "audio", "language": "zh-CN",
                        "new_session": False, "independent_asr_enabled": False})
            await asyncio.wait_for(started.wait(), 45)
            if failed.is_set():
                raise RuntimeError("actual product voice session failed")
            for index, step in enumerate(plan):
                image_path, wav_path = Path(step["image"]), Path(step["wav"])
                with Image.open(image_path) as image:
                    buf = io.BytesIO()
                    image.convert("RGB").save(buf, "JPEG", quality=95)
                    image_size = list(image.size)
                raw = buf.getvalue()
                with wave.open(str(wav_path)) as wav:
                    assert wav.getsampwidth() == 2
                    data = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2").astype(np.float32)
                    if wav.getnchannels() > 1:
                        data = data.reshape(-1, wav.getnchannels()).mean(axis=1)
                    data = soxr.resample(data, wav.getframerate(), 48000).astype("<i2")
                data = np.concatenate((np.zeros(48000, dtype="<i2"), data, np.zeros(144000, dtype="<i2")))
                record = {**step, "image_size": image_size, "image_sha256": hashlib.sha256(raw).hexdigest(),
                          "wav_sha256": hashlib.sha256(wav_path.read_bytes()).hexdigest(),
                          "events_from": len(report["events"]), "audio_from": report["audio_bytes"]}
                report["steps"].append(record)
                await send({"action": "stream_data", "input_type": "screen",
                            "data": "data:image/jpeg;base64,"+base64.b64encode(raw).decode(),
                            "request_id": f"diagram-vision-20261013-{index}"})
                await asyncio.sleep(1)
                # Match the product's live screen sharing: keep the selected
                # current frame fresh during the utterance, including onset.
                async def screen_frames():
                    while True:
                        await asyncio.sleep(2)
                        await send({"action": "stream_data", "input_type": "screen",
                                    "data": "data:image/jpeg;base64,"+base64.b64encode(raw).decode(),
                                    "request_id": f"diagram-vision-20261013-{index}"})
                        record["screen_refreshes"] = record.get("screen_refreshes", 0)+1
                refresher = asyncio.create_task(screen_frames())
                reply_done.clear()
                began = time.monotonic()
                for offset in range(0, len(data), 480):
                    if failed.is_set():
                        raise RuntimeError("product ended while submitting fixed audio")
                    await send({"action": "stream_data", "input_type": "audio",
                                "data": data[offset:offset+480].tolist()})
                    await asyncio.sleep(max(0, began+(offset+480)/48000-time.monotonic()))
                # Wait past intermediate sentence-level VAD completions.
                deadline = time.monotonic()+100
                while time.monotonic() < deadline:
                    if failed.is_set():
                        raise RuntimeError("product ended before final reply")
                    has_reply = any(e.get("type") == "gemini_response" and e.get("text")
                                    for e in report["events"][record["events_from"]:])
                    if has_reply and reply_done.is_set() and time.monotonic()-last_output > 5:
                        break
                    await asyncio.sleep(0.25)
                else:
                    raise TimeoutError("final reply did not settle within 100 seconds")
                record["events_to"] = len(report["events"])
                refresher.cancel()
                await asyncio.gather(refresher, return_exceptions=True)
                record["reply"] = "".join(e.get("text", "") for e in report["events"][record["events_from"]:]
                                         if e.get("type") == "gemini_response")
                record["audio_bytes"] = report["audio_bytes"]-record["audio_from"]
                args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
                print(json.dumps({"step": index, "reply": record["reply"], "audio_bytes": record["audio_bytes"]},
                                 ensure_ascii=False), flush=True)
        except Exception as exc:
            report["failure"] = type(exc).__name__ + ": " + str(exc)
        finally:
            if 'refresher' in locals():
                refresher.cancel()
                await asyncio.gather(refresher, return_exceptions=True)
            await send({"action": "end_session", "reason": "bounded_diagram_probe"})
            await asyncio.sleep(1)
            receiver.cancel()
            await asyncio.gather(receiver, return_exceptions=True)
            report["after"] = json.loads(ledger.read_text())
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
            print(json.dumps({"report": str(args.output), "failure": report.get("failure"),
                              "audio_bytes": report["audio_bytes"], "spent": report["after"]["spent"],
                              "replies": [e for e in report["events"] if e.get("type") == "gemini_response"]},
                             ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character", required=True)
    parser.add_argument("--image", type=Path)
    parser.add_argument("--wav", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(main(parser.parse_args()))
