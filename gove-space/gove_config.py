# ===== Gove reference config — the ONLY thing you may need to tune =====
#
# GPT-SoVITS clones the timbre from a short reference clip. For best quality the
# transcript below MUST match what is actually spoken in ref_audio/zh_ref.wav.
#
# >>> ACTION REQUIRED <<<
# Open ref_audio/zh_ref.wav, listen to it, and paste the exact words it says
# into GOVE_REF_PROMPT_TEXT. If the clip is English, also set PROMPT_LANG="en".
# If you leave a slightly-wrong transcript it still works but timbre is weaker.

GOVE_REF_AUDIO_PATH = "ref_audio/zh_ref.wav"
GOVE_REF_PROMPT_TEXT = "请把这句话替换成参考音频里实际说的内容"
GOVE_REF_PROMPT_LANG = "zh"   # zh | en | ja | auto

# Synthesis language for the simple endpoint. "auto" lets one endpoint handle
# mixed Chinese + English text — which is exactly the Gove use case.
GOVE_TEXT_LANG = "auto"
GOVE_TEXT_SPLIT_METHOD = "cut5"
# ======================================================================
