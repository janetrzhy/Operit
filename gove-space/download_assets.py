"""Download all model assets at Docker build time.

- GPT-SoVITS v2 base models (bert + hubert) from lj1995/GPT-SoVITS
- Gove voice weights (Gove.ckpt / Gove.pth) from OmniDimen/Gove
- A reference audio clip (required by GPT-SoVITS for zero-shot timbre)
"""
import os
import shutil
from huggingface_hub import hf_hub_download, snapshot_download
import requests

PRETRAINED_DIR = "GPT_SoVITS/pretrained_models"
REF_DIR = "ref_audio"
os.makedirs(PRETRAINED_DIR, exist_ok=True)
os.makedirs(REF_DIR, exist_ok=True)

# 1) GPT-SoVITS v2 base models. These two subdirs are what tts_infer.yaml points to.
print(">> downloading GPT-SoVITS v2 base models (bert + hubert) ...")
snapshot_download(
    repo_id="lj1995/GPT-SoVITS",
    local_dir=PRETRAINED_DIR,
    allow_patterns=[
        "chinese-roberta-wwm-ext-large/*",
        "chinese-hubert-base/*",
        # SV (speaker-verification) model required by v2Pro weights like Gove.pth
        "sv/*",
    ],
)

# 2) Gove voice weights.
print(">> downloading Gove weights ...")
for fn in ("Gove.ckpt", "Gove.pth"):
    p = hf_hub_download(repo_id="OmniDimen/Gove", filename=fn, local_dir=".")
    print("   got", p)

# 3) Reference audio.
# GPT-SoVITS needs a short reference clip + its exact transcript.
# The OmniDimen/Gove HF repo ships ONE wav whose *filename is the transcript*
# (an English ChatGPT description). We download it and derive the prompt text
# from the filename automatically, so no manual transcription is needed.
print(">> downloading reference audio from HF model repo ...")
from huggingface_hub import list_repo_files

ref_path = os.path.join(REF_DIR, "ref.wav")
prompt_path = os.path.join(REF_DIR, "ref_prompt.txt")

files = list_repo_files("OmniDimen/Gove")
wav = next((f for f in files if f.lower().endswith(".wav")), None)
if not wav:
    raise SystemExit("ERROR: no .wav found in OmniDimen/Gove. Add one to ref_audio/ref.wav manually.")

p = hf_hub_download(repo_id="OmniDimen/Gove", filename=wav, local_dir=REF_DIR)
shutil.copy(p, ref_path)

# Derive transcript from the filename (strip dir, extension, trailing dots/spaces).
stem = os.path.splitext(os.path.basename(wav))[0].strip().strip(".").strip()
with open(prompt_path, "w", encoding="utf-8") as f:
    f.write(stem)

print("   ref audio  ->", ref_path)
print("   ref prompt ->", repr(stem))

# 3.5) fast-langdetect model.
# GPT-SoVITS' LangSegmenter sets the fast_langdetect cache dir to
# pretrained_models/fast_langdetect and expects lid.176.bin there. On the
# non-root HF runtime it can't create the dir or download the model, which
# causes "Cache directory not found" on any multi-segment / mixed text.
# Pre-create the dir AND fetch the model at build time so runtime never has to.
print(">> downloading fast-langdetect model (lid.176.bin) ...")
fld_dir = os.path.join(PRETRAINED_DIR, "fast_langdetect")
os.makedirs(fld_dir, exist_ok=True)
fld_path = os.path.join(fld_dir, "lid.176.bin")
if not os.path.exists(fld_path):
    ok = False
    for url in (
        "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin",
        "https://huggingface.co/julien-c/fasttext-language-id/resolve/main/lid.176.bin",
    ):
        try:
            with requests.get(url, stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(fld_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        f.write(chunk)
            if os.path.getsize(fld_path) > 1_000_000:
                ok = True
                print("   lid.176.bin ->", fld_path, os.path.getsize(fld_path), "bytes")
                break
        except Exception as e:
            print("   langdetect download failed:", url, e)
    if not ok:
        print("   WARN: could not pre-download lid.176.bin; runtime may retry.")

# 4) NLTK data needed for English G2P (newer NLTK renamed these with _eng).
# IMPORTANT: HF Spaces runs the container as a non-root user, so we must store
# this in a fixed, world-readable dir (NLTK_DATA=/app/nltk_data) instead of the
# build-time root HOME, otherwise the runtime process can't find it.
print(">> downloading NLTK data for English text ...")
import nltk
nltk_dir = os.environ.get("NLTK_DATA", "/app/nltk_data")
os.makedirs(nltk_dir, exist_ok=True)
for pkg in (
    "averaged_perceptron_tagger_eng",
    "averaged_perceptron_tagger",
    "cmudict",
):
    try:
        nltk.download(pkg, download_dir=nltk_dir)
        print("   nltk:", pkg, "ok")
    except Exception as e:
        print("   nltk download failed:", pkg, e)

print(">> all assets ready.")
