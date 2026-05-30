# ===== Gove reference config =====
#
# GPT-SoVITS clones the timbre from a short reference clip + its transcript.
# download_assets.py grabs the wav from the HF Gove repo and writes the
# transcript (derived from the filename) to ref_audio/ref_prompt.txt, so you
# normally DON'T need to touch anything here.
import os

# Resolve everything relative to THIS file's directory and make it absolute,
# so it never depends on the process working directory.
_BASE = os.path.dirname(os.path.abspath(__file__))
_REF_DIR = os.path.join(_BASE, "ref_audio")
GOVE_REF_AUDIO_PATH = os.path.join(_REF_DIR, "ref.wav")

# Auto-load the transcript produced at build time; fall back if missing.
_prompt_file = os.path.join(_REF_DIR, "ref_prompt.txt")
if os.path.exists(_prompt_file):
    with open(_prompt_file, "r", encoding="utf-8") as _f:
        GOVE_REF_PROMPT_TEXT = _f.read().strip()
else:
    GOVE_REF_PROMPT_TEXT = ""

# The HF reference clip is English, so its prompt language is English.
# (Cross-lingual v2 still synthesizes Chinese fine from an English reference.)
GOVE_REF_PROMPT_LANG = "en"   # zh | en | ja | auto

# Synthesis language for the simple endpoint. "auto" lets one endpoint handle
# mixed Chinese + English text — exactly the Gove use case.
GOVE_TEXT_LANG = "auto"
GOVE_TEXT_SPLIT_METHOD = "cut5"

# ----- speed / pitch tuning -----
# Output is post-processed to match the original Gove voice:
#   * GOVE_PITCH_SCALE   raises pitch AND speed together (WAV samplerate relabel)
#   * GOVE_SPEED_FACTOR  is the model's time-stretch (changes speed, not pitch)
# Final speed  = GOVE_SPEED_FACTOR * GOVE_PITCH_SCALE
# Final pitch  = GOVE_PITCH_SCALE
# Defaults give ~2x speed and ~1.5x pitch (1.333 * 1.5 = 2.0).
GOVE_PITCH_SCALE = 1.5
GOVE_SPEED_FACTOR = 1.333
# =================================
