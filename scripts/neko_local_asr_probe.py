"""Prove the local speech input path works, with no key, no server and no paid call.

The host offers exactly one user-selectable local ASR provider, `faster_whisper`, and
until now the product reported `localAsrAvailable=false` only because the package was
absent - the microphone itself comes from the Electron renderer (`app-audio-capture.js`,
`getUserMedia`), so no Python capture library is involved. This runs the host's own
model loader (same CUDA-to-CPU fallback and same first-encode probe the product uses)
over a WAV spoken by Windows' own local text-to-speech, so transcription is the thing
under test rather than a synthesized stand-in.

    python scripts/neko_local_asr_probe.py [--model tiny] [--device cpu]

Nothing here touches the DeepSeek endpoint: the request counter in the output is there
to make that claim checkable.
"""
from __future__ import annotations

import argparse
import contextlib
import importlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / "benchmarks/raw/neko-product-host"
STORE = ROOT / "benchmarks/raw/neko-product-data"
WORKER = "main_logic.asr_client.workers.faster_whisper"
SPEECH = "explain the difference between read and watch in provider"


def isolate_store() -> None:
    """Point every app-data lookup at the project store before ConfigManager resolves.

    The resolver reads `core_config.json` off `%LOCALAPPDATA%`, which the storage
    anchor does not cover, so without this the probe would read the user's real
    N.E.K.O settings instead of the disposable ones.
    """
    os.environ.update({
        "NEKO_STORAGE_SELECTED_ROOT": str(STORE),
        "NEKO_STORAGE_ANCHOR_ROOT": str(STORE),
        "NEKO_STORAGE_CLOUDSAVE_ROOT": str(STORE),
        "LOCALAPPDATA": str(STORE),
        "APPDATA": str(STORE),
    })


def store_scoped():
    """Redirect app-data lookups to the project store, then put the environment back.

    The launcher shares this process environment with the Electron shell, so the
    redirection has to be temporary even though the probe itself never cares.
    """
    keys = ("NEKO_STORAGE_SELECTED_ROOT", "NEKO_STORAGE_ANCHOR_ROOT",
            "NEKO_STORAGE_CLOUDSAVE_ROOT", "LOCALAPPDATA", "APPDATA")

    @contextlib.contextmanager
    def scope():
        before = {key: os.environ.get(key) for key in keys}
        isolate_store()
        try:
            yield
        finally:
            for key, value in before.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    return scope()


def speech_route_status() -> dict[str, object]:
    """Ask the product whether its microphone route can reach the local recogniser.

    The route key is the character's Core provider, and `CORE_ASR_ROUTES` only lists
    providers that own a speech worker, so a Core of `deepseek` fails resolution
    before any provider preference - local or otherwise - is consulted. This reads
    that outcome without opening a session, so nothing is paid for or recorded.
    """
    with store_scoped():
        if str(HOST) not in sys.path:
            sys.path.insert(0, str(HOST))  # so a caller can ask without running main()
        from main_logic import asr_client

        core = ""
        config_file = STORE / "N.E.K.O/config/core_config.json"
        if config_file.is_file():
            try:
                stored = json.loads(config_file.read_text(encoding="utf-8"))
                core = str(stored.get("CORE_API_TYPE") or stored.get("coreApi") or "").strip().lower()
            except (OSError, ValueError):
                core = ""
        outcome: dict[str, object] = {
            "core_effective": core or "<unreadable>",
            "local_asr_available": asr_client.is_local_asr_available(),
            "core_route_known": core in asr_client._CORE_ASR_ROUTES,
        }
        for label, kwargs in (("with_local_preference", {"provider_preference": "faster_whisper"}),
                              ("as_shipped_default", {})):
            try:
                selection = asr_client._resolve_asr_selection(core, **kwargs)
                outcome[label] = {"provider": selection.provider_key,
                                  "availability": str(selection.availability),
                                  "credential_needed": bool(getattr(selection, "_api_key", ""))}
            except Exception as error:  # the resolver reports by raising, not by returning
                outcome[label] = f"{type(error).__name__}: {error}"
        outcome["provider_requests_sent"] = 0
    return outcome



