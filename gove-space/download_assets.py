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
print(">> all assets ready.")
