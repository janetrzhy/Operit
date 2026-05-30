# Gove TTS on Hugging Face Spaces (Docker, CPU basic free tier)
# Base: official GPT-SoVITS source + Gove voice weights from OmniDimen/Gove
FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive \
    HF_HOME=/app/.cache/huggingface \
    PYTHONUNBUFFERED=1 \
    GOVE_PORT=7860

WORKDIR /app

# ---- system deps ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg git git-lfs build-essential wget ca-certificates \
    && git lfs install \
    && rm -rf /var/lib/apt/lists/*

# ---- clone official GPT-SoVITS engine (pinned for reproducibility) ----
# api_v2.py and the GPT_SoVITS/ python package come from here, NOT from the Gove repo.
ARG GPTSOVITS_REF=main
RUN git clone --depth 1 --branch ${GPTSOVITS_REF} https://github.com/RVC-Boss/GPT-SoVITS.git /app \
    || (git clone https://github.com/RVC-Boss/GPT-SoVITS.git /tmp/gsv && cp -rT /tmp/gsv /app)

# ---- python deps ----
# Install the engine's own requirements first (it may pull a torch build).
RUN pip install --no-cache-dir -r requirements.txt || true
# Then force a single MATCHING CPU pair of torch + torchaudio LAST, so nothing
# can leave torchaudio linked against a different torch ABI (the cause of the
# "undefined symbol: aoti_torch_abi_version" crash).
RUN pip install --no-cache-dir --force-reinstall \
    torch==2.4.1 torchaudio==2.4.1 \
    --index-url https://download.pytorch.org/whl/cpu
# Extra pins for the API server + asset download (inlined to avoid an extra file).
RUN pip install --no-cache-dir \
    "huggingface_hub>=0.23.0" \
    "fastapi>=0.100.0" \
    "uvicorn[standard]>=0.23.0" \
    "pydantic>=2.0.0" \
    "soundfile>=0.12.1" \
    "requests>=2.31.0"

# ---- download model assets at BUILD time (baked into the image) ----
# This puts the cold-start cost into the build, not the first user request.
COPY download_assets.py /app/download_assets.py
RUN python download_assets.py

# ---- our config + the simple OpenAI-compatible endpoint patch ----
COPY tts_infer.yaml /app/tts_infer.yaml
COPY gove_config.py /app/gove_config.py
COPY patch_api.py  /app/patch_api.py
RUN python patch_api.py

EXPOSE 7860

# api_v2.py reads -c config; -a bind host; -p port
CMD ["python", "api_v2.py", "-a", "0.0.0.0", "-p", "7860", "-c", "tts_infer.yaml"]
