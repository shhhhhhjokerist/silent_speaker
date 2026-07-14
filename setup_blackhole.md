# macOS 虚拟音频配置指南

macOS 上使用 **BlackHole**（免费开源）作为虚拟音频设备，功能等同于 Windows 上的 VB-Cable。

---

## 1. 安装 BlackHole

```bash
# 推荐：用 Homebrew 安装 2 声道版本
brew install blackhole-2ch

# 或从官网下载安装包:
# https://existential.audio/blackhole/
```

安装后**重启电脑**（或至少重启音频服务）。

---

## 2. 验证安装

### 方法1：系统设置

1. 打开 **系统设置 → 声音**
2. **输出** 选项卡应能看到 **"BlackHole 2ch"**
3. **输入** 选项卡应也能看到 **"BlackHole 2ch"**

### 方法2：命令行

```bash
python tts_mic.py --list
```

应该能看到 `[N] BlackHole 2ch` 设备，且带有 ✅ 标记。

---

## 3. 创建多输出设备（关键步骤）

macOS 上 BlackHole 默认只做音频桥接。**如果你还想同时听到游戏声音**，需要创建一个"聚合设备"让声音同时输出到你的耳机和 BlackHole：

1. 打开 **应用程序 → 实用工具 → Audio MIDI Setup**
2. 左下角点击 **+** → **创建多输出设备**
3. 勾选你的**耳机/扬声器** + **BlackHole 2ch**
4. 在系统设置 → 声音 → 输出中选择这个多输出设备
5. 这样游戏声音走耳机，TTS 声音走 BlackHole → 语音软件的麦克风

> 如果不需要同时听游戏声音，直接跳过这一步。

---

## 4. 语音软件设置

### Discord

1. 用户设置 → 语音和视频
2. **输入设备** → 选择 **"BlackHole 2ch"**

### 其他软件（YY / 游戏语音）

同样，把麦克风/输入设备选为 **"BlackHole 2ch"**。

---

## 5. 测试

```bash
# 运行 TTS 工具
python tts_mic.py --list    # 确认 BlackHole 被检测到
python tts_mic.py            # 启动 CLI，自动选择 BlackHole
python tts_mic_gui.py        # 或启动 GUI
```

输入测试文字，在语音软件里确认输入音量条有反应。

---

## 6. 常见问题

**Q: 安装后看不到 BlackHole 设备？**
A: 重启电脑。如果还不行，尝试：
```bash
brew uninstall blackhole-2ch
brew install blackhole-2ch
```
然后重启。

**Q: 朋友听到的声音太小？**
A: 在 Audio MIDI Setup 里选中 BlackHole 2ch，调整音量滑块。或者在 TTS 工具里调高音量。

**Q: tkinter GUI 打不开？**
A: macOS 自带的 Python 可能没有 tkinter。用 Homebrew 安装：
```bash
brew install python-tk@3.11
```
或者直接用 CLI 版本 `python tts_mic.py`，功能一样。

**Q: 苹果芯片 (M1/M2/M3) 兼容吗？**
A: 完全兼容。BlackHole 和所有 Python 包都原生支持 Apple Silicon。
