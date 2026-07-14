#!/usr/bin/env python3
"""
TTS 虚拟麦克风工具 — TTS Virtual Microphone
=============================================
打字 → TTS 合成语音 → 虚拟音频线 → 虚拟麦克风 → 语音软件采集

用法:
    python tts_mic.py              # 自动检测 VB-Cable 设备
    python tts_mic.py --list       # 列出所有音频设备
    python tts_mic.py --device 3   # 指定输出设备 ID

前置条件:
    1. 安装 VB-Cable (https://vb-audio.com/Cable/)
    2. pip install -r requirements.txt
    3. 可选: 安装 ffmpeg 以支持 Edge TTS (下载后放 PATH 或同目录)
"""

import asyncio
import io
import json
import os
import sys
import tempfile
import time
import wave
from pathlib import Path

# ---- Windows 终端 UTF-8 修复 ----
if sys.platform == "win32":
    # 将 stdout/stderr 重配置为 UTF-8，解决中文 Windows GBK 编码问题
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

import numpy as np
import sounddevice as sd

# ---------------------------------------------------------------------------
# 路径与配置
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
CACHE_DIR = BASE_DIR / "cache"

DEFAULT_CONFIG = {
    "tts_engine": "edge",          # "edge" | "google" | "offline"
    "voice": "zh-CN-XiaoxiaoNeural",
    "rate": "+10%",
    "pitch": "+0Hz",
    "volume": 1.0,                 # 音量倍率 0.0 ~ 2.0，1.0 = 原始
    "output_device": None,         # None = 自动检测 VB-Cable
    "google_lang": "zh-CN",       # Google TTS 语言
    "google_proxy": "",            # Google TTS 代理，如 http://127.0.0.1:7890
    "hot_phrases": {
        "?": "你刚才说什么？",
        "??": "能再说一遍吗？",
        "ok": "好的没问题",
        "no": "不行",
        "wait": "等一下",
        "help": "我需要帮助",
        "lol": "哈哈哈",
        "gg": "打得好，这局结束了",
        "brb": "我马上回来",
        "bye": "拜拜，下次再玩",
    },
}


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


def get_config():
    """Merge user config with defaults."""
    cfg = DEFAULT_CONFIG.copy()
    user = load_config()
    cfg.update(user)
    # Deep merge hot_phrases
    if "hot_phrases" in user:
        cfg["hot_phrases"].update(user["hot_phrases"])
    return cfg


# ---------------------------------------------------------------------------
# 设备管理
# ---------------------------------------------------------------------------
def list_output_devices():
    """列出所有输出设备，返回设备列表。"""
    devices = sd.query_devices()
    outputs = []
    for i, dev in enumerate(devices):
        if dev["max_output_channels"] > 0:
            outputs.append((i, dev))
    return outputs


def print_devices():
    """打印设备列表，标记 VB-Cable。"""
    print("\n" + "=" * 65)
    print("  📢 可用的音频输出设备")
    print("=" * 65)
    outputs = list_output_devices()
    # 标记虚拟音频设备
    virt_keywords = ["BLACKHOLE", "SOUNDFLOWER", "LOOPBACK"] if sys.platform == "darwin" else ["CABLE", "VB-AUDIO", "VOICEMEETER"]
    for idx, dev in outputs:
        name = dev["name"]
        ch = dev["max_output_channels"]
        sr = int(dev["default_samplerate"])
        tags = []
        for kw in virt_keywords:
            if kw in name.upper():
                tags.append("✅ 虚拟音频线")
                break
        if idx == sd.default.device[1]:
            tags.append("(系统默认)")
        tag_str = f"  {' | '.join(tags)}" if tags else ""
        print(f"  [{idx:2d}] {name}")
        print(f"        {ch} 声道 @ {sr} Hz{tag_str}")
    print("=" * 65)
    if sys.platform == "darwin":
        print("  带 ✅ 的是 BlackHole 虚拟设备，语音软件麦克风要选对应的 Output 端")
        print("  提示: brew install blackhole-2ch 安装后重启电脑")
    else:
        print("  带 ✅ 的是 VB-Cable 虚拟设备，语音软件麦克风要选对应的 Output 端")
        print("  提示: 安装 VB-Cable 后如果没有看到，重启一下电脑")
    print("=" * 65 + "\n")


