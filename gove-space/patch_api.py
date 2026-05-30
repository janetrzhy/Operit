"""Inject a simple OpenAI-compatible endpoint into GPT-SoVITS' api_v2.py.

We do NOT hand-edit the upstream file. We programmatically insert a snippet
right before the `if __name__ == "__main__":` guard, so it reuses the already
defined `APP`, `tts_handle`, and `tts_pipeline` objects.

The snippet adds:
  POST /v1/audio/speech   (OpenAI-style: {"input": "..."} -> wav)
  GET  /healthz
  a startup warmup so the model is hot before the first real request.

Language is detected manually (zh vs en) to AVOID fast-langdetect, which tries
to download/cache a model at runtime and fails on the non-root HF filesystem.

Speed/pitch: the model applies GOVE_SPEED_FACTOR (time-stretch). Pitch is then
raised by rewriting the WAV header sample rate by GOVE_PITCH_SCALE (which also
speeds it up), so final speed = SPEED_FACTOR * PITCH_SCALE, final pitch =
PITCH_SCALE. Defaults ~2x speed / ~1.5x pitch to match the original Gove voice.
"""
import re

API = "api_v2.py"
with open(API, "r", encoding="utf-8") as f:
    src = f.read()

SNIPPET = r'''
# ===================== GOVE simple endpoint (injected) =====================
import struct as _struct
import gove_config as _gcfg
from pydantic import BaseModel as _BaseModel
from fastapi.responses import JSONResponse as _JSONResponse, Response as _Response

class SimpleTTSRequest(_BaseModel):
    input: str = ""
    model: str = "Gove"
    voice: str = "Gove"
    response_format: str = "wav"
    speed: float = 1.0

def _gove_lang(text):
    """Pick a concrete language, never 'auto' (avoids fast-langdetect)."""
    cfg = getattr(_gcfg, "GOVE_TEXT_LANG", "auto")
    if cfg and cfg != "auto":
        return cfg
    has_zh = any('一' <= c <= '鿿' for c in text)
    return "zh" if has_zh else "en"

def _gove_req(text, speed_mult=1.0):
    base_speed = float(getattr(_gcfg, "GOVE_SPEED_FACTOR", 1.0))
    return {
        "text": text,
        "text_lang": _gove_lang(text),
        "ref_audio_path": _gcfg.GOVE_REF_AUDIO_PATH,
        "prompt_text": _gcfg.GOVE_REF_PROMPT_TEXT,
        "prompt_lang": _gcfg.GOVE_REF_PROMPT_LANG,
        "media_type": "wav",
        "streaming_mode": False,
        "top_k": 15,
        "top_p": 1.0,
        "temperature": 1.0,
        "text_split_method": _gcfg.GOVE_TEXT_SPLIT_METHOD,
        "speed_factor": base_speed * float(speed_mult or 1.0),
    }

def _gove_pitch_wav(data, scale):
    """Raise pitch+speed by rewriting the WAV fmt chunk sample rate by `scale`.
    Cheap and lossless; players honor the header. Returns modified bytes."""
    try:
        if not scale or abs(scale - 1.0) < 1e-3:
            return data
        if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
            return data
        buf = bytearray(data)
        pos = 12
        n = len(buf)
        while pos + 8 <= n:
            cid = bytes(buf[pos:pos+4])
            csz = _struct.unpack_from("<I", buf, pos+4)[0]
            if cid == b"fmt ":
                sr = _struct.unpack_from("<I", buf, pos+12)[0]
                br = _struct.unpack_from("<I", buf, pos+16)[0]
                _struct.pack_into("<I", buf, pos+12, int(sr * scale))
                _struct.pack_into("<I", buf, pos+16, int(br * scale))
                break
            pos += 8 + csz + (csz & 1)
        return bytes(buf)
    except Exception:
        return data

async def _gove_synth(text, speed_mult=1.0):
    resp = await tts_handle(_gove_req(text, speed_mult))
    # Only post-process successful WAV responses.
    if isinstance(resp, _Response) and getattr(resp, "media_type", "") == "audio/wav":
        body = getattr(resp, "body", None)
        if body:
            scale = float(getattr(_gcfg, "GOVE_PITCH_SCALE", 1.0))
            return _Response(_gove_pitch_wav(bytes(body), scale), media_type="audio/wav")
    return resp

@APP.get("/healthz")
async def _gove_healthz():
    return {"status": "ok"}

@APP.post("/v1/audio/speech")
async def gove_simple_tts(request: SimpleTTSRequest):
    text = (request.input or "").strip()
    if not text:
        return _JSONResponse(status_code=400, content={"message": "input is required"})
    return await _gove_synth(text, request.speed)

@APP.on_event("startup")
async def _gove_warmup():
    """Run one tiny synth so weights are hot; keeps the first real request fast."""
    try:
        await _gove_synth("你好")
        print(">> Gove warmup done.")
    except Exception as _e:
        print(">> Gove warmup skipped:", _e)
# =================== end GOVE simple endpoint (injected) ===================

'''

marker = re.search(r'^if __name__ == ["\']__main__["\']:', src, re.MULTILINE)

if "gove_simple_tts" in src:
    print("Patch already applied; skipping.")
else:
    if marker is None:
        new_src = src + "\n" + SNIPPET
        print("WARN: __main__ guard not found; appended snippet at end.")
    else:
        idx = marker.start()
        new_src = src[:idx] + SNIPPET + src[idx:]
    with open(API, "w", encoding="utf-8") as f:
        f.write(new_src)
    print("Patched api_v2.py with /v1/audio/speech.")
