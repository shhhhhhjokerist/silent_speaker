# TTS 虚拟麦克风工具 🎙️

> 打字 → TTS 语音 → 虚拟麦克风 → 朋友在语音里听到

打游戏不方便开麦？用这个工具，在聊天框打字，让你的朋友听到合成语音。

**支持 Windows / macOS** | Edge TTS / Google TTS / 离线 TTS | CLI + GUI

---

## 🚀 快速开始

### 1. 安装虚拟音频设备（一次性）

| 平台 | 软件 | 安装方式 |
|------|------|----------|
| **Windows** | VB-Cable | [官网下载](https://vb-audio.com/Cable/) → 管理员安装 → 重启 |
| **macOS** | BlackHole | `brew install blackhole-2ch` → 重启 |

👉 详见 [setup_vbcable.md](setup_vbcable.md) (Win) / [setup_blackhole.md](setup_blackhole.md) (Mac)

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行

```bash
# GUI 版（推荐）
python tts_mic_gui.py

# CLI 版
python tts_mic.py

# 列出所有音频设备
python tts_mic.py --list
```

### 4. 设置语音软件

打开语音软件（Discord / YY / 游戏语音），把**麦克风/输入设备**选为虚拟设备：
- Windows: **"CABLE Output"**
- macOS: **"BlackHole 2ch"**

---

## 💬 使用方式

```
💬 > 你好啊，听得到吗？
  [Edge] 合成中... (1.5s) 播放中... 完成 (3.5s)

💬 > lol                    ← 快捷短语自动触发
  🔥 lol → 哈哈哈
```

GUI 界面更直观：引擎下拉切换、音量滑块调节、快捷短语一键发送。

---

## 🎛️ TTS 引擎

| 引擎 | 说明 | 网络要求 |
|------|------|----------|
| **Edge TTS** | 微软免费，音质最好，晓晓等 18 种中文语音 | 需联网（国内直连） |
| **Google TTS** | 经典谷歌娘声音 | 需联网（国内需代理） |
| **Offline** | Windows SAPI5 / macOS NSSpeech | 无需网络 |

可在 GUI 下拉切换，或 CLI 用 `/engine edge|google|offline`。

---

## ⌨️ 快捷短语

在 `config.json` 中预设：

```json
"hot_phrases": {
    "?": "你刚才说什么？",
    "gg": "打得不错",
    "brb": "我马上回来"
}
```

---

## 📦 打包

**Windows：**
```bash
build_exe.bat          # 生成 dist\tts_mic_gui.exe
```

**macOS：**
```bash
chmod +x build_mac.sh
./build_mac.sh         # 生成 dist/tts_mic 和 dist/tts_mic_gui
```

---

## 🔧 常见问题

**Q: 安装虚拟音频后看不到设备？**
A: **重启电脑**。驱动层面必须重启。

**Q: 朋友听不到声音？**
A: 三重检查：① 语音软件麦克风选了虚拟设备 ② tts_mic 输出设备是虚拟设备 ③ 系统声音面板里虚拟设备没被禁用。

**Q: Edge TTS 超时？**
A: 国内直连微软 TTS 通常没问题。如超时可切换离线引擎。

**Q: macOS GUI 打不开？**
A: `brew install python-tk@3.11`，或直接用 CLI 版（功能完全一致）。

**Q: Google TTS 超时？**
A: 国内需要代理。在 `config.json` 里填 `"google_proxy": "http://127.0.0.1:7890"`。
