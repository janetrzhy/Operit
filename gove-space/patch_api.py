"""Inject a simple OpenAI-compatible endpoint into GPT-SoVITS' api_v2.py.

We do NOT hand-edit the upstream file. We programmatically insert a snippet
right before the `if __name__ == "__main__":` guard, so it reuses the already
defined `APP`, `tts_handle`, and `tts_pipeline` objects.

The snippet adds:
  POST /v1/audio/speech   (OpenAI-style: {"input": "..."} -> streaming wav)
  GET  /healthz
  a startup warmup so the model is hot before the first real request.

WHY STREAMING: clients like Operit use a per-read socket timeout (e.g. 10s) that
measures the gap *between* received data packets, not the total request time. A
slow CPU backend that buffers the whole clip (30s+) sends nothing for 30s and
trips that timeout. By streaming (streaming_mode=True) we emit the WAV header
immediately and then PCM chunks as they're synthesized, so data keeps flowing
and the read timeout never fires — even on a free CPU.

SPEED/PITCH: we relabel the streamed WAV header's sample rate by
GOVE_PITCH_SCALE (raises pitch AND speed); the model also time-stretches by
GOVE_SPEED_FACTOR. Final speed = SPEED_FACTOR * PITCH_SCALE, pitch = PITCH_SCALE.

Language is detected manually (zh vs en) to AVOID fast-langdetect's runtime
cache issues on the non-root HF filesystem.
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
from fastapi.responses import JSONResponse as _JSONResponse, StreamingResponse as _StreamingResponse

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
        "streaming_mode": True,
        "top_k": 15,
        "top_p": 1.0,
        "temperature": 1.0,
        "text_split_method": _gcfg.GOVE_TEXT_SPLIT_METHOD,
        "speed_factor": base_speed * float(speed_mult or 1.0),
        "parallel_infer": False,
    }

def _gove_relabel_header(data, scale):
    """Rewrite a WAV header's sample rate / byte rate by `scale` (pitch+speed).
    Only touches the fmt chunk; PCM data passes through untouched."""
    try:
        if not scale or abs(scale - 1.0) < 1e-3:
            return data
        if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
            return data
        buf = bytearray(data)
        pos, n = 12, len(buf)
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

async def _gove_stream(text, speed_mult=1.0):
    """Return a StreamingResponse. Keeps bytes flowing so per-read client
    timeouts never fire, and relabels the first (header) chunk for pitch."""
    resp = await tts_handle(_gove_req(text, speed_mult))
    # Errors come back as JSONResponse — pass straight through.
    if not isinstance(resp, _StreamingResponse):
        return resp
    scale = float(getattr(_gcfg, "GOVE_PITCH_SCALE", 1.0))
    inner = resp.body_iterator

    async def gen():
        first = True
        async for chunk in inner:
            if first:
                chunk = _gove_relabel_header(bytes(chunk), scale)
                first = False
            yield chunk

    return _StreamingResponse(gen(), media_type="audio/wav")

@APP.get("/healthz")
async def _gove_healthz():
    return {"status": "ok"}

@APP.post("/v1/audio/speech")
async def gove_simple_tts(request: SimpleTTSRequest):
    text = (request.input or "").strip()
    if not text:
        return _JSONResponse(status_code=400, content={"message": "input is required"})
    return await _gove_stream(text, request.speed)

@APP.on_event("startup")
async def _gove_warmup():
    """Run one tiny synth so weights are hot; keeps the first real request fast."""
    try:
        resp = await _gove_stream("你好")
        if isinstance(resp, _StreamingResponse):
            async for _ in resp.body_iterator:
                pass
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
