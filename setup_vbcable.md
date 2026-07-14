# VB-Cable 安装与配置指南

VB-Cable 是一款免费的 Windows 虚拟音频设备软件，它创建一对虚拟的"扬声器→麦克风"，任何播放到虚拟扬声器的声音都会"桥接"到虚拟麦克风，语音软件（Discord/YY/游戏语音）采集虚拟麦克风即可收到声音。

---

## 1. 下载与安装

1. 打开 [VB-Audio 官网](https://vb-audio.com/Cable/)
2. 找到 **"VB-CABLE Virtual Audio Device"**（免费版）
3. 点击 **Download** 下载 zip 包
4. 解压后，**右键 `VBCABLE_Setup_x64.exe` → 以管理员身份运行**
5. 点击 **Install Driver**，等待安装完成
6. **重启电脑**（重要！不重启可能不生效）

> 如果提示驱动签名问题，参考[官网 FAQ](https://vb-audio.com/Cable/VBCABLE_System_Settings.pdf)

---

## 2. 验证安装

安装并重启后：

1. 任务栏 **右键点击喇叭图标** → **声音**
2. 切换到 **播放** 选项卡，应该能看到 **"CABLE Input"** 设备
3. 切换到 **录制** 选项卡，应该能看到 **"CABLE Output"** 设备

```
播放设备:  CABLE Input (VB-Audio Virtual Cable)   ← 我们的程序输出到这里
录制设备:  CABLE Output (VB-Audio Virtual Cable)  ← 语音软件从这里采集
               ↑              ↑
           它们内部是"连在一起"的
```

---

## 3. 语音软件设置

以 **Discord** 为例：

1. 打开 Discord → **用户设置**（齿轮图标）
2. **语音和视频** → **输入设备** → 选择 **"CABLE Output"**
3. 确认输入音量指示条有反应

以 **YY 语音** 为例：

1. 打开 YY → 进入频道
2. 进 **系统设置** → **语音设置**
3. **麦克风** → 选择 **"CABLE Output"**

游戏内语音同理，在音频设置里把麦克风/输入设备选为 **"CABLE Output"**。

---

## 4. 混合真实麦克风（可选）

如果你还想同时保留自己的真实麦克风（比如偶尔说句话），可以加装 **Voicemeeter**（免费，同一官网）：

- Voicemeeter 可以把真实麦克风 + 虚拟音频 混合成一路输出
- 配置稍复杂，需要的话可以单独出教程

---

## 5. 测试

1. 在 Windows 声音设置 → **录制** 选项卡 → 双击 **CABLE Output**
2. 切换到 **侦听** 选项卡 → 勾选 **"侦听此设备"** → 应用
3. 运行 `python tts_mic.py`，输入测试文字
4. 你应该能从电脑扬声器听到谷歌娘的声音
5. 测试完毕后记得**取消勾选**侦听

---

## 6. 常见问题

**Q: 安装后看不到 CABLE 设备？**
A: 重启电脑。如果还不行，尝试运行 `VBCABLE_Setup_x64.exe` 右键管理员安装。

**Q: 朋友听到的声音太小？**
A: 在 Windows 声音 → 录制 → CABLE Output → 属性 → 级别 调高。

**Q: 朋友听不到任何声音？**
A: 检查三个地方：
1. 语音软件的输入设备是否选为 CABLE Output
2. CABLE Output 是否被禁用（右键启用）
3. 运行 tts_mic 时确认输出设备是 CABLE Input

**Q: 朋友听到有我电脑的其他声音（游戏声、音乐）？**
A: 需要把系统默认播放设备设为你的真实扬声器/耳机，而不是 CABLE Input。
   CABLE Input 只在 tts_mic 里单独指定使用。
