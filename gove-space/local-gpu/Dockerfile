# Gove TTS — LOCAL GPU build (NVIDIA), for running on your own Windows/Linux PC.
# Unlike the HF CPU image, this uses a CUDA base + GPU torch so synthesis is fast
# (a sentence in ~1-3s instead of ~30s), which also means no client timeouts.
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    HF_HOME=/app/.cache/huggingface \
    NLTK_DATA=/app/nltk_data \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ---- system deps + python ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 python3-pip python3.10-venv \
    ffmpeg git git-lfs build-essential wget ca-certificates \
    && git lfs install \
    && ln -sf /usr/bin/python3.10 /usr/bin/python \
    && rm -rf /var/lib/apt/lists/*

# ---- clone official GPT-SoVITS engine ----
ARG GPTSOVITS_REF=main
RUN git clone --depth 1 --branch ${GPTSOVITS_REF} https://github.com/RVC-Boss/GPT-SoVITS.git /app \
    || (git clone https://github.com/RVC-Boss/GPT-SoVITS.git /tmp/gsv && cp -rT /tmp/gsv /app)

# ---- python deps: GPU torch (CUDA 12.1) ----
RUN pip install --no-cache-dir -r requirements.txt || true
RUN pip install --no-cache-dir --force-reinstall \
    torch==2.4.1 torchaudio==2.4.1 --index-url https://download.pytorch.org/whl/cu121
RUN pip install --no-cache-dir \
    "huggingface_hub>=0.23.0" "fastapi>=0.100.0" "uvicorn[standard]>=0.23.0" \
    "pydantic>=2.0.0" "soundfile>=0.12.1" "requests>=2.31.0" "nltk>=3.8"

# ---- download model assets at build time ----
COPY download_assets.py /app/download_assets.py
RUN mkdir -p /app/nltk_data /app/ref_audio /app/GPT_SoVITS/pretrained_models/fast_langdetect \
    && python download_assets.py \
    && python -m nltk.downloader -d /app/nltk_data \
         averaged_perceptron_tagger_eng averaged_perceptron_tagger cmudict \
    && chmod -R a+rwX /app/nltk_data /app/ref_audio /app/GPT_SoVITS/pretrained_models

# ---- config + endpoint patch ----
COPY tts_infer.yaml /app/tts_infer.yaml
COPY gove_config.py /app/gove_config.py
COPY patch_api.py  /app/patch_api.py
RUN python patch_api.py

EXPOSE 7860
CMD ["python", "api_v2.py", "-a", "0.0.0.0", "-p", "7860", "-c", "tts_infer.yaml"]