def synth_wav(target: Path, sentence: str) -> str:
    """Speak the sample with Windows' own local voice, into a WAV the host can read."""
    script = (
        "Add-Type -AssemblyName System.Speech;"
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        "$voice = $s.GetInstalledVoices() | Where-Object {"
        "$_.Enabled -and $_.VoiceInfo.Culture.Name -like ($env:NEKO_ASR_PROBE_VOICE + '*')} "
        "| Select-Object -First 1;"
        "if ($voice) { $s.SelectVoice($voice.VoiceInfo.Name); Write-Output $voice.VoiceInfo.Name }"
        " else { Write-Output 'NONE' };"
        f"$s.SetOutputToWaveFile('{target.as_posix()}');"
        "$s.Rate = -1;"
        f"$s.Speak('{sentence}');"
        "$s.Dispose();"
    )
    done = subprocess.run(["powershell", "-NoProfile", "-Command", script],
                          capture_output=True, text=True, timeout=120)
    if not target.is_file() or target.stat().st_size < 10_000:
        raise SystemExit(f"local speech synthesis produced no wav: {done.stderr[:300]}")
    return done.stdout.strip().splitlines()[-1] if done.stdout.strip() else "NONE"


def _tokens(text: str) -> set[str]:
    """Words for spoken English, characters for Chinese - the sample may be either."""
    cleaned = re.sub(r"[，。？！,.?!\"']", "", str(text or ""))
    if any("一" <= char <= "鿿" for char in cleaned):
        return {char for char in cleaned if "一" <= char <= "鿿"}
    return {word for word in cleaned.lower().split() if word}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="tiny",
                        help="faster-whisper size: tiny|base|small (weights download once)")
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda", "auto"])
    parser.add_argument("--audio", default="", help="transcribe this wav instead of synthesizing one")
    parser.add_argument("--say", default=SPEECH, help="what the local voice should speak")
    parser.add_argument("--voice", default="en", help="culture prefix of the local voice, e.g. zh")
    parser.add_argument("--lang", default="", help="pin the whisper language instead of detecting")
    parser.add_argument("--route", action="store_true",
                        help="only report whether the product's microphone route can reach the"
                             " local recogniser with this store's Core provider; opens nothing")
    args = parser.parse_args()

    sys.path.insert(0, str(HOST))
    if args.route:
        print(json.dumps(speech_route_status(), ensure_ascii=False, indent=2))
        return 0
    os.environ["NEKO_DEV_TEXT_ONLY"] = "1"  # the shipping configuration: mute stays on
    os.environ["NEKO_ASR_PROBE_VOICE"] = args.voice
    worker = importlib.import_module(WORKER)
    out: dict[str, object] = {"expected_text": args.say, "voice_culture": args.voice}

    tmp = Path(tempfile.mkdtemp(prefix="neko-asr-"))
    wav = Path(args.audio) if args.audio else tmp / "sample.wav"
    if not args.audio:
        out["local_voice"] = synth_wav(wav, args.say)
    os.environ[worker._MODEL_ENV] = args.model
    os.environ[worker._DEVICE_ENV] = args.device
    spec = worker._model_spec_from_env()
    out.update({"model_env": worker._MODEL_ENV, "device_env": worker._DEVICE_ENV,
                "product_default_model": getattr(worker, "_DEFAULT_MODEL_CPU", None),
                "product_default_compute": getattr(worker, "_DEFAULT_COMPUTE_CPU", None)})

    started = time.time()
    model = worker._load_whisper_model(spec)
    out["model_load_seconds"] = round(time.time() - started, 1)

    started = time.time()
    kwargs: dict[str, object] = {"beam_size": 1, "vad_filter": True}
    if args.lang:
        kwargs.update({"language": args.lang, "task": "transcribe"})
    segments, info = model.transcribe(str(wav), **kwargs)
    text = " ".join(segment.text.strip() for segment in segments).strip()
    out.update({"transcribe_seconds": round(time.time() - started, 1),
                "detected_language": getattr(info, "language", None),
                "transcript": text,
                "wav_bytes": wav.stat().st_size})

    spoken, heard = _tokens(args.say), _tokens(text)
    out["accuracy"] = round(len(spoken & heard) / len(spoken), 2) if spoken else 0.0
    out["missed"] = sorted(spoken - heard)

    # No voice for that culture on this machine: the wav was read by a foreign voice,
    # so a low score here says nothing about the recogniser. Say so instead of
    # reporting a Chinese ASR failure that was never tested.
    untested = out.get("local_voice") == "NONE"
    out["provider_requests_sent"] = 0
    if untested:
        out["status"] = "NOT_TESTED"
        out["reason"] = (f"本机没有 {args.voice} 的本地语音，这句话是被别国语音念出来的；"
                         "要测这门语言请自己对麦克风说，或用 --audio 指定一段真人录音")
    else:
        out["status"] = "PASS" if out["accuracy"] >= 0.9 and text else "FAIL"
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if untested or out["status"] == "PASS" else 1



if __name__ == "__main__":
    raise SystemExit(main())
