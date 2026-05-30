# Gove TTS — 本地 GPU 部署（Windows + NVIDIA + 外网访问）

在你自己的 Windows 旧电脑（有 N 卡）上跑 Gove，手机 Operit 通过 Tailscale 随时随地连。
**免费、快（一句 1-3 秒）、不超时。**

---

## 一、准备（Windows 旧电脑）

1. **更新 NVIDIA 驱动**到较新版本（[官网](https://www.nvidia.com/Download/index.aspx)）。
2. 安装 **Docker Desktop**：https://www.docker.com/products/docker-desktop/
   - 安装时勾选 **Use WSL 2 backend**（默认即是）。
3. 安装完打开 Docker Desktop → Settings → Resources → **WSL Integration** 开启。
   - GPU 支持在新版 Docker Desktop + WSL2 下开箱即用，无需额外装 CUDA。

> 验证 GPU 能被 Docker 看到，打开 PowerShell 运行：
> ```powershell
> docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi
> ```
> 能看到你的显卡信息就 OK。

---

## 二、构建并启动

把本目录（`local-gpu/`，含 6 个文件）整个拷到旧电脑，比如 `C:\gove\`。
在该目录打开 PowerShell：

```powershell
cd C:\gove
docker compose up -d --build
```

首次构建较久（下 ~2.5GB 模型 + 装 GPU torch）。完成后服务在 `http://localhost:7860`。

测试：
```powershell
curl -X POST "http://localhost:7860/v1/audio/speech" -H "Content-Type: application/json" -d '{\"input\":\"你好，本地 GPU 测试\"}' --output test.wav
```

查看日志 / 确认用上 GPU：
```powershell
docker logs -f gove-tts
```
日志里 device 应为 `cuda`，且 `>> Gove warmup done.` 出现。

---

## 三、手机 Operit 连接

### 在家（同 WiFi）
1. 旧电脑上看本机局域网 IP：PowerShell 运行 `ipconfig`，找 `IPv4 地址`（如 `192.168.1.20`）。
2. Operit → 设置 → 语音服务：
   - 引擎：**HTTP_TTS**
   - URL：`http://192.168.1.20:7860/v1/audio/speech`
   - 方法：POST，Content-Type：application/json
   - 请求体：`{"input":"{text}"}`，响应管线/Headers 留空

### 在外面也要用 → Tailscale（免费内网穿透）
1. 旧电脑和手机都装 **Tailscale**（https://tailscale.com），用**同一个账号**登录。
2. Tailscale 会给旧电脑一个固定的 `100.x.x.x` 地址（在 Tailscale 后台或客户端可见）。
3. Operit 里 URL 改成那个地址：
   `http://100.x.x.x:7860/v1/audio/speech`
4. 这样无论手机在哪（4G/5G/别的 WiFi），只要两端 Tailscale 在线就能连，**不需要公网 IP、不用改路由器**。

> Windows 防火墙若拦截，放行 Docker / 7860 端口；或首次连接时弹窗点“允许”。

---

## 四、日常使用
- 开机自启：`restart: unless-stopped` 已设置，Docker Desktop 设为开机启动即可，电脑开着就一直在。
- 更新声音参数（语速/音调）：改 `gove_config.py` 的 `GOVE_PITCH_SCALE` / `GOVE_SPEED_FACTOR`，然后 `docker compose up -d --build`。

## 关于速度/超时
本地 GPU 下一句话 1-3 秒返回，远低于 Operit 的 10 秒超时，长文分段朗读也顺畅。
（端点同时做了流式输出，进一步保证慢硬件也不会触发客户端读超时。）
