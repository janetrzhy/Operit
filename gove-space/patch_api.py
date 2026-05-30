"""Inject a simple OpenAI-compatible endpoint into GPT-SoVITS' api_v2.py.

We do NOT hand-edit the upstream file. We programmatically insert a snippet
right before the `if __name__ == "__main__":` guard, so it reuses the already
defined `APP`, `tts_handle`, and `tts_pipeline` objects.

The snippet adds:
  POST /v1/audio/speech   (OpenAI-style: {"input": "..."} -> wav)
  GET  /healthz
  a startup warmup so the model is hot before the first real request.
"""
import io
import re

API = "api_v2.py"
with open(API, "r", encoding="utf-8") as f:
    src = f.read()

SNIPPET = '''
# ===================== GOVE simple endpoint (injected) =====================
import gove_config as _gcfg
from pydantic import BaseModel as _BaseModel

class SimpleTTSRequest(_BaseModel):
    input: str = ""
    model: str = "Gove"
    voice: str = "Gove"
    response_format: str = "wav"
    speed: float = 1.0

@APP.get("/healthz")
async def _gove_healthz():
    return {"status": "ok"}

@APP.post("/v1/audio/speech")
async def gove_simple_tts(request: SimpleTTSRequest):
    text = (request.input or "").strip()
    if not text:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=400, content={"message": "input is required"})
    req = {
        "text": text,
        "text_lang": _gcfg.GOVE_TEXT_LANG,
        "ref_audio_path": _gcfg.GOVE_REF_AUDIO_PATH,
        "prompt_text": _gcfg.GOVE_REF_PROMPT_TEXT,
        "prompt_lang": _gcfg.GOVE_REF_PROMPT_LANG,
        "media_type": "wav",
        "streaming_mode": False,
        "top_k": 15,
        "top_p": 1.0,
        "temperature": 1.0,
        "text_split_method": _gcfg.GOVE_TEXT_SPLIT_METHOD,
        "speed_factor": float(request.speed or 1.0),
    }
    return await tts_handle(req)

@APP.on_event("startup")
async def _gove_warmup():
    """Run one tiny synth so weights are hot; keeps the first real request fast."""
    try:
        req = {
            "text": "你好",
            "text_lang": _gcfg.GOVE_TEXT_LANG,
            "ref_audio_path": _gcfg.GOVE_REF_AUDIO_PATH,
            "prompt_text": _gcfg.GOVE_REF_PROMPT_TEXT,
            "prompt_lang": _gcfg.GOVE_REF_PROMPT_LANG,
            "media_type": "wav",
            "streaming_mode": False,
            "text_split_method": _gcfg.GOVE_TEXT_SPLIT_METHOD,
        }
        await tts_handle(req)
        print(">> Gove warmup done.")
    except Exception as _e:
        print(">> Gove warmup skipped:", _e)
# =================== end GOVE simple endpoint (injected) ===================

'''

marker = re.search(r'^if __name__ == ["\']__main__["\']:', src, re.MULTILINE)
if marker is None:
    # Fallback: just append (works if upstream starts uvicorn elsewhere).
    new_src = src + "\n" + SNIPPET
    print("WARN: __main__ guard not found; appended snippet at end.")
else:
    idx = marker.start()
    new_src = src[:idx] + SNIPPET + src[idx:]

if "gove_simple_tts" in src:
    print("Patch already applied; skipping.")
else:
    with open(API, "w", encoding="utf-8") as f:
        f.write(new_src)
    print("Patched api_v2.py with /v1/audio/speech.")