def find_virtual_audio_device():
    """
    自动找到虚拟音频播放设备（跨平台）。
    Windows: VB-Cable / Voicemeeter
    macOS:   BlackHole / Soundflower
    返回设备 ID 或 None。
    """
    # 各平台的虚拟音频设备关键词
    if sys.platform == "darwin":
        keywords = ["BLACKHOLE", "SOUNDFLOWER", "LOOPBACK"]
    else:
        keywords = ["CABLE", "VB-AUDIO", "VOICEMEETER"]

    outputs = list_output_devices()
    for idx, dev in outputs:
        name_upper = dev["name"].upper()
        for kw in keywords:
            if kw in name_upper:
                return idx
    return None


def get_virtual_audio_help():
    """返回当前平台虚拟音频安装提示。"""
    if sys.platform == "darwin":
        return (
            "请先安装 BlackHole 虚拟音频设备:\n"
            "  brew install blackhole-2ch\n"
            "  或下载: https://existential.audio/blackhole/"
        )
    else:
        return "请先安装 VB-Cable: https://vb-audio.com/Cable/"


def resolve_output_device(config_device):
    """确定输出设备：用户指定 > 自动检测 > 系统默认。"""
    if config_device is not None:
        return config_device
    virt = find_virtual_audio_device()
    if virt is not None:
        return virt
    print(f"  ⚠️  未检测到虚拟音频设备，将使用系统默认输出设备")
    print(f"     {get_virtual_audio_help()}")
    return sd.default.device[1]  # 系统默认输出


# ---------------------------------------------------------------------------
# TTS 引擎
# ---------------------------------------------------------------------------

