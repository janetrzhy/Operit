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
# GPT-SoVITS needs a short reference clip + its exact transcript (set in gove_config.py).
# The OmniDimen/Gove GitHub repo ships labelled demo clips; we grab the Chinese one,
# which also works cross-lingually for English synthesis in v2.
print(">> downloading reference audio ...")
ref_path = os.path.join(REF_DIR, "zh_ref.wav")
got = False
for url in (
    # GitHub raw, Chinese-labelled demo clip (中.wav)
    "https://raw.githubusercontent.com/OmniDimen/Gove/main/%E4%B8%AD.wav",
):
    try:
        r = requests.get(url, timeout=60)
        if r.ok and len(r.content) > 1000:
            with open(ref_path, "wb") as f:
                f.write(r.content)
            got = True
            print("   ref audio ->", ref_path, len(r.content), "bytes")
            break
    except Exception as e:
        print("   ref download failed:", url, e)

if not got:
    # Fallback: the wav that lives in the HF model repo (long English filename).
    try:
        from huggingface_hub import list_repo_files
        files = list_repo_files("OmniDimen/Gove")
        wav = next((f for f in files if f.lower().endswith(".wav")), None)
        if wav:
            p = hf_hub_download(repo_id="OmniDimen/Gove", filename=wav, local_dir=REF_DIR)
            shutil.copy(p, ref_path)
            got = True
            print("   ref audio (fallback) ->", ref_path)
    except Exception as e:
        print("   fallback ref download failed:", e)

if not got:
    raise SystemExit("ERROR: could not obtain a reference audio clip. Add one manually to ref_audio/zh_ref.wav")

print(">> all assets ready.")
