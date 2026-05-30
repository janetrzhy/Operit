---
title: Gove TTS
emoji: 🗣️
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# Gove TTS (GPT-SoVITS) — Hugging Face Space

中英文男声 TTS，基于 [OmniDimen/Gove](https://huggingface.co/OmniDimen/Gove) 音色权重 + 官方 GPT-SoVITS 引擎。
给 [Operit](https://github.com/AAswordman/Operit) 当 HTTP_TTS 后端用。

## 这套文件做了什么
- 构建时克隆官方 GPT-SoVITS（提供 `api_v2.py` 和推理代码）。
- 构建时下载好 v2 底模 + Gove.ckpt/Gove.pth + 参考音频（成本压在 build 阶段）。
- 注入一个 OpenAI 兼容端点：`POST /v1/audio/speech`，请求体 `{"input":"要说的话"}` → 返回 wav。
- 启动时预热一次，让第一次真实请求更快。

## 部署步骤
1. 在 HF 新建一个 **Docker** SDK 的 Space，Hardware 选 **CPU basic（免费）**。
2. 把本目录所有文件上传到该 Space 仓库根目录（用 git 推送即可，无需手动传大模型——模型在构建时自动下载）。
3. 等待 Build 完成、状态变 **Running**（首次构建较久，要下 ~2GB 模型）。
4. **重要**：打开 `gove_config.py`，把 `GOVE_REF_PROMPT_TEXT` 改成 `ref_audio/zh_ref.wav` 里实际说的话（不改也能出声，但音色更弱）。

## 测试
```bash
curl -X POST https://<你的用户名>-gove-tts.hf.space/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input":"你好，欢迎使用 Gove，hello world"}' \
  --output test.wav
```

## 在 Operit 里配置（设置 → 语音服务）
| 字段 | 值 |
|---|---|
| TTS 引擎 | HTTP_TTS |
| URL | `https://<你的用户名>-gove-tts.hf.space/v1/audio/speech` |
| 方法 | POST |
| Content-Type | application/json |
| 请求体 | `{"input":"{text}"}` |
| 响应管线 | 留空（直接返回 wav 二进制） |

## ⚠️ 免费档的两个现实问题
1. **休眠**：15 分钟无访问会睡，冷启动 30–60s。用 [UptimeRobot](https://uptimerobot.com) 每 5 分钟 ping `https://<你的空间>.hf.space/healthz` 保活。
2. **超时**：Operit 的 HTTP TTS 客户端目前**硬编码 10 秒超时**（`HttpVoiceProvider.kt`）。免费 CPU 合成长句可能 >10s 而在 Operit 端报超时。缓解办法：保活避免冷启动 + 让 Operit 发送的文本短一些；要彻底解决需要改 Operit 源码把超时调大（本次未做）。