# ---- Edge TTS ----
async def tts_edge(text, voice, rate, pitch):
    """
    使用 Microsoft Edge TTS 合成语音。
    返回 (audio_samples, sample_rate)。
    """
    import edge_tts

    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        pitch=pitch,
    )

    # 流式收集音频数据（边下边存，降低延迟）
    audio_chunks = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_chunks.append(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            pass  # 可以用来做打字机效果

    if not audio_chunks:
        raise RuntimeError("Edge TTS 没有返回音频数据")

    mp3_data = b"".join(audio_chunks)

    # MP3 解码 → numpy array
    return _decode_mp3(mp3_data)


# ---- Google TTS (gTTS) ----
async def tts_google(text, lang="zh-CN", slow=False, proxy=""):
    """
    使用 Google Translate TTS (gTTS) 合成语音 — 经典的"谷歌娘"声音。
    返回 (audio_samples, sample_rate)。
    注意: 国内可能需要代理才能访问 Google。
    """
    import io as io_mod

    from gtts import gTTS

    loop = asyncio.get_event_loop()

    def _synth():
        tts_kwargs = {"text": text, "lang": lang, "slow": slow}
        if proxy:
            # gTTS 使用 requests，通过 session 传代理
            import requests
            session = requests.Session()
            session.proxies = {"http": proxy, "https": proxy}
            tts_kwargs["session"] = session
        tts = gTTS(**tts_kwargs)
        buf = io_mod.BytesIO()
        tts.write_to_fp(buf)
        return buf.getvalue()

    # gTTS 是同步阻塞调用，放到线程池执行，设置 8 秒超时
    mp3_data = await asyncio.wait_for(
        loop.run_in_executor(None, _synth), timeout=8.0
    )
    return _decode_mp3(mp3_data)


def _decode_mp3(mp3_data):
    """
    将 MP3 数据解码为 (samples, sample_rate)。
    优先使用 miniaudio（纯 Python，无需外部依赖），
    其次 pydub（需要 ffmpeg），最后降级到离线引擎。
    """
    # 方案1: miniaudio — 纯 Python MP3 解码器，无外部依赖
    try:
        import miniaudio

        decoded = miniaudio.decode(mp3_data, dither=miniaudio.DitherMode.NONE)
        # 转为 numpy float32 数组
        if decoded.sample_width == 2:
            dtype = np.int16
        elif decoded.sample_width == 4:
            dtype = np.int32
        else:
            dtype = np.uint8

        samples = np.frombuffer(decoded.samples, dtype=dtype).astype(np.float32)
        if decoded.nchannels == 2:
            samples = samples.reshape((-1, 2))
        # 归一化
        samples = samples / float(2 ** (decoded.sample_width * 8 - 1))
        return samples, decoded.sample_rate

    except ImportError:
        pass
    except Exception as e:
        print(f"  ⚠️  miniaudio 解码失败: {e}，尝试 pydub...")

    # 方案2: pydub + ffmpeg
    try:
        from pydub import AudioSegment
        import io

        audio = AudioSegment.from_file(io.BytesIO(mp3_data), format="mp3")
        samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
        if audio.channels == 2:
            samples = samples.reshape((-1, 2))
        samples = samples / (2 ** 15)
        return samples, audio.frame_rate

    except ImportError:
        pass
    except Exception as e:
        print(f"  ⚠️  pydub 解码失败: {e}")

    # 方案3: 写入临时文件用 ffmpeg CLI
    return _decode_mp3_fallback(mp3_data)


def _decode_mp3_fallback(mp3_data):
    """
    备用 MP3 解码方案：
    保存到临时文件，用 subprocess 调 ffmpeg 转 wav，再读回来。
    """
    import subprocess

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f_mp3:
        f_mp3.write(mp3_data)
        mp3_path = f_mp3.name

    wav_path = mp3_path.replace(".mp3", ".wav")

    try:
        # 尝试用 ffmpeg 转换
        subprocess.run(
            ["ffmpeg", "-y", "-i", mp3_path, "-f", "wav", wav_path],
            capture_output=True,
            timeout=10,
            check=True,
        )
        samples, sr = _read_wav(wav_path)
        return samples, sr
    except (FileNotFoundError, subprocess.CalledProcessError):
        raise RuntimeError(
            "MP3 解码失败！请安装以下任一方案：\n"
            "  1. pip install pydub  + 安装 ffmpeg (推荐)\n"
            "  2. 或切换为离线引擎: 修改 config.json 中 tts_engine 为 'offline'"
        )
    finally:
        # 清理临时文件
        for p in (mp3_path, wav_path):
            try:
                os.unlink(p)
            except OSError:
                pass


def _read_wav(path):
    """读取 WAV 文件返回 (samples, sample_rate)。"""
    with wave.open(path, "rb") as wf:
        n_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    # 根据位深解析
    if sample_width == 2:
        dtype = np.int16
    elif sample_width == 4:
        dtype = np.int32
    else:
        dtype = np.uint8

    samples = np.frombuffer(raw, dtype=dtype).astype(np.float32)
    if n_channels == 2:
        samples = samples.reshape((-1, 2))
    # 归一化
    max_val = float(2 ** (sample_width * 8 - 1))
    samples = samples / max_val

    return samples, sample_rate


# ---- 本地离线 TTS ----
def tts_offline(text, voice_name=None):
    """
    使用 Windows SAPI5 (pyttsx3) 离线合成语音。
    返回 (audio_samples, sample_rate)。
    """
    import pyttsx3

    engine = pyttsx3.init()
    engine.setProperty("rate", 180)  # 语速稍快

    # 尝试设置中文语音
    voices = engine.getProperty("voices")
    if voice_name:
        for v in voices:
            if voice_name.lower() in v.name.lower():
                engine.setProperty("voice", v.id)
                break
    else:
        # 优先选中文语音
        for v in voices:
            if "chinese" in v.name.lower() or "zh" in v.name.lower() or "hui" in v.name.lower():
                engine.setProperty("voice", v.id)
                break

    # 输出到临时 WAV
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = f.name

    try:
        engine.save_to_file(text, wav_path)
        engine.runAndWait()

        samples, sr = _read_wav(wav_path)
        return samples, sr
    finally:
        try:
            os.unlink(wav_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# 短语缓存
# ---------------------------------------------------------------------------
def get_cached_phrase(text, config):
    """
    检查是否有常用短语缓存。
    返回缓存路径或 None。
    """
    hot_phrases = config.get("hot_phrases", {})
    if text in hot_phrases:
        cache_path = CACHE_DIR / f"{text}.wav"  # deprecated, 先不用
    return None


# ---------------------------------------------------------------------------
# 音频播放
# ---------------------------------------------------------------------------
def play_audio(samples, sample_rate, device_id, volume=1.0):
    """
    播放音频到指定设备。
    samples: numpy array, float32, shape (n,) or (n, channels)
    sample_rate: int
    device_id: int or None
    volume: float, 0.0 ~ 2.0, 1.0 = 原始音量
    """
    # 应用音量
    samples = samples.astype(np.float32) * volume
    # 防止削波
    samples = np.clip(samples, -1.0, 1.0)

    try:
        sd.play(samples, samplerate=int(sample_rate), device=device_id)
        sd.wait()
    except sd.PortAudioError as e:
        # 如果指定设备失败，尝试默认设备
        print(f"  ⚠️  设备 {device_id} 播放失败: {e}")
        print(f"  🔄 尝试使用系统默认设备...")
        sd.play(samples, samplerate=int(sample_rate))
        sd.wait()


# ---------------------------------------------------------------------------
# 主交互循环
# ---------------------------------------------------------------------------
async def speak(text, config, device_id, on_status=None):
    """
    合成并播放语音。返回耗时(秒)。

    on_status: 可选回调函数，签名为 on_status(msg, end="\n")
              用于 GUI 更新状态文字。为 None 时用 print。
    """
    def status(msg, end="\n"):
        if on_status:
            on_status(msg)
        else:
            print(msg, end=end, flush=True)

    t0 = time.time()
    engine = config.get("tts_engine", "edge")
    voice = config.get("voice", "zh-CN-XiaoxiaoNeural")
    rate = config.get("rate", "+10%")
    pitch = config.get("pitch", "+0Hz")
    volume = config.get("volume", 1.0)

    try:
        if engine == "offline":
            status("  [离线] 合成中...", end=" ")
            samples, sr = tts_offline(text)
        elif engine == "google":
            lang = config.get("google_lang", "zh-CN")
            proxy = config.get("google_proxy", "")
            status("  [谷歌] 合成中...", end=" ")
            samples, sr = await tts_google(text, lang=lang, slow=False, proxy=proxy)
        else:
            status("  [Edge] 合成中...", end=" ")
            samples, sr = await tts_edge(text, voice, rate, pitch)

        elapsed_synth = time.time() - t0
        status(f"({elapsed_synth:.1f}s) 播放中...", end=" ")

        play_audio(samples, sr, device_id, volume=volume)

        total = time.time() - t0
        status(f"完成 ({total:.1f}s)")
        return total

    except Exception as e:
        status(f"\n  失败: {e}")
        if engine != "offline":
            status("  正在降级到离线引擎重试...")
            try:
                samples, sr = tts_offline(text)
                status("  播放中...", end=" ")
                play_audio(samples, sr, device_id, volume=volume)
                total = time.time() - t0
                status(f"完成 ({total:.1f}s)")
                return total
            except Exception as e2:
                status(f"  离线引擎也失败了: {e2}")
        return None


def show_help(config):
    """显示帮助信息。"""
    print("\n" + "-" * 50)
    print("  📖 命令列表:")
    print("    /help      — 显示此帮助")
    print("    /devices   — 列出音频设备")
    print("    /device N  — 切换输出设备为 ID N")
    print("    /engine X  — 切换引擎 (edge / offline)")
    print("    /voice X   — 设置 Edge TTS 语音")
    print("    /rate X    — 设置语速 (如 +20%, -10%)")
    print("    /hot       — 列出快捷短语")
    print("    /hot K=V   — 添加快捷短语 (如 /hot ?=你说啥)")
    print("    /config    — 显示当前配置")
    print("    /save      — 保存当前配置")
    print("    /quit      — 退出")
    print("-" * 50)

    hot = config.get("hot_phrases", {})
    if hot:
        print("  🔥 快捷短语 (直接输入即触发):")
        for k, v in hot.items():
            print(f"    {k:12s} → {v}")
    print()


async def interactive_loop():
    """主交互循环。"""
    config = get_config()
    device_id = resolve_output_device(config.get("output_device"))

    # 显示启动信息
    print("\n" + "=" * 55)
    print("  🎙️  TTS 虚拟麦克风 v1.0")
    print("=" * 55)
    print(f"  引擎: {config['tts_engine']}")
    print(f"  语音: {config.get('voice', '(系统默认)')}")
    print(f"  语速: {config.get('rate', '默认')}")

    # 显示输出设备
    try:
        dev_info = sd.query_devices(device_id)
        print(f"  输出设备: [{device_id}] {dev_info['name']}")
    except Exception:
        print(f"  输出设备: [{device_id}]")

    print("=" * 55)
    print("  输入文字后回车即可发送语音")
    print("  输入 /help 查看完整命令，/quit 退出")
    print("=" * 55 + "\n")

    hot = config.get("hot_phrases", {})

    while True:
        try:
            user_input = input("  💬 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  再见！")
            break

        if not user_input:
            continue

        # ---- 命令处理 ----
        if user_input.startswith("/"):
            parts = user_input.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if cmd == "/quit" or cmd == "/q":
                print("  再见！")
                break

            elif cmd == "/help" or cmd == "/h":
                show_help(config)

            elif cmd == "/devices" or cmd == "/d":
                print_devices()

            elif cmd == "/device":
                try:
                    device_id = int(arg)
                    dev_info = sd.query_devices(device_id)
                    print(f"  ✅ 输出设备切换为: [{device_id}] {dev_info['name']}")
                    config["output_device"] = device_id
                except (ValueError, IndexError):
                    print(f"  ❌ 无效设备 ID: {arg}")

            elif cmd == "/engine":
                if arg in ("edge", "google", "offline"):
                    config["tts_engine"] = arg
                    print(f"  ✅ TTS 引擎切换为: {arg}")
                else:
                    print(f"  ❌ 引擎只能是 edge / google / offline")

            elif cmd == "/voice":
                if arg:
                    config["voice"] = arg
                    print(f"  ✅ 语音切换为: {arg}")
                    print(f"  提示: 可用语音有 zh-CN-XiaoxiaoNeural, "
                          f"zh-CN-YunxiNeural, zh-CN-XiaoyiNeural 等")

            elif cmd == "/rate":
                if arg:
                    config["rate"] = arg
                    print(f"  ✅ 语速切换为: {arg}")

            elif cmd == "/hot":
                if "=" in arg:
                    k, v = arg.split("=", 1)
                    k, v = k.strip(), v.strip()
                    config["hot_phrases"][k] = v
                    hot = config["hot_phrases"]
                    print(f"  ✅ 快捷短语: {k} → {v}")
                else:
                    if hot:
                        print("  🔥 快捷短语:")
                        for k, v in hot.items():
                            print(f"    {k:12s} → {v}")
                    else:
                        print("  暂无快捷短语")

            elif cmd == "/config":
                print(json.dumps(config, indent=4, ensure_ascii=False))

            elif cmd == "/save":
                save_config(config)
                print(f"  ✅ 配置已保存到 {CONFIG_PATH}")

            else:
                print(f"  ❓ 未知命令: {cmd}，输入 /help 查看帮助")

        else:
            # ---- 普通文本 / 快捷短语 ----
            # 检查是否完全匹配快捷短语
            if user_input in hot:
                text = hot[user_input]
                print(f"  🔥 触发快捷短语: {user_input} → {text}")
            else:
                text = user_input

            await speak(text, config, device_id)
            print()  # 空行分隔


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
def main():
    """解析命令行参数并启动。"""
    # 简单命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "--list" or sys.argv[1] == "-l":
            print_devices()
            return
        elif sys.argv[1] == "--device" or sys.argv[1] == "-d":
            if len(sys.argv) > 2:
                try:
                    device_id = int(sys.argv[2])
                    print(f"使用设备 [{device_id}]")
                    # 直接进入单次模式
                    text = input("输入要说的文字: ").strip()
                    if text:
                        config = get_config()
                        asyncio.run(speak(text, config, device_id))
                except ValueError:
                    print(f"无效设备 ID: {sys.argv[2]}")
            else:
                print("用法: python tts_mic.py --device <ID>")
            return
        elif sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print(__doc__)
            return

    # 默认：交互模式
    try:
        asyncio.run(interactive_loop())
    except KeyboardInterrupt:
        print("\n  再见！")


if __name__ == "__main__":
    main()
